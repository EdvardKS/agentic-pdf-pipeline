import json
from pathlib import Path
import re

from pipeline.schema_loader import build_extraction_prompt
from pipeline.ollama_client import client, CHAT_MODEL


def append_result(file_path, data):

    with open(file_path, "r", encoding="utf-8") as f:
        content = json.load(f)

    content.append(data)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=2, ensure_ascii=False)


def schema_extract_node(state):

    text = state["clean_text"]

    prompt = build_extraction_prompt(text)

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

    # limpiar markdown ```json
    clean_output = re.sub(r"```json|```", "", raw_output).strip()

    try:
        extracted = json.loads(clean_output)
    except Exception:
        extracted = {
            "error": "json_parse_failed",
            "raw_response": raw_output
        }

    # mantener log en estado
    if "extraction_log" not in state:
        state["extraction_log"] = []

    state["extraction_log"].append(extracted)

    # guardar directamente en outputs JSON
    output_file = state.get("output_file")

    if output_file:
        append_result(output_file, extracted)

    return state