from pathlib import Path
import hashlib
from datetime import datetime


def calculate_sha256(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def find_pdfs(folder_path: str):

    base_path = Path(folder_path)

    if not base_path.exists():
        raise ValueError(f"La ruta {folder_path} no existe")

    documents = []

    for file in base_path.rglob("*.pdf"):

        stat = file.stat()

        documents.append({
            "path": str(file),
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime),
            "sha256": calculate_sha256(file)
        })

    return documents

def print_pdf_list(pdf_list):

    print("\nPDFs encontrados:\n")

    for i, doc in enumerate(pdf_list, 1):
        print(
            f"{i}. {doc['path']} | "
            f"{doc['size']} bytes | "
            f"{doc['sha256'][:10]}..."
        )

    print(f"\nTotal encontrados: {len(pdf_list)}\n")