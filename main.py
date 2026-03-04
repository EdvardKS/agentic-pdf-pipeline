from searchDocs import find_pdfs
from manifest import generate_manifest, summarize_batch, mark_duplicates


def user_menu():

    print("Opciones:")
    print("1 - Extraer")
    print("2 - Cancelar")

    choice = input("\nSelecciona opción: ")

    return choice.strip()


def main():

    ruta_docs = "./docs"

    documents = find_pdfs(ruta_docs)

    if not documents:
        print("No se encontraron PDFs")
        return

    documents = mark_duplicates(documents)

    summary = summarize_batch(documents)

    manifest_path = generate_manifest(documents)

    choice = user_menu()

    if choice == "1":

        print("\nComienza el pipeline\n")

    elif choice == "2":

        print("\nCancelado\n")

    else:

        print("\nOpción no válida\n")


if __name__ == "__main__":
    main()