import streamlit as st
import cv2
import pytesseract
import pandas as pd
import re
import tempfile
import os
import numpy as np

# --- TESSERACT ENGINE SETUP ---
if os.path.exists('/usr/bin/tesseract'):
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# --- YOUR EXACT FORMAT MAPPING ---
def get_color_code(num):
    if num in [1, 3, 7, 9]: return "G"
    if num in [2, 4, 6, 8]: return "R"
    if num in [0, 5]: return "G/V" if num == 5 else "R/V"
    return "Unknown"

def get_size_code(num):
    return "B" if num >= 5 else "S"

st.set_page_config(page_title="91 Club ULTIMATE Scanner", layout="wide")
st.title("🧨 91 Club ULTIMATE AGGRESSIVE Scanner")
st.write("Target: 500+ Results | Logic: Concatenation Deduplication | Mode: Frame-by-Frame Deep Scan")

uploaded_file = st.file_uploader("Upload Your Fast Game Recording", type=['mp4', 'mov'])

if uploaded_file:
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_file.read())
    
    if st.button("🔥 START ULTIMATE EXTRACTION"):
        cap = cv2.VideoCapture(tfile.name)
        raw_results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Scan EVERY frame (Maximum Power)
        curr_frame = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            curr_frame += 1
            if curr_frame % 5 == 0: # Update progress UI every 5 frames
                progress_bar.progress(min(curr_frame / total_frames, 1.0))
                status_text.text(f"Scanning Frame {curr_frame}/{total_frames}... Found {len(raw_results)} potential lines.")

            # --- AGGRESSIVE IMAGE PROCESSING ---
            # 1. Grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 2. Sharpening Filter (Crucial for fast videos)
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(gray, -1, kernel)
            
            # 3. High Contrast Binarization
            _, thresh = cv2.threshold(sharpened, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # --- DEEP OCR SCAN ---
            # Using PSM 6 (uniform block) + digits whitelist
            text = pytesseract.image_to_string(thresh, config='--psm 6 digits')
            
            # Regex to find Period Number (10+ digits) and Result (1 digit)
            periods = re.findall(r'\d{10,15}', text)
            results = re.findall(r'\b\d{1}\b', text)
            
            for i in range(min(len(periods), len(results))):
                p_num = str(periods[i])
                r_num = int(results[i])
                c_code = get_color_code(r_num)
                s_code = get_size_code(r_num)
                
                # --- YOUR CONCATENATION LOGIC ---
                # This makes the results unique based on the full row data
                concat_key = f"{p_num}{r_num}{c_code}{s_code}"
                
                raw_results.append({
                    "Concat_Key": concat_key,
                    "Period Number": p_num,
                    "Result Number": r_num,
                    "Result Color": c_code,
                    "Size": s_code
                })

        cap.release()
        
        if raw_results:
            # Create DataFrame
            df = pd.DataFrame(raw_results)
            
            # APPLY DEDUPLICATION ON CONCAT KEY
            df = df.drop_duplicates(subset=['Concat_Key'])
            
            # SORT BY PERIOD (Newest at top as per your example)
            df = df.sort_values(by='Period Number', ascending=False)
            
            # FINAL CLEANUP: Remove the helper key
            final_df = df[['Period Number', 'Result Number', 'Result Color', 'Size']]
            
            st.success(f"💎 MISSION COMPLETE! Found {len(final_df)} Unique Results.")
            st.dataframe(final_df, height=600)
            
            # DOWNLOAD EXCEL
            excel_data = final_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 DOWNLOAD 500+ RESULTS EXCEL", excel_data, "91Club_Aggressive_Results.csv", "text/csv")
        else:
            st.error("Zero results found. Please check if the video has enough light.")
