from searchDocs import find_pdfs
from manifest import generate_manifest, summarize_batch, mark_duplicates

from pipeline.graph.graph import build_graph
from pipeline.graph.state import DocumentState
# from pipeline.vector_store import add_vectors
# from chat import start_chat

import json
from datetime import datetime
from pathlib import Path


def user_menu():
    print("Opciones:")
    print("1 - Extraer")
    print("2 - Cancelar")
    return input("\nSelecciona opción: ").strip()

def create_output_file():

    output_dir = Path("./outputs")
    output_dir.mkdir(exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    path = output_dir / f"extraction_{ts}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump([], f)

    return path
 

def main():

    ruta_docs = "./docs"
    
    #Descubrimos PDFs y metadatos básicos (path, sha256)
    documents = find_pdfs(ruta_docs)

    if not documents:
        print("No se encontraron PDFs")
        return
    
    #Marcamos duplicados por sha256
    documents = mark_duplicates(documents)

    summarize_batch(documents)
    #Generamos manifest en batches/
    generate_manifest(documents)

    choice = user_menu()

    if choice == "1":

        print("\nComienza el pipeline\n")
        output_file = create_output_file() 

        # Construimos el grafo UNA vez (muy importante: no dentro del loop)
        graph = build_graph()

        # Procesamos cada doc con el grafo
        for doc in documents:
            if doc.get("duplicate"):
                continue

            print(f"\nProcesando: {doc['path']}")

            # Creamos el estado inicial para este documento  
            state: DocumentState = {
                "path": doc["path"],
                "sha256": doc["sha256"],
                "text": "",
                "clean_text": "",
                "chunks": [],
                "embeddings": [],
                "ocr_used": False,
                "output_file": str(output_file),
                "extraction_log": []
            } 

            # Ejecutamos el grafo: extract -> clean -> chunk -> embed
            result = graph.invoke(state)

            # # Recuperamos embeddings generados
            # vectors = result["embeddings"]

            # # Los añadimos a tu vector_store en memoria
            # add_vectors(vectors)

            # print(f"Embeddings generados: {len(vectors)}")
             

        # Al terminar, el índice está listo y arrancamos el chat RAG
        print("\nExtracción completada\n")

    elif choice == "2":
        print("\nCancelado\n")

    else:
        print("\nOpción no válida\n")


if __name__ == "__main__":
    main()