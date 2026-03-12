import streamlit as st
import cv2
import pytesseract
import pandas as pd
import re
import tempfile
import os
import numpy as np

# --- TESSERACT PATH SETUP ---
if os.path.exists('/usr/bin/tesseract'):
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

st.set_page_config(page_title="91 Club Extractor", layout="wide")
st.title("🎯 91 Club: Ultimate 2-Column Scanner")
st.markdown("### Scanning for Period Number & Result Number only.")

uploaded_video = st.file_uploader("Upload Your Fast Recording (MP4)", type=['mp4', 'mov'])

if uploaded_video:
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_video.read())

    if st.button("🔥 START DEEP EXTRACTION"):
        status = st.empty()
        progress_bar = st.progress(0)
        counter = st.empty()
        
        cap = cv2.VideoCapture(tfile.name)
        final_results = {} # Dictionary ensures 100% unique Period Numbers
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            frame_idx += 1
            # Update UI every 10 frames
            if frame_idx % 10 == 0:
                progress_bar.progress(min(frame_idx / total_frames, 1.0))
                status.info(f"Processing Frame {frame_idx}/{total_frames}...")
                counter.metric("Unique Periods Found", len(final_results))

            # --- IMAGE ENHANCEMENT ---
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Sharpening to fix motion blur from fast scrolling
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(gray, -1, kernel)
            
            # Adaptive Threshold to make numbers solid black on white
            thresh = cv2.adaptiveThreshold(sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                          cv2.THRESH_BINARY, 11, 2)

            # --- OCR SCAN ---
            # psm 6: Uniform block of text. digits: Only read numbers.
            text = pytesseract.image_to_string(thresh, config='--psm 6 digits')
            
            # Match Period Numbers (12-15 digits) and Result Numbers (1 digit)
            periods = re.findall(r'\d{12,15}', text)
            numbers = re.findall(r'\b\d{1}\b', text)
            
            for i in range(min(len(periods), len(numbers))):
                p_num = str(periods[i])
                r_num = int(numbers[i])
                
                # STRICT UNIQUE RULE: Lock the period number
                if p_num not in final_results:
                    final_results[p_num] = {
                        "Period Number": p_num,
                        "Result Number": r_num
                    }

        cap.release()

        if final_results:
            status.success(f"✅ Mission Complete! Found {len(final_results)} Unique Results.")
            df = pd.DataFrame(list(final_results.values()))
            
            # Sort Newest to Oldest (Descending)
            df = df.sort_values(by='Period Number', ascending=False)
            
            st.dataframe(df, use_container_width=True)
            
            # Final Download
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Result Excel", csv, "91Club_Results.csv", "text/csv")
        else:
            status.error("No results found. Please check video quality.")
