import streamlit as st
import cv2
import pytesseract
import pandas as pd
import re
import tempfile
import os

# --- FIX FOR TESSERACT PATH ON STREAMLIT ---
if os.path.exists('/usr/bin/tesseract'):
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# --- 91 CLUB LOGIC FUNCTIONS ---
def get_color(num):
    if num in [1, 3, 7, 9]: return "Green"
    if num in [2, 4, 6, 8]: return "Red"
    if num in [0, 5]: return "Violet"
    return "Unknown"

def get_size(num):
    return "Big" if num >= 5 else "Small"

# --- STREAMLIT UI ---
st.set_page_config(page_title="91 Club Extractor", layout="wide")
st.title("📊 91 Club Video to Excel Converter")
st.write("Upload your video. We will scan every frame (x4 slow-read) to get all 500 results.")

uploaded_file = st.file_uploader("Upload MP4 Video", type=['mp4', 'mov'])

if uploaded_file:
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_file.read())
    
    if st.button("🚀 Start Deep Scan"):
        cap = cv2.VideoCapture(tfile.name)
        raw_data = []
        progress_bar = st.progress(0)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # We read every 1st frame (frame_step=1) for maximum accuracy on fast videos
        frame_step = 1 
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            curr = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            if curr % frame_step == 0:
                progress_bar.progress(min(curr / total_frames, 1.0))
                
                # Pre-processing for better OCR
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                text = pytesseract.image_to_string(gray, config='--psm 6 digits')
                
                # Extracting Periods (13 digits) and Results (1 digit)
                periods = re.findall(r'\d{12,15}', text)
                results = re.findall(r'\b\d{1}\b', text)
                
                for i in range(min(len(periods), len(results))):
                    r_val = int(results[i])
                    raw_data.append({
                        "Period Number": int(periods[i]),
                        "Result Number": r_val,
                        "Result Color": get_color(r_val),
                        "Size": get_size(r_val)
                    })
        cap.release()
        
        if raw_data:
            df = pd.DataFrame(raw_data)
            df = df.drop_duplicates(subset=['Period Number']).sort_values(by='Period Number')
            st.success(f"Extracted {len(df)} Unique Results!")
            st.dataframe(df)
            
            # Export to Excel
            output = "91_Club_Results.xlsx"
            df.to_excel(output, index=False)
            with open(output, "rb") as f:
                st.download_button("📥 Download Excel Sheet", f, file_name=output)
        else:
            st.error("No results found. Ensure the video is clear.")