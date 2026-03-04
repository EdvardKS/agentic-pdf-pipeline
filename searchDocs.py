from pathlib import Path


def find_pdfs(folder_path: str):
    """
    Busca archivos PDF recursivamente dentro de una carpeta
    """
    base_path = Path(folder_path)

    if not base_path.exists():
        raise ValueError(f"La ruta {folder_path} no existe")

    pdf_files = []

    for file in base_path.rglob("*.pdf"):
        pdf_files.append(file)

    return pdf_files


def print_pdf_list(pdf_list):

    print("\nPDFs encontrados:\n")

    for i, pdf in enumerate(pdf_list, 1):
        print(f"{i}. {pdf}")

    print(f"\nTotal encontrados: {len(pdf_list)}\n")