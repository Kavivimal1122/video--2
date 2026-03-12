import streamlit as st
import cv2
import pytesseract
import pandas as pd
import re
import tempfile
import os
import numpy as np

# --- TESSERACT PATH ---
if os.path.exists('/usr/bin/tesseract'):
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

def get_color(num):
    if num in [1, 3, 7, 9]: return "Green"
    if num in [2, 4, 6, 8]: return "Red"
    if num in [0, 5]: return "Violet"
    return "Unknown"

def get_size(num):
    return "Big" if num >= 5 else "Small"

st.set_page_config(page_title="91 Club Pro Extractor", layout="wide")
st.title("🚀 91 Club 500-Result Deep Scanner")

uploaded_file = st.file_uploader("Upload Video", type=['mp4', 'mov'])

if uploaded_file:
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_file.read())
    
    if st.button("🔍 Start Deep Extraction"):
        cap = cv2.VideoCapture(tfile.name)
        raw_data = []
        progress_bar = st.progress(0)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # --- CONFIGURATION ---
        # frame_step = 1 means check EVERY frame. Slow but very accurate.
        frame_step = 1 
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            curr = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
            if curr % frame_step == 0:
                progress_bar.progress(min(curr / total_frames, 1.0))
                
                # 1. CROP TO TABLE (Focus on the center-bottom where history is)
                h, w, _ = frame.shape
                # We crop: Top 30% off, Bottom 10% off, Sides 5% off
                roi = frame[int(h*0.3):int(h*0.9), int(w*0.05):int(w*0.95)]
                
                # 2. IMAGE ENHANCEMENT
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
                # Increase contrast
                gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
                # Resize (Makes text 2x bigger, easier for AI to read)
                gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                
                # 3. DEEP OCR
                # --psm 6 assumes a block of uniform text
                text = pytesseract.image_to_string(gray, config='--psm 6 digits')
                
                # Use a smarter regex to find periods (10 to 15 digits)
                periods = re.findall(r'\d{10,15}', text)
                results = re.findall(r'\b\d{1}\b', text)
                
                for i in range(min(len(periods), len(results))):
                    try:
                        p_val = int(periods[i])
                        r_val = int(results[i])
                        raw_data.append({
                            "Period Number": p_val,
                            "Result Number": r_val,
                            "Result Color": get_color(r_val),
                            "Size": get_size(r_val)
                        })
                    except: continue
        cap.release()
        
        if raw_data:
            df = pd.DataFrame(raw_data)
            # Remove Duplicates & Sort
            df = df.drop_duplicates(subset=['Period Number']).sort_values(by='Period Number', ascending=True)
            
            st.success(f"✅ Success! Found {len(df)} Unique Results.")
            st.dataframe(df)
            
            # Download Button
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Results (CSV/Excel)", csv, "91_Club_Results.csv", "text/csv")
        else:
            st.error("Still found 0 results. The video might be too blurry or the table area is hidden.")
