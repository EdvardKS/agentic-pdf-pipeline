import fitz
import os
from pathlib import Path
from pipeline.ollama_client import client,VISION_MODEL

TMP_DIR = Path("./tmp")
TMP_DIR.mkdir(exist_ok=True)

def _pdf_to_images(pdf_path):
    images = []
    with fitz.open(pdf_path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img = TMP_DIR / f"tmp_page_{page.number}.png"
            pix.save(str(img))
            images.append(str(img))
    return images

def ocr_pdf(pdf_path):
    images = _pdf_to_images(pdf_path)
    text = ""

    for img in images:
        response = client.chat(
            model= VISION_MODEL, # type: ignore
            messages=[{
                "role": "user",
                "content": "Extract all text from this document image exactly as written.",
                "images": [img]
            }]
        ) # type: ignore
        text += response["message"]["content"]
        os.remove(img)

    # guardar artefacto OCR
    name = Path(pdf_path).stem
    out = TMP_DIR / f"{name}.ocr.txt"
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)

    return text, str(out)