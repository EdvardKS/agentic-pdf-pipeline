import fitz  # PyMuPDF
import os
from pathlib import Path

TMP_DIR = Path("./tmp")
TMP_DIR.mkdir(exist_ok=True)

def extract_raw_text(pdf_path):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()

    text_length = len(text)

    return {
        "text": text,
        "text_length": text_length,
        "ocr_needed": text_length < 100
    }

def save_text_artifact(pdf_path, text, suffix="raw"):
    """
    Guarda el texto extraído en ./tmp/<nombre_pdf>.<suffix>.txt
    """
    name = Path(pdf_path).stem
    out = TMP_DIR / f"{name}.{suffix}.txt"
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    return str(out)