from searchDocs import find_pdfs, print_pdf_list
from manifest import generate_manifest


def main():

    ruta_docs = "./docs"

    pdfs = find_pdfs(ruta_docs)

    if not pdfs:
        print("No se encontraron PDFs")
        return

    print_pdf_list(pdfs)

    print("Opciones:")
    print("1 - Extraer")
    print("2 - Cancelar")

    opcion = input("\nSelecciona opción: ")

    if opcion == "1":

        manifest_path = generate_manifest(pdfs)

        print("\nBatch creado:")
        print(manifest_path)

        print("\nComienza el pipeline\n")

    elif opcion == "2":
        print("\nCancelado\n")


if __name__ == "__main__":
    main()