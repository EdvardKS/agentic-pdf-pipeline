from searchDocs import find_pdfs
from manifest import generate_manifest, summarize_batch, mark_duplicates
from pipeline.preprocess import extract_raw_text, save_text_artifact
from pipeline.ocr import ocr_pdf


def user_menu():
    print("Opciones:")
    print("1 - Extraer")
    print("2 - Cancelar")
    return input("\nSelecciona opción: ").strip()


def main():
    ruta_docs = "./docs"

    documents = find_pdfs(ruta_docs)

    if not documents:
        print("No se encontraron PDFs")
        return

    documents = mark_duplicates(documents)

    summarize_batch(documents)
    generate_manifest(documents)

    choice = user_menu()

    if choice == "1":

        print("\nComienza el pipeline\n")

        for doc in documents:

            if doc.get("duplicate"):
                continue

            result = extract_raw_text(doc["path"])

            print(f"\nProcesado: {doc['path']}")
            print(f"Caracteres extraídos: {result['text_length']}")

            if result["ocr_needed"]:
                print("⚠ OCR requerido")

                text, artifact = ocr_pdf(doc["path"])

                doc["text"] = text
                doc["text_artifact"] = artifact

                print(f"Caracteres OCR: {len(text)}")
                print(f"Artefacto OCR: {artifact}")

            else:
                artifact = save_text_artifact(doc["path"], result["text"], "raw")

                doc["text"] = result["text"]
                doc["text_artifact"] = artifact

                print(f"Artefacto RAW: {artifact}")

    elif choice == "2":
        print("\nCancelado\n")

    else:
        print("\nOpción no válida\n")


if __name__ == "__main__":
    main()