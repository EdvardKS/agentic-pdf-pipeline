import os
from pathlib import Path
from typing import Tuple, List

import fitz  # PyMuPDF

from pipeline.space.space_client import get_space_client


TMP_DIR = Path("./tmp")
TMP_DIR.mkdir(exist_ok=True)


def pdf_to_images(pdf_path: str, dpi: int = 300) -> List[str]:
    """
    Convierte cada página del PDF a PNG en ./tmp y devuelve lista de paths.
    """
    out_paths: List[str] = []

    with fitz.open(pdf_path) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            img_path = TMP_DIR / f"{Path(pdf_path).stem}.page_{page.number}.png"
            pix.save(str(img_path))
            out_paths.append(str(img_path))

    return out_paths


def ocr_pdf(pdf_path: str, *, dpi: int = 300, cleanup: bool = True) -> Tuple[str, str]:
    """
    OCR vía HF Space:
      1) PDF -> PNGs en ./tmp
      2) POST /ocr (multipart) por imagen
      3) concatena texto
      4) guarda artefacto OCR en ./tmp/<pdfname>.ocr.txt

    Devuelve:
      (texto_ocr, ruta_artefacto_txt)
    """
    space = get_space_client()

    images = pdf_to_images(pdf_path, dpi=dpi)
    text_parts: List[str] = []

    for img in images:
        resp = space.ocr_image(img)
        text_parts.append(resp.get("text", ""))

        if cleanup:
            try:
                os.remove(img)
            except OSError:
                pass

    text = "\n".join([t for t in text_parts if t.strip()])

    artifact_path = TMP_DIR / f"{Path(pdf_path).stem}.ocr.txt"
    artifact_path.write_text(text, encoding="utf-8")

    return text, str(artifact_path)
