import streamlit as st
import pytesseract
import pandas as pd
import re
from PIL import Image, ImageOps, ImageFilter
import io
import os

# --- TESSERACT ENGINE SETUP (For Streamlit Cloud) ---
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

st.set_page_config(page_title="91 Club Screenshot Scanner", layout="wide")
st.title("📸 91 Club: High-Accuracy Screenshot Scanner")
st.write("Upload one or more screenshots of the game history for a perfect Excel report.")

# Allow multiple file uploads
uploaded_files = st.file_uploader("Upload Screenshots (PNG/JPG)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if uploaded_files:
    final_results = {} # Use dictionary to keep Period Numbers unique
    
    if st.button("🔍 Scan Screenshots"):
        with st.spinner("Analyzing images..."):
            for uploaded_file in uploaded_files:
                # Load image
                img = Image.open(uploaded_file)
                
                # --- STEP 1: IMAGE ENHANCEMENT ---
                # Convert to Grayscale
                img = img.convert('L')
                # Increase Contrast and Sharpen (makes numbers pop)
                img = ImageOps.autocontrast(img)
                img = img.filter(ImageFilter.SHARPEN)
                
                # --- STEP 2: OCR EXTRACTION ---
                # PSM 6 is best for table-like structures
                text = pytesseract.image_to_string(img, config='--psm 6 digits')
                
                # Regex: Look for 15-digit Period Numbers and 1-digit Results
                periods = re.findall(r'\d{13,15}', text)
                numbers = re.findall(r'\b\d{1}\b', text)
                
                for i in range(min(len(periods), len(numbers))):
                    p_num = str(periods[i])
                    r_num = int(numbers[i])
                    
                    # Ensure the period looks real (usually starts with 202)
                    if p_num.startswith("20"):
                        color, size = get_91club_data(r_num)
                        
                        # Save to dict to prevent duplicates across multiple screenshots
                        if p_num not in final_results:
                            final_results[p_num] = {
                                "Period Number": p_num,
                                "Result Number": r_num,
                                "Color": color,
                                "Size": size
                            }

        if final_results:
            df = pd.DataFrame(list(final_results.values()))
            # Sort Newest to Oldest
            df = df.sort_values(by='Period Number', ascending=False)
            
            st.success(f"✅ Found {len(df)} Unique Clean Results!")
            st.dataframe(df, use_container_width=True)
            
            # --- DOWNLOAD ---
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Download Clean Excel Sheet",
                data=output.getvalue(),
                file_name="91Club_Screenshot_Results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No results found. Please ensure the screenshot is clear.")
