import importlib
import json
from datetime import datetime
from pathlib import Path

from searchDocs import find_pdfs
from manifest import generate_manifest, summarize_batch, mark_duplicates
from pipeline.graph.graph import build_graph
from pipeline.graph.state import DocumentState
from pipeline.schema_loader import load_schema


REGISTRY_PATH = Path("models_registry.json")

CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"


def load_registry() -> dict:
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def user_menu(registry: dict) -> str:
    print(f"\n{CYAN}╔══════════════════════════════════════════════╗{RESET}")
    print(f"{CYAN}║     MAM Solicitors — Pipeline Fiscal         ║{RESET}")
    print(f"{CYAN}╚══════════════════════════════════════════════╝{RESET}")
    print("\nSelecciona el modelo a generar:\n")
    for key, model in registry.items():
        print(f"  {YELLOW}{key}{RESET} - {model['label']}")
    print(f"\n  {YELLOW}0{RESET} - Cancelar")
    return input("\nOpción: ").strip()


def load_exporter(module_path: str):
    """Importa dinámicamente el módulo exportador y devuelve su función export."""
    module = importlib.import_module(module_path)
    return module.export


def create_output_dir(output_dir: str) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def main():
    ruta_docs = "./docs"

    documents = find_pdfs(ruta_docs)

    if not documents:
        print(f"{RED}No se encontraron PDFs en {ruta_docs}{RESET}")
        return

    documents = mark_duplicates(documents)
    summarize_batch(documents)
    generate_manifest(documents)

    registry = load_registry()
    choice = user_menu(registry)

    if choice == "0":
        print("\nCancelado.\n")
        return

    if choice not in registry:
        print(f"\n{RED}Opción no válida.{RESET}\n")
        return

    model_config = registry[choice]
    model_name = model_config["name"]
    schema_path = model_config["schema"]
    exporter_module = model_config["exporter"]
    output_dir = model_config["output_dir"]

    print(f"\n{GREEN}Modelo seleccionado:{RESET} {model_config['label']}")
    print(f"Schema: {schema_path}")
    print(f"Salida: {output_dir}\n")

    schema = load_schema(schema_path)
    exporter = load_exporter(exporter_module)
    create_output_dir(output_dir)

    graph = build_graph()

    docs_procesados = 0
    docs_exportados = 0

    for doc in documents:
        if doc.get("duplicate"):
            print(f"  [SKIP duplicado] {doc['path']}")
            continue

        print(f"\n{CYAN}Procesando:{RESET} {doc['path']}")
        docs_procesados += 1

        state: DocumentState = {
            "path": doc["path"],
            "sha256": doc["sha256"],
            "text": "",
            "clean_text": "",
            "chunks": [],
            "embeddings": [],
            "ocr_used": False,
            "output_file": "",
            "extraction_log": [],
            "schema": schema,
            "selected_model": choice,
            "validated_data": {},
        }

        result = graph.invoke(state)

        # Usar validated_data (normalizado) si existe, fallback a extraction_log
        validated = result.get("validated_data") or {}
        if not validated:
            extraction_log = result.get("extraction_log", [])
            validated = extraction_log[-1] if extraction_log else {}

        if validated:
            try:
                exporter(validated, output_dir, doc)
                docs_exportados += 1
            except Exception as e:
                print(f"  {RED}Error al exportar {doc['path']}: {e}{RESET}")
        else:
            print(f"  {RED}Sin datos extraídos para {doc['path']}{RESET}")

    print(f"\n{GREEN}══════════════════════════════════════════{RESET}")
    print(f"{GREEN}Pipeline completado{RESET}")
    print(f"  Documentos procesados : {docs_procesados}")
    print(f"  Documentos exportados : {docs_exportados}")
    print(f"  Directorio de salida  : {output_dir}")
    print(f"{GREEN}══════════════════════════════════════════{RESET}\n")


if __name__ == "__main__":
    main()
