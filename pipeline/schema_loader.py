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

Reglas IMPORTANTES:
- Debes devolver TODOS los campos.
- No uses null.
- Si un campo no aparece claramente, busca la mejor aproximación en el documento.
- Si no es posible encontrarlo, devuelve una cadena vacía "".

Devuelve SOLO JSON válido con esta estructura:

{{
  "nombre_cliente": "",
  "fecha_contrato": "",
  "direccion_inmueble": ""
}}

NO uses markdown.
NO uses ```json.

DOCUMENTO:
{text}
"""

    return prompt