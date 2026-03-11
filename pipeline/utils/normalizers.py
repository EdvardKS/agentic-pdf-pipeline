"""
Funciones puras de normalización y validación de valores extraídos por el LLM.
"""

import re

# Meses en español → número
_MESES = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12",
}

# Países de la UE/EEE para determinar tipo gravamen IRNR
PAISES_UE_EEE = {
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES",
    "FI", "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV",
    "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK",
    "IS", "LI", "NO",  # EEE
}


# ---------------------------------------------------------------------------
# Números
# ---------------------------------------------------------------------------

def parse_number(value) -> float:
    """
    Convierte una cadena numérica a float, detectando formato europeo y americano.

    Formato europeo: 38.570,34  →  38570.34  (punto=miles, coma=decimal)
    Formato europeo: 38.570     →  38570     (solo miles sin decimales)
    Formato americano: 38,570.34 → 38570.34
    Sin separadores: 38570.34  → 38570.34
    """
    if value is None:
        return 0.0
    s = str(value).strip()
    if not s:
        return 0.0

    # Detectar formato europeo: dígitos, punto cada 3, coma decimal al final
    if re.match(r'^\d{1,3}(\.\d{3})+(,\d+)?$', s):
        s = s.replace(".", "").replace(",", ".")
    # Detectar formato europeo sin decimales pero con punto de miles: "150.000"
    elif re.match(r'^\d{1,3}(\.\d{3})+$', s):
        s = s.replace(".", "")
    else:
        # Quitar comas de miles americanas y espacios
        s = s.replace(",", "").replace(" ", "")

    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def format_number_es(value: float, decimals: int = 2) -> str:
    """Formatea un número en formato español: 38.570,34"""
    formatted = f"{value:,.{decimals}f}"
    # Python usa coma para miles y punto para decimales (en locale en_US)
    # Convertir: 38,570.34 → 38.570,34
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------------------
# NIFs / NIEs
# ---------------------------------------------------------------------------

def normalize_nif(value: str) -> str:
    """Elimina guiones, espacios y pone en mayúsculas."""
    if not value:
        return ""
    return re.sub(r'[\s\-\.]', '', str(value)).upper()


def validate_nif(value: str) -> bool:
    """Valida formato NIF español: 8 dígitos + letra."""
    v = normalize_nif(value)
    return bool(re.match(r'^\d{8}[A-Z]$', v))


def validate_nie(value: str) -> bool:
    """Valida formato NIE español: X/Y/Z + 7 dígitos + letra."""
    v = normalize_nif(value)
    return bool(re.match(r'^[XYZ]\d{7}[A-Z]$', v))


def validate_cif(value: str) -> bool:
    """Valida formato CIF español (empresas): letra + 7 dígitos + dígito/letra."""
    v = normalize_nif(value)
    return bool(re.match(r'^[ABCDEFGHJKLMNPQRSUVW]\d{7}[0-9A-J]$', v))


def is_valid_identifier(value: str) -> bool:
    """Acepta NIF, NIE o CIF (o identificación extranjera de al menos 5 chars)."""
    v = normalize_nif(value)
    if not v or len(v) < 5:
        return False
    return validate_nif(v) or validate_nie(v) or validate_cif(v) or len(v) >= 5


# ---------------------------------------------------------------------------
# Fechas
# ---------------------------------------------------------------------------

def validate_date(value: str) -> bool:
    """Verifica que la fecha esté en formato YYYY-MM-DD."""
    if not value:
        return False
    return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', str(value).strip()))


def normalize_date(value: str) -> str:
    """
    Intenta convertir fechas en múltiples formatos a YYYY-MM-DD.
    Acepta:
      - "2024-03-12"           → "2024-03-12"
      - "12/03/2024"           → "2024-03-12"
      - "12 de marzo de 2024"  → "2024-03-12"
      - "12-03-2024"           → "2024-03-12"
    """
    if not value:
        return ""
    s = str(value).strip()

    # Ya en formato ISO
    if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
        return s

    # DD/MM/YYYY o DD-MM-YYYY
    m = re.match(r'^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$', s)
    if m:
        return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"

    # "12 de marzo de 2024" o "12 de marzo 2024"
    m = re.match(
        r'^(\d{1,2})\s+de\s+(\w+)\s+(?:de\s+)?(\d{4})$',
        s,
        re.IGNORECASE
    )
    if m:
        mes_str = m.group(2).lower()
        mes_num = _MESES.get(mes_str)
        if mes_num:
            return f"{m.group(3)}-{mes_num}-{m.group(1).zfill(2)}"

    return s  # devolver tal cual si no se puede normalizar


def date_to_parts(date_str: str) -> tuple:
    """Devuelve (año, mes, día) de una fecha YYYY-MM-DD. Vacíos si inválida."""
    if not validate_date(date_str):
        return ("", "", "")
    parts = date_str.split("-")
    return (parts[0], parts[1], parts[2])


# ---------------------------------------------------------------------------
# Período trimestral AEAT
# ---------------------------------------------------------------------------

def periodo_trimestral(date_str: str) -> str:
    """Devuelve '1T', '2T', '3T' o '4T' según el mes de la fecha."""
    if not validate_date(date_str):
        return ""
    try:
        mes = int(date_str.split("-")[1])
        if mes <= 3:
            return "1T"
        elif mes <= 6:
            return "2T"
        elif mes <= 9:
            return "3T"
        else:
            return "4T"
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Tipo gravamen IRNR
# ---------------------------------------------------------------------------

def tipo_gravamen_irnr(pais_residencia: str) -> float:
    """
    Devuelve el tipo impositivo IRNR según país de residencia.
    UE/EEE → 19%, resto → 24%.
    """
    pais = str(pais_residencia).strip().upper()
    return 19.0 if pais in PAISES_UE_EEE else 24.0


# ---------------------------------------------------------------------------
# Warnings
# ---------------------------------------------------------------------------

def check_warnings(data: dict, model_name: str) -> list:
    """
    Retorna lista de warnings (campos importantes vacíos).
    No bloquea el pipeline.
    """
    warnings = []

    campos_criticos = {
        "aeat_211": [
            "retenedor_nif", "transmitente_nr_nif",
            "transmitente_nr_pais_residencia", "contraprestacion"
        ],
        "aeat_210": [
            "declarante_nif", "declarante_pais_residencia",
            "valor_transmision", "fecha_transmision"
        ],
        "andalucia_600": [
            "sujeto_pasivo_nif", "inmueble_referencia_catastral", "valor_inmueble"
        ],
        "valencia_600": [
            "sujeto_pasivo_nif", "inmueble_referencia_catastral", "valor_inmueble"
        ],
        "murcia_600": [
            "sujeto_pasivo_nif", "inmueble_referencia_catastral", "valor_inmueble"
        ],
    }

    criticos = campos_criticos.get(model_name, [])
    for campo in criticos:
        if not data.get(campo):
            warnings.append(f"ADVERTENCIA: campo crítico '{campo}' está vacío")

    return warnings
