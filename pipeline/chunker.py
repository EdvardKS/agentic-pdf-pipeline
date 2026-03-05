from pathlib import Path
import os

TMP_DIR = Path("./tmp")
TMP_DIR.mkdir(exist_ok=True)

def save_chunks(doc_path, chunks):

    name = Path(doc_path).stem
    out = TMP_DIR / f"{name}.chunks.txt"

    with open(out, "w", encoding="utf-8") as f:

        for i, chunk in enumerate(chunks):
            f.write(f"\n--- CHUNK {i} ---\n")
            f.write(chunk)

    return str(out)

def semantic_chunk(text, chunk_size=None, overlap=None):
    if chunk_size is None:
        chunk_size = int(os.getenv("CHUNK_SIZE", "3000"))
    if overlap is None:
        overlap = int(os.getenv("CHUNK_OVERLAP", "120"))

    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 10)

    chunks = []

    start = 0
    text_length = len(text)

    while start < text_length:

        end = start + chunk_size
        chunk = text[start:end]

        chunks.append(chunk)

        start = end - overlap

    return chunks
