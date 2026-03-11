"""
Exportador AEAT Modelo 211 — Retención no residentes
Salida: {nif}_{YYYY}_{MM}_{DD}.json + {nif}_{YYYY}_{MM}_{DD}.pdf
"""

from pathlib import Path
from exporters.base_exporter import build_filename, save_json, PDFReport

MODEL_CONFIG = {"name": "aeat_211"}
MODEL_LABEL = "AEAT Modelo 211 — Retención e ingreso a cuenta\npor adquisición de inmuebles a no residentes (IRNR)"
MODEL_REF = "Art. 25.2 LIRNR / RD 1776/2004"


def export(data: dict, output_dir: str, doc: dict) -> dict:
    """
    Genera {nif}_{YYYY}_{MM}_{DD}.json y .pdf en output_dir.
    Devuelve {"json": path, "pdf": path}.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    filename_base = build_filename(data, MODEL_CONFIG)

    # ---- JSON ----
    json_path = save_json(data, output_dir, filename_base)

    # ---- PDF ----
    pdf_path = _build_pdf(data, output_dir, filename_base, doc)

    print(f"  → JSON: {json_path}")
    if pdf_path:
        print(f"  → PDF:  {pdf_path}")

    return {"json": json_path, "pdf": pdf_path}


def _build_pdf(data: dict, output_dir: str, filename_base: str, doc: dict) -> str:
    pdf_output = str(Path(output_dir) / f"{filename_base}.pdf")
    report = PDFReport(pdf_output, MODEL_LABEL, MODEL_REF)

    report.add_header(Path(doc["path"]).name)

    # Sección: Retenedor (comprador)
    report.add_section("Retenedor — Comprador (quien practica la retención)")
    report.add_fields([
        ("NIF Retenedor", data.get("retenedor_nif", "")),
        ("Apellido 1", data.get("retenedor_apellido1", "")),
        ("Apellido 2", data.get("retenedor_apellido2", "")),
        ("Nombre / Razón Social", data.get("retenedor_nombre", "")),
        ("Domicilio fiscal", data.get("retenedor_domicilio", "")),
        ("Municipio", data.get("retenedor_municipio", "")),
        ("Provincia", data.get("retenedor_provincia", "")),
        ("Código Postal", data.get("retenedor_cp", "")),
    ])

    # Sección: Transmitente No Residente (vendedor)
    report.add_section("Transmitente No Residente — Vendedor")
    report.add_fields([
        ("NIF / ID Fiscal", data.get("transmitente_nr_nif", "")),
        ("Apellido 1", data.get("transmitente_nr_apellido1", "")),
        ("Apellido 2", data.get("transmitente_nr_apellido2", "")),
        ("Nombre", data.get("transmitente_nr_nombre", "")),
        ("País de residencia (ISO)", data.get("transmitente_nr_pais_residencia", "")),
    ])

    # Sección: Inmueble
    report.add_section("Bien Inmueble")
    report.add_fields([
        ("Referencia Catastral", data.get("inmueble_referencia_catastral", "")),
        ("Dirección", data.get("inmueble_direccion", "")),
        ("Municipio", data.get("inmueble_municipio", "")),
        ("Provincia", data.get("inmueble_provincia", "")),
        ("Código Postal", data.get("inmueble_cp", "")),
        ("Fecha de transmisión", data.get("fecha_transmision", "")),
    ])

    # Sección: Liquidación
    contraprestacion = data.get("contraprestacion", 0)
    retencion = data.get("retencion_3pct", 0)

    report.add_calculation_table([
        ("Contraprestación (precio de venta)", f"{float(contraprestacion):.2f} €" if contraprestacion else "—"),
        ("Retención 3% (Base × 3%)", f"{float(retencion):.2f} €" if retencion else "—", True),
        ("Ejercicio", data.get("ejercicio", "")),
        ("Período", data.get("periodo", "0A")),
    ], title="Liquidación — Casillas Modelo 211")

    # Advertencias si hay campos vacíos clave
    if not data.get("retenedor_nif"):
        report.add_warning("NIF del retenedor (comprador) no encontrado en el documento")
    if not data.get("fecha_transmision"):
        report.add_warning("Fecha de transmisión no encontrada — verificar manualmente")

    report.add_footer(Path(doc["path"]).name, doc.get("sha256", ""))

    return report.save()
