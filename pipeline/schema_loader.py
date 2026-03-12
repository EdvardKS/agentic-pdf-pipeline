import json
from pathlib import Path


def load_schema(schema_path: str = "pipeline/schemas/contract_schema.json") -> dict:
    """Carga el schema de extracción desde la ruta indicada."""
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_array_schema(schema: dict) -> bool:
    """Devuelve True si el schema usa output_key (extracción de arrays)."""
    return bool(schema.get("output_key"))


def build_extraction_prompt(text: str, schema: dict = None) -> str:
    """
    Construye el prompt de extracción a partir del schema.
    Soporta schemas planos (dict) y schemas de array (output_key definido).
    """
    if schema is None:
        schema = load_schema()

    if is_array_schema(schema):
        return _build_array_prompt(text, schema)
    else:
        return _build_flat_prompt(text, schema)


def _build_policy_block(schema: dict) -> str:
    """Construye el bloque de instrucciones de extraction_policy si existe."""
    policy = schema.get("extraction_policy", {})
    if not policy:
        return ""

    lines = []
    if policy.get("null_if_missing"):
        lines.append("- Si un campo NO aparece en el documento, devuelve null (no cadena vacía).")
    if policy.get("do_not_infer_unknown_values"):
        lines.append("- NO inferir valores. Extrae SOLO lo que está explícitamente en el texto.")
    if policy.get("do_not_calculate_tax_fields_without_source"):
        lines.append("- NO calcular campos fiscales (cuota, tipo gravamen, base imponible) si no aparecen en el documento.")
    if policy.get("normalize_dates_to"):
        lines.append(f"- Normalizar todas las fechas al formato {policy['normalize_dates_to']}.")
    if policy.get("for_legal_entities"):
        lines.append(f"- Personas jurídicas: {policy['for_legal_entities']}.")

    if not lines:
        return ""
    return "POLÍTICA DE EXTRACCIÓN:\n" + "\n".join(lines)


def _build_flat_prompt(text: str, schema: dict) -> str:
    """Prompt estándar para schemas de campo plano."""
    fields = schema["fields"]
    policy_block = _build_policy_block(schema)

    prompt_sections = []
    for field_name, field_data in fields.items():
        description = field_data.get("description", "")
        field_type = field_data.get("type", "")
        fmt = field_data.get("format", "")
        examples = field_data.get("examples", [])
        rules = field_data.get("rules", [])
        options = field_data.get("options", [])
        is_required = field_data.get("required", True)

        # Añadir indicador opcional
        required_tag = "" if is_required is not False else " [OPCIONAL]"

        # Añadir opciones válidas si es enum
        options_text = ""
        if options:
            options_text = f"Opciones válidas: {', '.join(options)}"

        example_text = "\n".join([f"- {e}" for e in examples])
        rules_text = "\n".join([f"- {r}" for r in rules]) if rules else ""

        reglas_bloque = ("Reglas:\n" + rules_text) if rules_text else ""
        opciones_bloque = options_text if options_text else ""

        section = f"""
CAMPO: {field_name}{required_tag}
Tipo: {field_type}
Formato esperado: {fmt}
Descripción: {description}
{opciones_bloque}
{reglas_bloque}
Ejemplos válidos:
{example_text}
"""
        prompt_sections.append(section)

    fields_prompt = "\n".join(prompt_sections)

    # Plantilla JSON: arrays usan [], booleans usan false, resto usan "..."
    template_parts = []
    for k, v in fields.items():
        ftype = v.get("type", "string")
        if ftype == "array":
            template_parts.append(f'"{k}": []')
        elif ftype == "boolean":
            template_parts.append(f'"{k}": false')
        elif ftype in ("number", "integer"):
            template_parts.append(f'"{k}": null')
        else:
            template_parts.append(f'"{k}": null')
    json_template_keys = ",\n  ".join(template_parts)
    json_template = "{\n  " + json_template_keys + "\n}"

    # Reglas de output según si hay política null_if_missing
    policy = schema.get("extraction_policy", {})
    null_rule = "null" if policy.get("null_if_missing") else "cadena vacía \"\""
    policy_section = f"\n{policy_block}\n" if policy_block else ""

    return f"""
Extrae del documento los siguientes campos.
{policy_section}
{fields_prompt}

REGLAS OBLIGATORIAS:

1. Debes devolver EXCLUSIVAMENTE un JSON válido.
2. No escribas explicaciones.
3. No uses listas con *.
4. No uses markdown.
5. No escribas texto antes ni después del JSON.
6. Si un campo no se encuentra en el documento, devuelve {null_rule}.
7. Los campos tipo array devuelven [] si no hay datos.
8. Los campos tipo boolean devuelven true o false (sin comillas).

Formato exacto requerido:

{json_template}

DOCUMENTO:
{text}
"""


def _build_array_prompt(text: str, schema: dict) -> str:
    """Prompt para schemas de array (extracción de múltiples objetos)."""
    output_key = schema["output_key"]
    description = schema.get("description", "")
    instructions = schema.get("extraction_instructions", [])
    item_fields = schema["fields"][output_key].get("item_fields", {})

    # Construir descripción de cada campo del item
    field_descriptions = []
    for field_name, field_data in item_fields.items():
        ftype = field_data.get("type", "string")
        fdesc = field_data.get("description", "")
        fexamples = field_data.get("examples", [])
        frules = field_data.get("rules", [])
        ftext_ex = field_data.get("text_examples", [])

        ex_str = ", ".join([f'"{e}"' for e in fexamples[:4]]) if fexamples else ""
        rules_str = "\n    ".join([f"- {r}" for r in frules]) if frules else ""
        text_ex_str = ""
        if ftext_ex:
            text_ex_str = "    Ejemplos en texto: " + " | ".join(
                [f'"{t["text"][:60]}" → "{t["value"]}"' for t in ftext_ex[:2]]
            )

        field_descriptions.append(
            f'  "{field_name}" ({ftype}): {fdesc}'
            + (f'\n    Ejemplos: {ex_str}' if ex_str else '')
            + (f'\n    Reglas:\n    {rules_str}' if rules_str else '')
            + (f'\n    {text_ex_str}' if text_ex_str else '')
        )

    fields_str = "\n".join(field_descriptions)

    # Instrucciones especiales del schema
    instructions_str = "\n".join([f"{i+1}. {instr}" for i, instr in enumerate(instructions)])

    # Plantilla de un item para que el modelo sepa el formato exacto
    _empty_val = '""'
    item_template_keys = ",\n      ".join([
        f'"{k}": {"false" if v.get("type") == "boolean" else _empty_val}'
        for k, v in item_fields.items()
    ])
    item_template = '{\n      ' + item_template_keys + '\n    }'

    return f"""
{description}

INSTRUCCIONES OBLIGATORIAS:
{instructions_str}

CAMPOS A EXTRAER POR CADA PERSONA:

{fields_str}

REGLAS GENERALES:
- Devuelve EXCLUSIVAMENTE un JSON válido con la clave "{output_key}" conteniendo un array.
- No escribas explicaciones, comentarios ni texto fuera del JSON.
- No uses markdown ni bloques de código.
- Si un campo no aparece, usa "" para strings y false para booleans.
- Incluye TODAS las personas del documento, sin excepción.

FORMATO EXACTO REQUERIDO:

{{
  "{output_key}": [
    {item_template},
    {item_template}
  ]
}}

DOCUMENTO:
{text}
"""
