import json
from pipeline.schema_loader import build_extraction_prompt
from pipeline.ollama_client import client, CHAT_MODEL


def schema_extract_node(state):
    """
    Nodo LangGraph encargado de extraer información estructurada
    usando el schema definido.
    """

    text = state["clean_text"]

    # construir prompt dinámico desde el schema
    prompt = build_extraction_prompt(text)

    response = client.chat(
        model=CHAT_MODEL, # type: ignore
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    ) # type: ignore

    raw_output = response["message"]["content"]

    # intentar parsear JSON
    try:
        extracted = json.loads(raw_output)
    except Exception:
        extracted = {
            "error": "json_parse_failed",
            "raw_response": raw_output
        }

    # inicializar log si no existe
    if "extraction_log" not in state:
        state["extraction_log"] = []

    # añadir nuevo resultado (no sobrescribir)
    state["extraction_log"].append(extracted)

    return state