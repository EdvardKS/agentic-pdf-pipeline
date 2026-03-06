# Importamos las funciones del pipeline "core".
# La idea es NO reescribir lógica, solo orquestarla.
from pipeline.preprocess import extract_raw_text, save_text_artifact
from pipeline.ocr import ocr_pdf
from pipeline.text_cleaner import clean_text

# Importamos el tipo de estado (solo para tipado y claridad).
from pipeline.graph.state import DocumentState


def extract_node(state: DocumentState) -> DocumentState:
    """
    Nodo 1: Extrae texto del PDF. Si es insuficiente, usa OCR.
    Además guarda artefactos en tmp/ (raw u ocr).
    """

    # 1) Extraemos el texto "digital" con PyMuPDF (si el PDF tiene capa de texto)
    result = extract_raw_text(state["path"])

    # 2) Si el extractor decide que hace falta OCR (ej. text_length < threshold)
    if result["ocr_needed"]:
        # Ejecuta OCR con modelo vision en Ollama.
        # ocr_pdf típicamente devuelve: (texto, ruta_artefacto)
        text, artifact_path = ocr_pdf(state["path"])

        # Guardamos texto y marcamos que usamos OCR
        state["text"] = text
        state["ocr_used"] = True

        # Opcional: guarda o registra artifact_path en state para trazabilidad
        # state["text_artifact"] = artifact_path  # (si lo añades al TypedDict)

    else:
        # 3) Si NO hace falta OCR, usamos el texto extraído directamente
        text = result["text"]

        # Guardamos en state
        state["text"] = text
        state["ocr_used"] = False

        # 4) Guardamos artefacto raw en tmp/ para reproducibilidad
        # save_text_artifact(path, text, "raw") suele devolver la ruta del fichero
        _artifact_path = save_text_artifact(state["path"], text, "raw")

        # Opcional: guardar el path
        # state["text_artifact"] = _artifact_path  # (si lo añades al TypedDict)

    # 5) Devolvemos el state actualizado para el siguiente nodo
    return state


def clean_node(state: DocumentState) -> DocumentState:
    """
    Nodo 2: Limpia/normaliza el texto.
    """

    # 1) Limpiamos el texto (normalización de espacios, caracteres raros, etc.)
    state["clean_text"] = clean_text(state["text"])

    # 2) Devolvemos estado actualizado
    return state


    """
    Nodo 4: Genera embeddings por chunk y los deja en state["embeddings"].
    """

    # 1) Reutilizamos tu función embed_chunks(doc)
    # embed_chunks espera algo con doc_id (sha256) y chunks.
    # Le pasamos un dict "tipo doc" mínimo.
    doc_like = {
        "sha256": state["sha256"],
        "chunks": state["chunks"],
    }

    # 2) Genera embeddings (lista de vectores/objetos)
    vectors = embed_chunks(doc_like)

    # 3) Guardamos en el estado
    state["embeddings"] = vectors

    # 4) Devolvemos estado para quien lo consuma (main)
    return state