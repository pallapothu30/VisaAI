from pathlib import Path
from typing import Dict, Tuple

import cv2
import numpy as np
import pytesseract


def preprocess_image(image_path: Path) -> np.ndarray:
    img = cv2.imdecode(np.fromfile(str(image_path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Unable to read image")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=1.2, fy=1.2, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def ocr_text(image: np.ndarray) -> str:
    config = "--oem 3 --psm 6"
    text = pytesseract.image_to_string(image, config=config)
    return text


def parse_structured(text: str) -> Dict:
    import re
    def find(pattern: str) -> str | None:
        m = re.search(pattern, text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    dob = find(r"DOB[:\s]+([0-9]{2}[-/][0-9]{2}[-/][0-9]{4})")
    expiry = find(r"Expiry[:\s]+([0-9]{2}[-/][0-9]{2}[-/][0-9]{4})")
    passport = find(r"Passport\s*(No\.?|Number)?[:\s]+([A-Z0-9]+)")
    name = find(r"Name[:\s]+([A-Za-z\s]+)")

    def to_iso(d: str | None) -> str | None:
        if not d:
            return None
        parts = d.replace("/", "-").split("-")
        if len(parts) == 3:
            dd, mm, yyyy = parts
            return f"{yyyy}-{mm}-{dd}"
        return d

    return {
        "name": name,
        "dob": to_iso(dob),
        "passport_number": passport if not passport or passport.startswith("P") else f"P{passport}",
        "expiry_date": to_iso(expiry),
    }


def run_ocr_pipeline(file_path: Path) -> Tuple[str, Dict]:
    # If PDF, try first page rasterization via OpenCV + poppler/ghostscript absent -> rely on tesseract built-in if present.
    # For MVP we treat non-images as unsupported and let tesseract attempt anyway.
    image = preprocess_image(file_path)
    text = ocr_text(image)
    parsed = parse_structured(text)
    return text, parsed



