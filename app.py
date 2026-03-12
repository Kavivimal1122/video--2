import streamlit as st
import cv2
import pytesseract
import pandas as pd
import re
import tempfile
import os

# --- TESSERACT ENGINE SETUP ---
if os.path.exists('/usr/bin/tesseract'):
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# --- 91 CLUB MAPPING LOGIC ---
def get_color_code(num):
    if num in [1, 3, 7, 9]: return "G"
    if num in [2, 4, 6, 8]: return "R"
    if num == 5: return "G/V"
    if num == 0: return "R/V"
    return "Unknown"

def get_size_code(num):
    return "B" if num >= 5 else "S"

st.set_page_config(page_title="91 Club Ultimate Scanner", layout="wide")
st.title("🎰 91 Club: Video to Excel (Strict Mode)")
st.write("Scan fast recordings and get clean, unique results.")

uploaded_video = st.file_uploader("Upload Game Video", type=['mp4', 'mov'])

if uploaded_video:
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_video.read())

    if st.button("🔥 START DEEP SCAN"):
        cap = cv2.VideoCapture(tfile.name)
        # Dictionary locks the Period Number so only the FIRST discovery is saved
        final_results = {} 
        
        progress_bar = st.progress(0)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            frame_idx += 1
            if frame_idx % 5 == 0:
                progress_bar.progress(min(frame_idx / total_frames, 1.0))

            # Image Preprocessing (Grayscale + Threshold)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            
            # OCR Scan
            text = pytesseract.image_to_string(thresh, config='--psm 6 digits')
            
            periods = re.findall(r'\d{12,15}', text)
            numbers = re.findall(r'\b\d{1}\b', text)
            
            for i in range(min(len(periods), len(numbers))):
                p_num = str(periods[i])
                r_num = int(numbers[i])
                
                # STRICT RULE: Only save if Period Number is new
                if p_num not in final_results:
                    final_results[p_num] = {
                        "Period Number": p_num,
                        "Result Number": r_num,
                        "Result Color": get_color_code(r_num),
                        "Size": get_size_code(r_num)
                    }

        cap.release()

        if final_results:
            df = pd.DataFrame(list(final_results.values()))
            # Sort Newest to Oldest
            df = df.sort_values(by='Period Number', ascending=False)
            
            st.success(f"✅ Found {len(df)} Unique Clean Results!")
            st.dataframe(df)
            
            # Download Button
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download win_go_results.xlsx", csv, "win_go_results.csv", "text/csv")
        else:
            st.error("No results found. Is the video clear?")
