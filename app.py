import streamlit as st
import pytesseract
import pandas as pd
import re
from PIL import Image, ImageOps, ImageFilter
import io
import os

# --- TESSERACT ENGINE SETUP ---
if os.path.exists('/usr/bin/tesseract'):
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# --- 91 CLUB LOGIC ---
def get_91club_data(num):
    # Color Mapping
    if num in [1, 3, 7, 9]: color = "G"
    elif num in [2, 4, 6, 8]: color = "R"
    elif num == 5: color = "G/V"
    else: color = "R/V" # For 0
    
    # Size Mapping
    size = "B" if num >= 5 else "S"
    return color, size

st.set_page_config(page_title="91 Club Row Scanner", layout="wide")
st.title("📸 91 Club: Full Table Scanner")
st.write("This version reads row-by-row to ensure all 10+ results are captured.")

uploaded_files = st.file_uploader("Upload Screenshot", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    final_results = {} 
    
    if st.button("🔍 Extract All Rows"):
        with st.spinner("Processing table..."):
            for uploaded_file in uploaded_files:
                img = Image.open(uploaded_file)
                
                # Image Pre-processing for better table reading
                img = img.convert('L') # Grayscale
                img = ImageOps.invert(img) # Invert helps OCR read white text on dark buttons
                img = ImageOps.autocontrast(img)
                
                # Use PSM 6 (Assume a uniform block of text)
                text = pytesseract.image_to_string(img, config='--psm 6')
                
                # Split text into lines to process row by row
                lines = text.split('\n')
                
                for line in lines:
                    # Look for Period Number (usually starts with 2026...)
                    period_match = re.search(r'(20\d{11,13})', line)
                    
                    if period_match:
                        p_num = period_match.group(1)
                        
                        # After finding the period, look for the single result digit in the same line
                        # We look for a 1-digit number that is NOT part of the period
                        remaining_text = line.replace(p_num, "")
                        result_match = re.search(r'\b(\d{1})\b', remaining_text)
                        
                        if result_match:
                            r_num = int(result_match.group(1))
                            color, size = get_91club_data(r_num)
                            
                            if p_num not in final_results:
                                final_results[p_num] = {
                                    "Period Number": p_num,
                                    "Result Number": r_num,
                                    "Color": color,
                                    "Size": size
                                }

        if final_results:
            df = pd.DataFrame(list(final_results.values()))
            df = df.sort_values(by='Period Number', ascending=False)
            
            st.success(f"✅ Successfully extracted {len(df)} results!")
            st.dataframe(df, use_container_width=True)
            
            # Excel Download
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Download Results as Excel",
                data=output.getvalue(),
                file_name="91Club_Full_Scan.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No rows detected. Try a clearer screenshot.")
