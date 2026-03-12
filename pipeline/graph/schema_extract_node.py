import json
import re

from pipeline.schema_loader import build_extraction_prompt, is_array_schema
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


def validate_extraction(data: dict, schema: dict) -> list:
    errors = []

    if is_array_schema(schema):
        output_key = schema["output_key"]
        if output_key not in data:
            errors.append(f"Falta la clave '{output_key}' en el JSON")
        elif not isinstance(data[output_key], list):
            errors.append(f"'{output_key}' debe ser un array, no {type(data[output_key]).__name__}")
        elif len(data[output_key]) == 0:
            errors.append(f"'{output_key}' es un array vacio - debe contener al menos una persona")
        else:
            for i, item in enumerate(data[output_key]):
                if not item.get("nombre_completo"):
                    errors.append(f"Item {i}: falta 'nombre_completo'")
                if not item.get("rol"):
                    errors.append(f"Item {i}: falta 'rol'")
    else:
        fields_def = schema.get("fields", {})
        for field, field_def in fields_def.items():
            if field_def.get("required") is False:
                continue
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
    except json.JSONDecodeError:
        try:
            def remove_duplicates(pairs):
                seen = {}
                for k, v in pairs:
                    seen[k] = v
                return seen
            return json.loads(json_text, object_pairs_hook=remove_duplicates)
        except Exception:
            return {}


def _build_correction_prompt(schema: dict, extracted: dict, errors: list, text: str) -> str:
    if is_array_schema(schema):
        output_key = schema["output_key"]
        item_fields = schema["fields"][output_key].get("item_fields", {})
        item_keys = ",\n      ".join([
            '"{k}": {v}'.format(
                k=k,
                v="false" if v.get("type") == "boolean" else '""'
            )
            for k, v in item_fields.items()
        ])
        item_template = '{\n      ' + item_keys + '\n    }'
        return (
            "\nLa extraccion anterior es incorrecta y debe corregirse.\n\n"
            "ERRORES DETECTADOS:\n" + str(errors) + "\n\n"
            "RESULTADO ANTERIOR:\n" + json.dumps(extracted, ensure_ascii=False, indent=2) + "\n\n"
            "INSTRUCCIONES:\n"
            "1. Devuelve EXCLUSIVAMENTE un JSON con la clave \"" + output_key + "\" conteniendo un array.\n"
            "2. Incluye TODAS las personas del documento.\n"
            "3. Cada persona debe tener al menos \"nombre_completo\" y \"rol\".\n"
            "4. No escribas texto fuera del JSON. No uses markdown.\n"
            "5. Usa \"\" para strings vacios y false para booleans.\n\n"
            "FORMATO EXACTO:\n"
            "{\n  \"" + output_key + "\": [\n    " + item_template + "\n  ]\n}\n\n"
            "DOCUMENTO:\n" + text
        )
    else:
        required_fields = list(schema.get("fields", {}).keys())
        correction_template_keys = ",\n  ".join(['"{k}": ""'.format(k=k) for k in required_fields])
        correction_template = "{\n  " + correction_template_keys + "\n}"
        return (
            "\nLa extraccion anterior es incorrecta y debe corregirse.\n\n"
            "CAMPOS OBLIGATORIOS:\n" + str(required_fields) + "\n\n"
            "ERRORES DETECTADOS:\n" + str(errors) + "\n\n"
            "RESULTADO ANTERIOR:\n" + json.dumps(extracted, ensure_ascii=False, indent=2) + "\n\n"
            "INSTRUCCIONES OBLIGATORIAS:\n"
            "1. Corrige SOLO los campos incorrectos o ausentes.\n"
            "2. Devuelve TODOS los campos obligatorios.\n"
            "3. Devuelve EXCLUSIVAMENTE un JSON valido.\n"
            "4. No escribas explicaciones ni markdown.\n"
            "5. No uses null. Si no encuentras un valor, devuelve cadena vacia \"\".\n\n"
            "Formato exacto requerido:\n" + correction_template + "\n\n"
            "DOCUMENTO:\n" + text
        )


def schema_extract_node(state):
    text = state["clean_text"]
    schema = state.get("schema") or {}

    if is_array_schema(schema):
        output_key = schema["output_key"]
        item_fields = list(schema["fields"][output_key].get("item_fields", {}).keys())
        print(f"\n{YELLOW}MODO ARRAY — output_key: '{output_key}'{RESET}")
        print(f"{YELLOW}ITEM FIELDS:{RESET} {item_fields}")
    else:
        required_fields = list(schema.get("fields", {}).keys())
        print(f"\n{YELLOW}SCHEMA FIELDS:{RESET} {required_fields}")

    prompt = build_extraction_prompt(text, schema)

    attempt = 0
    extracted = {}

    while attempt < MAX_RETRIES:
        print(f"\n{CYAN}==================== ATTEMPT {attempt + 1}/{MAX_RETRIES} ===================={RESET}")

        stream = client.chat(
            model=CHAT_MODEL,
            stream=True,
            options={"temperature": 0},
            messages=[{"role": "user", "content": prompt}]
        )

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
            print(f"{RED}No se pudo parsear JSON valido.{RESET}")

        errors = validate_extraction(extracted, schema)

        if not errors:
            print(f"\n{GREEN}VALIDACION OK{RESET}")
            break

        print(f"\n{YELLOW}VALIDATION FAILED:{RESET} {errors}")
        prompt = _build_correction_prompt(schema, extracted, errors, text)
        attempt += 1

    if "extraction_log" not in state:
        state["extraction_log"] = []

    state["extraction_log"].append(extracted)

    output_file = state.get("output_file")
    if output_file:
        append_result(output_file, extracted)

    return state
