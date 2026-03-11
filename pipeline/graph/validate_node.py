"""
Nodo de validación y normalización del pipeline LangGraph.

Posición en el grafo: schema_extract → validate → [exportar]

Responsabilidades:
1. Normalizar todos los campos extraídos (números, fechas, NIFs)
2. Calcular campos derivados si están vacíos (retencion_3pct, cuota, periodo, etc.)
3. Registrar warnings de campos críticos vacíos (no bloquea el pipeline)
4. Guardar resultado en state["validated_data"]
"""

import json
from pipeline.utils.normalizers import (
    parse_number,
    normalize_nif,
    normalize_date,
    validate_date,
    periodo_trimestral,
    tipo_gravamen_irnr,
    check_warnings,
)

YELLOW = "\033[93m"
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"


def validate_node(state: dict) -> dict:
    extraction_log = state.get("extraction_log", [])
    if not extraction_log:
        print(f"{RED}[validate_node] Sin datos en extraction_log{RESET}")
        state["validated_data"] = {}
        return state

    raw = extraction_log[-1]
    schema = state.get("schema") or {}
    fields_def = schema.get("fields", {})
    model_name = schema.get("document_type", "")

    print(f"\n{CYAN}[validate_node] Normalizando {len(raw)} campos...{RESET}")

    validated = {}

    for field_name, raw_value in raw.items():
        field_def = fields_def.get(field_name, {})
        field_type = field_def.get("type", "string")

        if field_type == "number":
            validated[field_name] = parse_number(raw_value)
        elif field_type == "date":
            validated[field_name] = normalize_date(str(raw_value) if raw_value else "")
        elif field_name.endswith("_nif") or field_name.endswith("_nie"):
            validated[field_name] = normalize_nif(str(raw_value) if raw_value else "")
        else:
            validated[field_name] = str(raw_value) if raw_value is not None else ""

    # -----------------------------------------------------------------------
    # Cálculos derivados según tipo de modelo
    # -----------------------------------------------------------------------
    _compute_derived(validated, model_name)

    # -----------------------------------------------------------------------
    # Warnings de campos críticos vacíos
    # -----------------------------------------------------------------------
    warnings = check_warnings(validated, model_name)
    if warnings:
        for w in warnings:
            print(f"  {YELLOW}{w}{RESET}")
    else:
        print(f"  {GREEN}Sin advertencias críticas{RESET}")

    print(f"\n{GREEN}[validate_node] Datos validados:{RESET}")
    print(json.dumps(validated, indent=2, ensure_ascii=False, default=str))

    state["validated_data"] = validated
    return state


