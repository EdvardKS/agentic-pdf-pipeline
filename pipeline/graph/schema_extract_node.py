import json
from pathlib import Path
import re

from pipeline.schema_loader import build_extraction_prompt, load_schema
from pipeline.ollama_client import client, CHAT_MODEL


MAX_RETRIES = 3


def append_result(file_path, data):

    with open(file_path, "r", encoding="utf-8") as f:
        content = json.load(f)

    content.append(data)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=2, ensure_ascii=False)


def validate_extraction(data, required_fields):

    errors = []

    for field in required_fields:

        if field not in data:
            errors.append(f"{field} missing")

        elif data[field] in [None, "", "null"]:
            errors.append(f"{field} empty")

    return errors


def schema_extract_node(state):

    text = state["clean_text"]

    prompt = build_extraction_prompt(text)

    # cargar schema dinámicamente
    schema = load_schema()
    required_fields = list(schema["fields"].keys())
    print("SCHEMA FIELDS:", required_fields)
    attempt = 0
    extracted = {}

    while attempt < MAX_RETRIES:

        response = client.chat(
            model=CHAT_MODEL, # type: ignore
            messages=[{
                "role": "user",
                "content": prompt
            }]
        ) # type: ignore

        raw_output = response["message"]["content"]

        print("\nLLM RESPONSE:")
        print(raw_output)

        clean_output = re.sub(r"```json|```", "", raw_output).strip()

        try:
            extracted = json.loads(clean_output)
        except Exception:
            extracted = {}

        errors = validate_extraction(extracted, required_fields)

        if not errors:
            break

        print("VALIDATION FAILED:", errors)

        prompt = f"""
La extracción anterior tiene errores.

Errores detectados:
{errors}

Resultado anterior:
{extracted}

Debes corregir SOLO los campos incorrectos usando el documento.

Documento:
{text}

Devuelve SOLO JSON válido.
"""

        attempt += 1

    # mantener log en estado
    if "extraction_log" not in state:
        state["extraction_log"] = []

    state["extraction_log"].append(extracted)

    # guardar directamente en outputs JSON
    output_file = state.get("output_file")

    if output_file:
        append_result(output_file, extracted)

    return state