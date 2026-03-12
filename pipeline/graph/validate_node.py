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
from pipeline.schema_loader import is_array_schema
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


def _normalize_cliente(cliente: dict) -> dict:
    """Normaliza los campos de un objeto cliente individual."""
    out = {}
    for k, v in cliente.items():
        if k == "nif_nie_cif":
            out[k] = normalize_nif(str(v) if v else "")
        elif k == "fecha_nacimiento":
            out[k] = normalize_date(str(v) if v else "")
        elif k == "es_no_residente":
            if isinstance(v, bool):
                out[k] = v
            else:
                out[k] = str(v).lower() in ("true", "1", "yes", "si", "sí")
        else:
            out[k] = str(v) if v is not None else ""
    # Inferir es_no_residente si no está explícito
    if "es_no_residente" not in out:
        pais = out.get("pais_domicilio", "").lower()
        out["es_no_residente"] = bool(pais) and "españa" not in pais and "spain" not in pais
    return out


def validate_node(state: dict) -> dict:
    extraction_log = state.get("extraction_log", [])
    if not extraction_log:
        print(f"{RED}[validate_node] Sin datos en extraction_log{RESET}")
        state["validated_data"] = {}
        return state

    raw = extraction_log[-1]
    schema = state.get("schema") or {}
    model_name = schema.get("document_type", "")

    # -----------------------------------------------------------------------
    # Rama para schemas de array (extraccion_clientes)
    # -----------------------------------------------------------------------
    if is_array_schema(schema):
        output_key = schema["output_key"]
        clientes_raw = raw.get(output_key, [])
        print(f"\n{CYAN}[validate_node] Normalizando array '{output_key}': {len(clientes_raw)} items{RESET}")
        clientes_validados = [_normalize_cliente(c) for c in clientes_raw]
        print(f"  {GREEN}Clientes normalizados: {len(clientes_validados)}{RESET}")
        state["validated_data"] = {output_key: clientes_validados}
        return state

    # -----------------------------------------------------------------------
    # Rama para schemas planos (resto de modelos fiscales)
    # -----------------------------------------------------------------------
    fields_def = schema.get("fields", {})

    print(f"\n{CYAN}[validate_node] Normalizando {len(raw)} campos...{RESET}")

    validated = {}

    for field_name, raw_value in raw.items():
        field_def = fields_def.get(field_name, {})
        field_type = field_def.get("type", "string")

        if field_type in ("array",):
            # Preservar arrays tal como vienen del LLM
            validated[field_name] = raw_value if isinstance(raw_value, list) else ([] if raw_value is None else raw_value)
        elif field_type in ("number", "integer"):
            validated[field_name] = parse_number(raw_value)
        elif field_type == "date":
            validated[field_name] = normalize_date(str(raw_value) if raw_value else "")
        elif field_name.endswith("_nif") or field_name.endswith("_nie"):
            validated[field_name] = normalize_nif(str(raw_value) if raw_value else "")
        else:
            validated[field_name] = str(raw_value) if raw_value is not None else ""

    # -----------------------------------------------------------------------
    # Calculos derivados segun tipo de modelo
    # -----------------------------------------------------------------------
    _compute_derived(validated, model_name)

    # -----------------------------------------------------------------------
    # Warnings de campos criticos vacios
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

        # Periodo siempre 0A para modelo 210 (incremento patrimonial es anual)
        if not data.get("periodo"):
            data["periodo"] = "0A"
            print(f"  {YELLOW}[derivado] periodo=0A (incremento patrimonial: período anual){RESET}")

        # Ejercicio desde fecha_transmision si no está
        if not data.get("ejercicio") and data.get("fecha_transmision"):
            fecha = normalize_date(data["fecha_transmision"])
            if validate_date(fecha):
                data["fecha_transmision"] = fecha
                data["ejercicio"] = fecha[:4]
                print(f"  {YELLOW}[derivado] ejercicio={data['ejercicio']}{RESET}")

    # --- Modelos 600 autonómicos ---
    else:
        # Los nuevos schemas usan base_imponible directamente (extraída del documento)
        # Compatibilidad: si hubiera valor_inmueble del schema antiguo, usarlo como fallback
        base = parse_number(data.get("base_imponible") or data.get("valor_inmueble") or 0)
        pct = parse_number(data.get("porcentaje_transmitido", 0)) or 100.0
        tipo = parse_number(data.get("tipo_gravamen", 0))

        if base:
            # Aplicar porcentaje solo si no es 100% (ajuste del proindiviso)
            base_ajustada = round(base * pct / 100, 2) if pct != 100.0 else base
            data["base_imponible"] = base_ajustada

            if tipo and not parse_number(data.get("cuota_tributaria", 0)):
                cuota = round(base_ajustada * tipo / 100, 2)
                data["cuota_tributaria"] = cuota
                print(f"  {YELLOW}[derivado] cuota_tributaria calculada: {cuota}{RESET}")

    # Normalizar fecha_devengo / fecha_transmision si presentes
    for campo_fecha in ["fecha_devengo", "fecha_transmision", "fecha_adquisicion"]:
        if data.get(campo_fecha):
            fecha_norm = normalize_date(str(data[campo_fecha]))
            if fecha_norm:
                data[campo_fecha] = fecha_norm
