import fitz  # PyMuPDF


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