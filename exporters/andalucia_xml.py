"""
Exportador Modelo 600 — Andalucía (ITP/AJD)
Salida: {nif}_{YYYY}_{MM}_{DD}.json + {nif}_{YYYY}_{MM}_{DD}.pdf
"""

from pathlib import Path
from exporters.base_exporter import build_filename, save_json, PDFReport

MODEL_CONFIG = {"name": "andalucia_600"}
MODEL_LABEL = "Modelo 600 — Junta de Andalucía\nImpuesto sobre Transmisiones Patrimoniales y AJD"
MODEL_REF = "Autoliquidación ITP/AJD — SURWEB Andalucía"


def export(data: dict, output_dir: str, doc: dict) -> dict:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    filename_base = build_filename(data, MODEL_CONFIG)

    json_path = save_json(data, output_dir, filename_base)
    pdf_path = _build_pdf(data, output_dir, filename_base, doc)

    print(f"  → JSON: {json_path}")
    if pdf_path:
        print(f"  → PDF:  {pdf_path}")

    return {"json": json_path, "pdf": pdf_path}


def _build_pdf(data: dict, output_dir: str, filename_base: str, doc: dict) -> str:
    pdf_output = str(Path(output_dir) / f"{filename_base}.pdf")
    report = PDFReport(pdf_output, MODEL_LABEL, MODEL_REF)

    report.add_header(Path(doc["path"]).name)

    # Presentación
    report.add_section("Datos de Presentación")
    report.add_fields([
        ("Fecha devengo", data.get("fecha_devengo", "")),
        ("Tipo de documento", data.get("tipo_documento", "")),
        ("Notario", data.get("notario", "")),
        ("Nº Protocolo", data.get("numero_protocolo", "")),
        ("Ejercicio protocolo", data.get("ejercicio_protocolo", "")),
    ])

    # Sujeto pasivo
    report.add_section("Sujeto Pasivo — Adquirente")
    report.add_fields([
        ("NIF", data.get("sujeto_pasivo_nif", "")),
        ("Apellido 1", data.get("sujeto_pasivo_apellido1", "")),
        ("Apellido 2", data.get("sujeto_pasivo_apellido2", "")),
        ("Nombre", data.get("sujeto_pasivo_nombre", "")),
        ("Domicilio", data.get("sujeto_pasivo_domicilio", "")),
        ("Municipio", data.get("sujeto_pasivo_municipio", "")),
        ("Provincia", data.get("sujeto_pasivo_provincia", "")),
        ("Código Postal", data.get("sujeto_pasivo_cp", "")),
        ("% Participación", data.get("sujeto_pasivo_porcentaje", "100")),
    ])

    # Transmitente
    report.add_section("Transmitente — Vendedor / Causante")
    report.add_fields([
        ("NIF", data.get("transmitente_nif", "")),
        ("Apellido 1", data.get("transmitente_apellido1", "")),
        ("Apellido 2", data.get("transmitente_apellido2", "")),
        ("Nombre", data.get("transmitente_nombre", "")),
        ("Domicilio", data.get("transmitente_domicilio", "")),
    ])

    # Inmueble
    report.add_section("Bien Inmueble")
    report.add_fields([
        ("Descripción", data.get("inmueble_descripcion", "")),
        ("Referencia Catastral", data.get("inmueble_referencia_catastral", "")),
        ("Dirección", data.get("inmueble_direccion", "")),
        ("Municipio", data.get("inmueble_municipio", "")),
        ("Provincia", data.get("inmueble_provincia", "")),
        ("Código Postal", data.get("inmueble_cp", "")),
    ])

    # Liquidación
    valor = float(data.get("valor_inmueble", 0) or 0)
    pct = float(data.get("porcentaje_transmitido", 100) or 100)
    tipo = float(data.get("tipo_gravamen", 8) or 8)
    base = float(data.get("base_imponible", 0) or round(valor * pct / 100, 2))
    cuota = float(data.get("cuota_tributaria", 0) or round(base * tipo / 100, 2))

    report.add_calculation_table([
        ("Casilla 69 — Valor total del bien", f"{valor:.2f} \u20ac"),
        ("% Transmitido", f"{pct:.2f}%"),
        ("Casilla 72 — Base liquidable", f"{base:.2f} \u20ac"),
        ("Tipo de gravamen", f"{tipo:.2f}%"),
        ("Casilla 74 — Cuota", f"{cuota:.2f} \u20ac", True),
        ("Casilla 80 — Total a ingresar", f"{cuota:.2f} \u20ac", True),
    ], title="Liquidación — Casillas Modelo 600 Andalucía")

    report.add_footer(Path(doc["path"]).name, doc.get("sha256", ""))

    return report.save()
