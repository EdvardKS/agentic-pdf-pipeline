import json
from pathlib import Path


def load_schema(schema_path: str = "pipeline/schemas/contract_schema.json") -> dict:
    """
    Carga el schema de extracción desde la ruta indicada.
    """
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_extraction_prompt(text: str, schema: dict = None) -> str:
    """
    Construye el prompt de extracción a partir del schema.
    Si no se pasa schema, carga el contrato por defecto.
    """
    if schema is None:
        schema = load_schema()

    fields = schema["fields"]

    prompt_sections = []

    for field_name, field_data in fields.items():

        description = field_data.get("description", "")
        field_type = field_data.get("type", "")
        fmt = field_data.get("format", "")
        examples = field_data.get("examples", [])

        example_text = "\n".join([f"- {e}" for e in examples])

        section = f"""
CAMPO: {field_name}
Tipo: {field_type}
Formato esperado: {fmt}

Descripción:
{description}

Ejemplos válidos:
{example_text}
"""
        prompt_sections.append(section)

    fields_prompt = "\n".join(prompt_sections)

    # Generar la plantilla JSON con los nombres de campo reales
    json_template_keys = ",\n  ".join([f'"{k}": "..."' for k in fields.keys()])
    json_template = "{\n  " + json_template_keys + "\n}"

    prompt = f"""
Extrae del documento los siguientes campos.

{fields_prompt}

REGLAS OBLIGATORIAS:

1. Debes devolver EXCLUSIVAMENTE un JSON válido.
2. No escribas explicaciones.
3. No uses listas con *.
4. No uses markdown.
5. No escribas texto antes ni después del JSON.
6. Si un campo no se encuentra en el documento, devuelve una cadena vacía "".

Formato exacto requerido:

{json_template}

DOCUMENTO:
{text}
"""

    return prompt
