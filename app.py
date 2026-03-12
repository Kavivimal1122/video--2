import streamlit as st
import cv2
import pytesseract
import easyocr
import pandas as pd
import numpy as np
import re
import tempfile
import os

# ---------- OCR ENGINES ----------
reader = easyocr.Reader(['en'], gpu=False)

if os.path.exists('/usr/bin/tesseract'):
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'


# ---------- GAME LOGIC ----------
def get_color_code(num):
    if num in [1,3,7,9]:
        return "Green"
    if num in [2,4,6,8]:
        return "Red"
    if num == 0:
        return "Red/Violet"
    if num == 5:
        return "Green/Violet"
    return "Unknown"

def get_size_code(num):
    return "Big" if num >= 5 else "Small"


# ---------- IMAGE PROCESSING ----------
def preprocess(frame):

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # upscale image
    frame = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    # sharpen
    kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
    sharp = cv2.filter2D(frame,-1,kernel)

    # adaptive threshold
    thresh = cv2.adaptiveThreshold(
        sharp,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11,
        2
    )

    return thresh


# ---------- OCR ----------
def run_ocr(img):

    text_all = ""

    # Tesseract
    try:
        text1 = pytesseract.image_to_string(
            img,
            config="--psm 6 -c tessedit_char_whitelist=0123456789"
        )
        text_all += text1
    except:
        pass

    # EasyOCR
    try:
        result = reader.readtext(img, detail=0)
        text_all += " ".join(result)
    except:
        pass

    return text_all


# ---------- STREAMLIT UI ----------
st.set_page_config(layout="wide")
st.title("🚀 91 Club ULTRA AGGRESSIVE AI Scanner")

uploaded_file = st.file_uploader("Upload Video", type=["mp4","mov"])

if uploaded_file:

    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_file.read())

    if st.button("START EXTRACTION"):

        cap = cv2.VideoCapture(tfile.name)

        results = []
        seen_periods = set()

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        progress = st.progress(0)

        frame_no = 0

        while cap.isOpened():

            ret, frame = cap.read()
            if not ret:
                break

            frame_no += 1

            progress.progress(frame_no/total_frames)

            # scan every 2 frames
            if frame_no % 2 != 0:
                continue

            # ---------- ROI (Crop middle area) ----------
            h,w,_ = frame.shape
            roi = frame[int(h*0.25):int(h*0.75), int(w*0.2):int(w*0.8)]

            processed = preprocess(roi)

            text = run_ocr(processed)

            periods = re.findall(r'\d{10,15}', text)
            numbers = re.findall(r'\b\d\b', text)

            for i in range(min(len(periods), len(numbers))):

                p = periods[i]
                n = int(numbers[i])

                if p in seen_periods:
                    continue

                seen_periods.add(p)

                results.append({
                    "Period Number":p,
                    "Result Number":n,
                    "Result Color":get_color_code(n),
                    "Size":get_size_code(n)
                })


        cap.release()

        if results:

            df = pd.DataFrame(results)

            df = df.drop_duplicates()

            df = df.sort_values(
                by="Period Number",
                ascending=False
            )

            st.success(f"Total Results Found: {len(df)}")

            st.dataframe(df)

            csv = df.to_csv(index=False).encode()

            st.download_button(
                "Download Excel",
                csv,
                "91club_results.csv",
                "text/csv"
            )

        else:
            st.error("No results detected")
