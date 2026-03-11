"""
Exportador AEAT Modelo 210 - Incremento Patrimonial
Genera un fichero en formato texto estructurado compatible con el diseño de
registro publicado por la AEAT para el Modelo 210 (IRNR - Incremento patrimonial
por transmisión de inmueble por no residente).

Nombre del fichero: NIF_YYYY_periodo.210
Períodos: 1T, 2T, 3T, 4T (trimestral según fecha de transmisión)
"""

from pathlib import Path


def _float(value) -> float:
    try:
        return float(str(value).replace(",", ".").replace(" ", ""))
    except (ValueError, TypeError):
        return 0.0


def _fmt_importe(value, longitud=17) -> str:
    """Formatea un importe en céntimos (entero) con signo, relleno con ceros."""
    try:
        centimos = int(round(abs(_float(value)) * 100))
        signo = "N" if _float(value) < 0 else "P"
    except Exception:
        centimos = 0
        signo = "P"
    return signo + str(centimos).zfill(longitud)


def _pad(value, length, align="left") -> str:
    s = str(value) if value is not None else ""
    s = s[:length]
    if align == "left":
        return s.ljust(length)
    return s.rjust(length)


def _periodo_from_fecha(fecha: str) -> str:
    """Determina el período trimestral a partir de la fecha de transmisión."""
    try:
        mes = int(fecha.split("-")[1])
        if mes <= 3:
            return "1T"
        elif mes <= 6:
            return "2T"
        elif mes <= 9:
            return "3T"
        else:
            return "4T"
    except Exception:
        return "1T"


