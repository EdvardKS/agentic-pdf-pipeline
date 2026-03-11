from typing import TypedDict, List, Any, Dict

# DocumentState define la "forma" del estado que viaja por el grafo.
# TypedDict sirve para tipado/autocompletado; en runtime sigue siendo un dict.
class DocumentState(TypedDict):
    # Ruta del PDF a procesar
    path: str

    # Hash del documento (sirve como doc_id estable)
    sha256: str

    # Texto extraído (raw u OCR)
    text: str

    # Texto limpio/normalizado
    clean_text: str

    # Lista de chunks (strings)
    chunks: List[str]

    # Lista de vectores/objetos embedding por chunk (depende de tu diseño)
    # Normalmente aquí guardas: [{doc_id, chunk_id, text, embedding}, ...]
    embeddings: List[Any]

    # Flag para saber si se usó OCR
    ocr_used: bool

    # Ruta al archivo JSON de salida donde se guardan las extracciones
    output_file: str

    # Log de resultados extraídos por los nodos
    extraction_log: List[Any]

    # Schema dinámico cargado según el modelo seleccionado
    schema: Dict[str, Any]

    # Key del modelo fiscal seleccionado ("1"…"5")
    selected_model: str

    # Datos normalizados y validados tras el nodo de validación
    validated_data: Dict[str, Any]
    
    
    
    