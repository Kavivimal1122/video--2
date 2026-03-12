import cv2
import pytesseract
import pandas as pd
import re
import os
import tempfile
import streamlit as st

# --- TESSERACT CONFIGURATION ---
# If running on Windows locally, uncomment the line below and point to your .exe
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- HELPER FUNCTIONS ---
def get_color_logic(num):
    """Maps 91 Club numbers to colors based on official game rules."""
    if num in [1, 3, 7, 9]: return "Green"
    if num in [2, 4, 6, 8]: return "Red"
    if num in [0]: return "Red/Violet"
    if num in [5]: return "Green/Violet"
    return "Unknown"

def get_size_logic(num):
    """Classifies numbers as Big (5-9) or Small (0-4)."""
    return "Big" if num >= 5 else "Small"

# --- STREAMLIT UI ---
st.set_page_config(page_title="91 Club OCR Scanner", layout="wide")
st.title("🎰 91 Club Win Go - Video to Excel Converter")
st.markdown("### Process fast-scrolling recordings with 0.25x slow-scan logic.")

uploaded_video = st.file_uploader("Upload your MP4 screen recording", type=['mp4', 'mov'])

if uploaded_video:
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_video.read())

    if st.button("🚀 Start Deep Scan & Export"):
        cap = cv2.VideoCapture(tfile.name)
        # We use a Dictionary to ensure Period Number is a unique key (Set behavior)
        results_data = {} 
        
        progress_bar = st.progress(0)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # SLOW-MOTION LOGIC: Analyze every single frame to catch fast scrolls
        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            # Update progress bar every 10 frames to save UI resources
            if frame_count % 10 == 0:
                progress_bar.progress(min(frame_count / total_frames, 1.0))
            
            # --- STEP 1: IMAGE PREPROCESSING ---
            # Convert to grayscale and apply thresholding to make text sharper
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            
            # --- STEP 2: OCR EXTRACTION ---
            # psm 6: Assume a uniform block of text. digits: Only look for numbers.
            text = pytesseract.image_to_string(thresh, config='--psm 6 digits')
            
            # --- STEP 3: DATA PARSING ---
            # Regex to find Period Number (10-15 digits) and Result (1 digit)
            periods = re.findall(r'\d{12,15}', text)
            numbers = re.findall(r'\b\d{1}\b', text)
            
            for i in range(min(len(periods), len(numbers))):
                p_num = str(periods[i])
                r_num = int(numbers[i])
                
                # --- STEP 4: DUPLICATE REMOVAL (DICT LOCK) ---
                # If the period is already in our dictionary, we skip it.
                if p_num not in results_data:
                    results_data[p_num] = {
                        "Period_Number": p_num,
                        "Result_Number": r_num,
                        "Color": get_color_logic(r_num),
                        "Size": get_size_logic(r_num)
                    }

        cap.release()

        # --- STEP 5: FINAL PROCESSING ---
        if results_data:
            df = pd.DataFrame(list(results_data.values()))
            
            # Sort by Period Number (Ascending)
            df = df.sort_values(by='Period_Number', ascending=True)
            
            st.success(f"✅ Successfully extracted {len(df)} unique game results!")
            st.dataframe(df)

            # --- STEP 6: EXCEL EXPORT ---
            output_path = "win_go_results.xlsx"
            df.to_excel(output_path, index=False)
            
            with open(output_path, "rb") as f:
                st.download_button(
                    label="📥 Download win_go_results.xlsx",
                    data=f,
                    file_name="win_go_results.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.error("No results detected. Ensure the video is clear and displays the game history.")