def export(data: dict, output_dir: str, doc: dict) -> str:
    """
    Genera un fichero .210 por documento y lo guarda en output_dir.
    Devuelve la ruta del fichero generado.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    nif = data.get("declarante_nif", "UNKNOWN").replace(" ", "").upper()
    ejercicio = str(data.get("ejercicio", "2024"))

    fecha_transmision = data.get("fecha_transmision", "")
    periodo = data.get("periodo") or _periodo_from_fecha(fecha_transmision)

    filename = f"{nif}_{ejercicio}_{periodo}.210"
    output_path = Path(output_dir) / filename

    # Cálculos derivados
    valor_adquisicion = _float(data.get("valor_adquisicion", 0))
    valor_transmision = _float(data.get("valor_transmision", 0))

    incremento = _float(data.get("incremento_patrimonial", 0))
    if incremento == 0 and valor_transmision > 0:
        incremento = valor_transmision - valor_adquisicion

    pais = data.get("declarante_pais_residencia", "").upper()
    tipo_gravamen = _float(data.get("tipo_gravamen_aplicable", 0))
    if tipo_gravamen == 0:
        # UE/EEE: 19%; resto: 24%
        paises_ue = {"AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES",
                     "FI", "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV",
                     "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK",
                     "IS", "LI", "NO"}  # EEE incluido
        tipo_gravamen = 19.0 if pais in paises_ue else 24.0

    cuota = _float(data.get("cuota_resultante", 0))
    if cuota == 0 and incremento > 0:
        cuota = incremento * tipo_gravamen / 100

    retencion_211 = _float(data.get("retencion_modelo_211", 0))
    if retencion_211 == 0 and valor_transmision > 0:
        retencion_211 = round(valor_transmision * 0.03, 2)

    cuota_diferencial = _float(data.get("cuota_diferencial", 0))
    if cuota_diferencial == 0:
        cuota_diferencial = cuota - retencion_211

    # -----------------------------------------------------------------------
    # Fichero de declaración (formato estructurado)
    # -----------------------------------------------------------------------
    lineas = []

    lineas.append(
        "<T210>"
        f"<Ejercicio>{ejercicio}</Ejercicio>"
        f"<Periodo>{periodo}</Periodo>"
        f"<Clave_Declaracion>GP</Clave_Declaracion>"  # GP = Ganancia patrimonial
        f"<NIF_Declarante>{_pad(nif, 20)}</NIF_Declarante>"
        f"<Apellido1>{_pad(data.get('declarante_apellido1', ''), 50)}</Apellido1>"
        f"<Apellido2>{_pad(data.get('declarante_apellido2', ''), 50)}</Apellido2>"
        f"<Nombre>{_pad(data.get('declarante_nombre', ''), 40)}</Nombre>"
        f"<Pais_Residencia>{_pad(pais, 2)}</Pais_Residencia>"
        f"<Domicilio_Pais>{_pad(data.get('declarante_domicilio_pais', ''), 100)}</Domicilio_Pais>"
    )

    if data.get("representante_nif"):
        lineas.append(
            f"<NIF_Representante>{_pad(data.get('representante_nif', ''), 9)}</NIF_Representante>"
            f"<Nombre_Representante>{_pad(data.get('representante_nombre', ''), 80)}</Nombre_Representante>"
        )

    lineas.append(
        f"<Ref_Catastral>{_pad(data.get('inmueble_referencia_catastral', ''), 20)}</Ref_Catastral>"
        f"<Direccion_Inmueble>{_pad(data.get('inmueble_direccion', ''), 80)}</Direccion_Inmueble>"
        f"<Municipio_Inmueble>{_pad(data.get('inmueble_municipio', ''), 40)}</Municipio_Inmueble>"
        f"<Provincia_Inmueble>{_pad(data.get('inmueble_provincia', ''), 30)}</Provincia_Inmueble>"
        f"<Fecha_Adquisicion>{data.get('fecha_adquisicion', '')}</Fecha_Adquisicion>"
        f"<Valor_Adquisicion>{_fmt_importe(valor_adquisicion)}</Valor_Adquisicion>"
        f"<Fecha_Transmision>{fecha_transmision}</Fecha_Transmision>"
        f"<Valor_Transmision>{_fmt_importe(valor_transmision)}</Valor_Transmision>"
        f"<Incremento_Patrimonial>{_fmt_importe(incremento)}</Incremento_Patrimonial>"
        f"<Tipo_Gravamen>{tipo_gravamen:.2f}</Tipo_Gravamen>"
        f"<Cuota_Resultante>{_fmt_importe(cuota)}</Cuota_Resultante>"
        f"<Retencion_Modelo_211>{_fmt_importe(retencion_211)}</Retencion_Modelo_211>"
        f"<Cuota_Diferencial>{_fmt_importe(cuota_diferencial)}</Cuota_Diferencial>"
        "</T210>"
    )

    # --- Resumen legible ---
    signo_dif = "A INGRESAR" if cuota_diferencial >= 0 else "A DEVOLVER"
    resumen = [
        "# MODELO 210 - AEAT - IRNR Incremento Patrimonial",
        f"# Fichero: {filename}",
        f"# Origen: {Path(doc['path']).name}",
        f"# SHA256: {doc.get('sha256', '')}",
        "#",
        f"# Declarante (vendedor NR): {data.get('declarante_nombre', '')} {data.get('declarante_apellido1', '')}",
        f"# NIF/ID declarante: {nif}",
        f"# País residencia: {pais}",
        f"# Inmueble: {data.get('inmueble_direccion', '')}",
        f"# Fecha adquisición: {data.get('fecha_adquisicion', '')}",
        f"# Valor adquisición: {valor_adquisicion:.2f} EUR",
        f"# Fecha transmisión: {fecha_transmision}",
        f"# Valor transmisión: {valor_transmision:.2f} EUR",
        f"# Incremento patrimonial: {incremento:.2f} EUR",
        f"# Tipo gravamen: {tipo_gravamen:.2f}%",
        f"# Cuota resultante: {cuota:.2f} EUR",
        f"# Retención M211: {retencion_211:.2f} EUR",
        f"# Cuota diferencial ({signo_dif}): {abs(cuota_diferencial):.2f} EUR",
        "#",
    ]

    content = "\n".join(resumen) + "\n" + "".join(lineas) + "\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  → Exportado: {output_path}")
    return str(output_path)
