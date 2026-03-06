import json
from pathlib import Path

SCHEMA_PATH = Path("pipeline/schemas/contract_schema.json")


def load_schema():
    """
    Carga el schema de extracción.
    """
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_extraction_prompt(text: str):

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

    prompt = f""" 
Extrae del documento los siguientes campos.

{fields_prompt}

REGLAS OBLIGATORIAS:

1. Debes devolver EXCLUSIVAMENTE un JSON válido.
2. No escribas explicaciones.
3. No uses listas con *.
4. No uses markdown.
5. No escribas texto antes ni después del JSON.

Formato exacto requerido:

{{
 "nombre_cliente": "...",
 "fecha_contrato": "...",
 "direccion_inmueble": "..."
}}

DOCUMENTO:
{text}
"""

    return prompt