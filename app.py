import streamlit as st
import cv2
import pytesseract
import pandas as pd
import re
import tempfile
import os

# --- TESSERACT PATH ---
if os.path.exists('/usr/bin/tesseract'):
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# EXACT FORMAT MAPPING
def get_color_code(num):
    if num in [1, 3, 7, 9]: return "G"
    if num in [2, 4, 6, 8]: return "R"
    if num in [5]: return "G/V"
    if num in [0]: return "R/V"
    return "Unknown"

def get_size_code(num):
    return "B" if num >= 5 else "S"

st.title("🎯 91 Club 500-Result Clean Scanner")
st.write("Mode: Strict Unique Period (No Duplicates)")

uploaded_file = st.file_uploader("Upload Video", type=['mp4', 'mov'])

if uploaded_file:
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_file.read())
    
    if st.button("🔥 Run Clean Scan"):
        cap = cv2.VideoCapture(tfile.name)
        final_results = {} # We use a Dictionary to prevent duplicate periods
        
        progress_bar = st.progress(0)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            curr = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            if curr % 2 == 0: # Check every 2nd frame for speed
                progress_bar.progress(min(curr / total_frames, 1.0))
                
                # Pre-process
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                text = pytesseract.image_to_string(gray, config='--psm 6 digits')
                
                # Extract
                periods = re.findall(r'\d{12,15}', text)
                results = re.findall(r'\b\d{1}\b', text)
                
                for i in range(min(len(periods), len(results))):
                    p_num = str(periods[i])
                    r_num = int(results[i])
                    
                    # --- STRICT RULE ---
                    # If we haven't seen this Period Number yet, save it.
                    # If we HAVE seen it, ignore all other versions of it.
                    if p_num not in final_results:
                        final_results[p_num] = {
                            "Period Number": p_num,
                            "Result Number": r_num,
                            "Result Color": get_color_code(r_num),
                            "Size": get_size_code(r_num)
                        }

        cap.release()
        
        if final_results:
            # Convert dictionary back to a list
            df = pd.DataFrame(list(final_results.values()))
            
            # Sort Newest to Oldest
            df = df.sort_values(by='Period Number', ascending=False)
            
            st.success(f"✅ Found {len(df)} Unique Clean Rows!")
            st.dataframe(df)
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Final Excel", csv, "Clean_Results.csv", "text/csv")