def _compute_derived(data: dict, model_name: str) -> None:
    """
    Calcula campos derivados in-place en data.
    Modifica el dict directamente.
    """

    # --- AEAT 211 ---
    if "aeat_211" in model_name or "modelo_211" in model_name:
        contraprestacion = parse_number(data.get("contraprestacion", 0))
        retencion = parse_number(data.get("retencion_3pct", 0))

        if contraprestacion and not retencion:
            retencion = round(contraprestacion * 0.03, 2)
            data["retencion_3pct"] = retencion
            print(f"  {YELLOW}[derivado] retencion_3pct calculada: {retencion}{RESET}")

        # Normalizar contraprestación (puede venir en formato europeo)
        if contraprestacion:
            data["contraprestacion"] = contraprestacion

        # Ejercicio desde fecha_transmision si no está
        if not data.get("ejercicio") and data.get("fecha_transmision"):
            fecha = normalize_date(data["fecha_transmision"])
            if validate_date(fecha):
                data["ejercicio"] = fecha[:4]
                print(f"  {YELLOW}[derivado] ejercicio={data['ejercicio']}{RESET}")

        # Periodo siempre 0A para 211
        if not data.get("periodo"):
            data["periodo"] = "0A"

        # Fallback NIF: si retenedor_nif vacío, no hay fallback automático pero se logea
        retenedor_nif = normalize_nif(data.get("retenedor_nif", ""))
        if retenedor_nif:
            data["retenedor_nif"] = retenedor_nif

    # --- AEAT 210 ---
    elif "aeat_210" in model_name or "modelo_210" in model_name:
        valor_adq = parse_number(data.get("valor_adquisicion", 0))
        valor_trans = parse_number(data.get("valor_transmision", 0))

        if valor_adq:
            data["valor_adquisicion"] = valor_adq
        if valor_trans:
            data["valor_transmision"] = valor_trans

        incremento = parse_number(data.get("incremento_patrimonial", 0))
        if not incremento and valor_trans and valor_adq:
            incremento = round(valor_trans - valor_adq, 2)
            data["incremento_patrimonial"] = incremento
            print(f"  {YELLOW}[derivado] incremento_patrimonial calculado: {incremento}{RESET}")

        pais = str(data.get("declarante_pais_residencia", "")).upper()
        tipo = parse_number(data.get("tipo_gravamen_aplicable", 0))
        if not tipo and pais:
            tipo = tipo_gravamen_irnr(pais)
            data["tipo_gravamen_aplicable"] = tipo
            print(f"  {YELLOW}[derivado] tipo_gravamen_aplicable={tipo}% (país {pais}){RESET}")

        cuota = parse_number(data.get("cuota_resultante", 0))
        if not cuota and incremento and tipo:
            cuota = round(incremento * tipo / 100, 2)
            data["cuota_resultante"] = cuota
            print(f"  {YELLOW}[derivado] cuota_resultante calculada: {cuota}{RESET}")

        retencion_211 = parse_number(data.get("retencion_modelo_211", 0))
        if not retencion_211 and valor_trans:
            retencion_211 = round(valor_trans * 0.03, 2)
            data["retencion_modelo_211"] = retencion_211
            print(f"  {YELLOW}[derivado] retencion_modelo_211 calculada: {retencion_211}{RESET}")

        cuota_dif = parse_number(data.get("cuota_diferencial", 0))
        if not cuota_dif and cuota is not None:
            cuota_dif = round(cuota - retencion_211, 2)
            data["cuota_diferencial"] = cuota_dif
            print(f"  {YELLOW}[derivado] cuota_diferencial calculada: {cuota_dif}{RESET}")

        # Período trimestral
        if not data.get("periodo") and data.get("fecha_transmision"):
            fecha = normalize_date(data["fecha_transmision"])
            if validate_date(fecha):
                data["fecha_transmision"] = fecha
                data["periodo"] = periodo_trimestral(fecha)
                data["ejercicio"] = fecha[:4]
                print(f"  {YELLOW}[derivado] periodo={data['periodo']}, ejercicio={data['ejercicio']}{RESET}")

    # --- Modelos 600 autonómicos ---
    else:
        valor = parse_number(data.get("valor_inmueble", 0))
        if valor:
            data["valor_inmueble"] = valor

        pct = parse_number(data.get("porcentaje_transmitido", 100))
        if not pct:
            pct = 100.0
        data["porcentaje_transmitido"] = pct

        tipo = parse_number(data.get("tipo_gravamen", 0))
        base = round(valor * pct / 100, 2) if valor else 0
        if base and not data.get("base_imponible"):
            data["base_imponible"] = base

        if base and tipo and not data.get("cuota_tributaria"):
            cuota = round(base * tipo / 100, 2)
            data["cuota_tributaria"] = cuota
            print(f"  {YELLOW}[derivado] cuota_tributaria calculada: {cuota}{RESET}")

    # Normalizar fecha_devengo / fecha_transmision si presentes
    for campo_fecha in ["fecha_devengo", "fecha_transmision", "fecha_adquisicion"]:
        if data.get(campo_fecha):
            fecha_norm = normalize_date(str(data[campo_fecha]))
            if fecha_norm:
                data[campo_fecha] = fecha_norm
