import json
import re

from pipeline.schema_loader import build_extraction_prompt
from pipeline.ollama_client import client, CHAT_MODEL


MAX_RETRIES = 3

BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"


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
        elif data[field] in [None, "null"]:
            errors.append(f"{field} empty")

    return errors


def extract_json_from_response(raw_output: str) -> dict:
    clean_output = re.sub(r"```json|```", "", raw_output).strip()

    json_match = re.search(r"\{.*\}", clean_output, re.DOTALL)

    if not json_match:
        return {}

    json_text = json_match.group(0)

    try:
        return json.loads(json_text)
    except Exception:
        return {}


def schema_extract_node(state):
    text = state["clean_text"]

    # Usar schema dinámico desde el estado; si no viene, usar dict vacío
    schema = state.get("schema") or {}
    required_fields = list(schema.get("fields", {}).keys())

    print(f"\n{YELLOW}SCHEMA FIELDS:{RESET} {required_fields}")

    prompt = build_extraction_prompt(text, schema)

    attempt = 0
    extracted = {}

    # Construir plantilla de corrección con campos reales
    correction_template_keys = ",\n  ".join([f'"{k}": ""' for k in required_fields])
    correction_template = "{\n  " + correction_template_keys + "\n}"

    while attempt < MAX_RETRIES:
        print(f"\n{CYAN}==================== ATTEMPT {attempt + 1}/{MAX_RETRIES} ===================={RESET}")

        stream = client.chat(
            model=CHAT_MODEL,  # type: ignore
            stream=True,
            options={"temperature": 0},
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )  # type: ignore

        raw_output = ""

        print(f"\n{BLUE}RESPUESTA DEL MODELO:{RESET}")
        for chunk in stream:
            content = chunk["message"].get("content", "")
            print(content, end="", flush=True)
            raw_output += content
        print()

        extracted = extract_json_from_response(raw_output)

        print(f"\n{MAGENTA}JSON PARSEADO:{RESET}")
        if extracted:
            print(json.dumps(extracted, indent=2, ensure_ascii=False))
        else:
            print(f"{RED}No se pudo parsear JSON válido.{RESET}")

        errors = validate_extraction(extracted, required_fields)

        if not errors:
            print(f"\n{GREEN}VALIDACIÓN OK{RESET}")
            break

        print(f"\n{YELLOW}VALIDATION FAILED:{RESET} {errors}")

        prompt = f"""
La extracción anterior es incorrecta y debe corregirse.

CAMPOS OBLIGATORIOS:
{required_fields}

ERRORES DETECTADOS:
{errors}

RESULTADO ANTERIOR:
{json.dumps(extracted, ensure_ascii=False, indent=2)}

INSTRUCCIONES OBLIGATORIAS:
1. Corrige SOLO los campos incorrectos o ausentes.
2. Debes devolver TODOS los campos obligatorios.
3. Devuelve EXCLUSIVAMENTE un JSON válido.
4. No escribas explicaciones.
5. No uses markdown.
6. No uses listas con *.
7. No escribas texto antes ni después del JSON.
8. No uses null. Si no encuentras un valor exacto, devuelve cadena vacía "".

Formato exacto requerido:
{correction_template}

DOCUMENTO:
{text}
"""
        attempt += 1

    if "extraction_log" not in state:
        state["extraction_log"] = []

    state["extraction_log"].append(extracted)

    output_file = state.get("output_file")

    if output_file:
        append_result(output_file, extracted)

    return state
