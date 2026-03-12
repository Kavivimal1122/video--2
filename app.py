import streamlit as st
import cv2
import pytesseract
import pandas as pd
import re
import tempfile
import os
import numpy as np

# --- TESSERACT ENGINE PATH ---
if os.path.exists('/usr/bin/tesseract'):
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# Logic for 91 Club results
def get_color(num):
    if num in [1, 3, 7, 9]: return "Green"
    if num in [2, 4, 6, 8]: return "Red"
    if num in [0, 5]: return "Violet"
    return "Unknown"

def get_size(num):
    return "Big" if num >= 5 else "Small"

st.set_page_config(page_title="91 Club AGGRESSIVE Scanner", layout="wide")
st.title("🔥 91 Club 'Aggressive' 500-Result Scanner")
st.markdown("### This version uses Triple-Image Scanning and Concatenation Duplication Removal.")

uploaded_file = st.file_uploader("Upload Game Recording", type=['mp4', 'mov'])

if uploaded_file:
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_file.read())
    
    if st.button("🧨 Start AGGRESSIVE Scan"):
        cap = cv2.VideoCapture(tfile.name)
        raw_data = []
        progress_bar = st.progress(0)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            curr = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            progress_bar.progress(min(curr / total_frames, 1.0))
            
            # --- AGGRESSIVE IMAGE PRE-PROCESSING ---
            # 1. Grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 2. Create 3 different versions to ensure we catch the text
            # Version A: Standard Threshold
            _, thresh1 = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            # Version B: Adaptive Threshold (handles light/shadows better)
            thresh2 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
            
            # Combine both versions for the AI to "read"
            combined_scans = [thresh1, thresh2]
            
            for scan in combined_scans:
                # Zoom in on text (2x)
                scan = cv2.resize(scan, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
                
                # --- AGGRESSIVE OCR ---
                # psm 11: Sparse text. Find as much as possible.
                text = pytesseract.image_to_string(scan, config='--psm 11 digits')
                
                # Regex for Periods (usually 10-15 digits) and Results (1 digit)
                periods = re.findall(r'\d{10,15}', text)
                results = re.findall(r'\b\d{1}\b', text)
                
                for i in range(min(len(periods), len(results))):
                    p_num = str(periods[i])
                    r_num = int(results[i])
                    color = get_color(r_num)
                    size = get_size(r_num)
                    
                    # --- CONCATENATION LOGIC ---
                    # Create a unique key to prevent duplicates
                    unique_key = f"{p_num}_{r_num}_{color}_{size}"
                    
                    raw_data.append({
                        "Unique_ID": unique_key, # Concatenated Value
                        "Period Number": p_num,
                        "Result Number": r_num,
                        "Result Color": color,
                        "Size": size
                    })

        cap.release()
        
        if raw_data:
            df = pd.DataFrame(raw_data)
            
            # --- REMOVE DUPLICATES USING THE CONCATENATED ID ---
            df = df.drop_duplicates(subset=['Unique_ID'])
            
            # Sort by Period Number
            df = df.sort_values(by='Period Number', ascending=True)
            
            # Clean up: Remove the helper Unique_ID column before showing the user
            final_df = df.drop(columns=['Unique_ID'])
            
            st.success(f"💎 SUCCESS! Found {len(final_df)} Unique Results.")
            st.dataframe(final_df)
            
            # Export to CSV/Excel
            csv = final_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download All 500+ Results", csv, "Full_91Club_Results.csv", "text/csv")
        else:
            st.error("Aggressive scan failed to find text. Is the video very blurry?")
