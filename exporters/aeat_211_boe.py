"""
Exportador AEAT Modelo 211
Genera un fichero en formato texto estructurado compatible con el diseño de
registro publicado por la AEAT para el Modelo 211 (Retención e ingreso a
cuenta por adquisición de inmuebles a no residentes).

Nombre del fichero: NIF_YYYY_0A.211
"""

from pathlib import Path


def _float(value) -> float:
    try:
        return float(str(value).replace(",", ".").replace(" ", ""))
    except (ValueError, TypeError):
        return 0.0


def _fmt_importe(value, decimales=2, longitud=17) -> str:
    """Formatea un importe en céntimos (entero) sin punto decimal, relleno con ceros a la izquierda."""
    try:
        importe_centimos = int(round(_float(value) * 100))
    except Exception:
        importe_centimos = 0
    return str(importe_centimos).zfill(longitud)


def _pad(value, length, fill=" ", align="left") -> str:
    s = str(value) if value is not None else ""
    s = s[:length]
    if align == "left":
        return s.ljust(length, fill)
    return s.rjust(length, fill)


def export(data: dict, output_dir: str, doc: dict) -> str:
    """
    Genera un fichero .211 por documento y lo guarda en output_dir.
    Devuelve la ruta del fichero generado.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    nif = data.get("retenedor_nif", "UNKNOWN").replace(" ", "").upper()
    ejercicio = str(data.get("ejercicio", "2024"))
    periodo = "0A"

    filename = f"{nif}_{ejercicio}_{periodo}.211"
    output_path = Path(output_dir) / filename

    contraprestacion = _float(data.get("contraprestacion", 0))
    retencion = _float(data.get("retencion_3pct", 0))

    # Si no se extrajo la retención, calcularla
    if retencion == 0 and contraprestacion > 0:
        retencion = round(contraprestacion * 0.03, 2)

    # -----------------------------------------------------------------------
    # Registro tipo 1 — Identificación del declarante (retenedor/comprador)
    # Formato simplificado basado en el diseño de registro AEAT 211
    # -----------------------------------------------------------------------
    lineas = []

    # Cabecera del fichero
    lineas.append(
        "<T211>"
        f"<Ejercicio>{ejercicio}</Ejercicio>"
        f"<Periodo>{periodo}</Periodo>"
        f"<NIF_Retenedor>{_pad(nif, 9)}</NIF_Retenedor>"
        f"<Apellido1_Retenedor>{_pad(data.get('retenedor_apellido1', ''), 50)}</Apellido1_Retenedor>"
        f"<Apellido2_Retenedor>{_pad(data.get('retenedor_apellido2', ''), 50)}</Apellido2_Retenedor>"
        f"<Nombre_Retenedor>{_pad(data.get('retenedor_nombre', ''), 40)}</Nombre_Retenedor>"
        f"<Domicilio_Retenedor>{_pad(data.get('retenedor_domicilio', ''), 80)}</Domicilio_Retenedor>"
        f"<Municipio_Retenedor>{_pad(data.get('retenedor_municipio', ''), 40)}</Municipio_Retenedor>"
        f"<Provincia_Retenedor>{_pad(data.get('retenedor_provincia', ''), 30)}</Provincia_Retenedor>"
        f"<CP_Retenedor>{_pad(data.get('retenedor_cp', ''), 5)}</CP_Retenedor>"
    )

    # Datos del transmitente no residente
    lineas.append(
        f"<NIF_Transmitente_NR>{_pad(data.get('transmitente_nr_nif', ''), 20)}</NIF_Transmitente_NR>"
        f"<Apellido1_Transmitente>{_pad(data.get('transmitente_nr_apellido1', ''), 50)}</Apellido1_Transmitente>"
        f"<Apellido2_Transmitente>{_pad(data.get('transmitente_nr_apellido2', ''), 50)}</Apellido2_Transmitente>"
        f"<Nombre_Transmitente>{_pad(data.get('transmitente_nr_nombre', ''), 40)}</Nombre_Transmitente>"
        f"<Pais_Residencia>{_pad(data.get('transmitente_nr_pais_residencia', ''), 2)}</Pais_Residencia>"
    )

    # Datos del inmueble
    lineas.append(
        f"<Fecha_Transmision>{data.get('fecha_transmision', '')}</Fecha_Transmision>"
        f"<Ref_Catastral>{_pad(data.get('inmueble_referencia_catastral', ''), 20)}</Ref_Catastral>"
        f"<Direccion_Inmueble>{_pad(data.get('inmueble_direccion', ''), 80)}</Direccion_Inmueble>"
        f"<Municipio_Inmueble>{_pad(data.get('inmueble_municipio', ''), 40)}</Municipio_Inmueble>"
        f"<Provincia_Inmueble>{_pad(data.get('inmueble_provincia', ''), 30)}</Provincia_Inmueble>"
        f"<CP_Inmueble>{_pad(data.get('inmueble_cp', ''), 5)}</CP_Inmueble>"
    )

    # Importes
    lineas.append(
        f"<Contraprestacion>{_fmt_importe(contraprestacion)}</Contraprestacion>"
        f"<Retencion_3pct>{_fmt_importe(retencion)}</Retencion_3pct>"
        "</T211>"
    )

    # --- Bloque de datos legibles (comentario para revisión humana) ---
    resumen = [
        "# MODELO 211 - AEAT - Retención no residentes",
        f"# Fichero: {filename}",
        f"# Origen: {Path(doc['path']).name}",
        f"# SHA256: {doc.get('sha256', '')}",
        "#",
        f"# Retenedor (comprador): {data.get('retenedor_nombre', '')} {data.get('retenedor_apellido1', '')} {data.get('retenedor_apellido2', '')}",
        f"# NIF retenedor: {nif}",
        f"# Transmitente NR (vendedor): {data.get('transmitente_nr_nombre', '')} {data.get('transmitente_nr_apellido1', '')}",
        f"# País residencia transmitente: {data.get('transmitente_nr_pais_residencia', '')}",
        f"# Inmueble: {data.get('inmueble_direccion', '')}",
        f"# Fecha transmisión: {data.get('fecha_transmision', '')}",
        f"# Contraprestación: {contraprestacion:.2f} EUR",
        f"# Retención 3%: {retencion:.2f} EUR",
        "#",
    ]

    content = "\n".join(resumen) + "\n" + "".join(lineas) + "\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"  → Exportado: {output_path}")
    return str(output_path)
