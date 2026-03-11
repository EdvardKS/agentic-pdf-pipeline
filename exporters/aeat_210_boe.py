"""
Exportador AEAT Modelo 210 — IRNR Incremento Patrimonial
Salida: {nif}_{YYYY}_{MM}_{DD}.json + {nif}_{YYYY}_{MM}_{DD}.pdf
"""

from pathlib import Path
from exporters.base_exporter import build_filename, save_json, PDFReport

MODEL_CONFIG = {"name": "aeat_210"}
MODEL_LABEL = "AEAT Modelo 210 — IRNR Incremento Patrimonial\npor transmisión de inmueble (no residente)"
MODEL_REF = "Art. 24 LIRNR / RD 1776/2004"


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

    # Declarante (no residente)
    report.add_section("Declarante — Vendedor No Residente")
    report.add_fields([
        ("NIF / ID Fiscal", data.get("declarante_nif", "")),
        ("Apellido 1", data.get("declarante_apellido1", "")),
        ("Apellido 2", data.get("declarante_apellido2", "")),
        ("Nombre", data.get("declarante_nombre", "")),
        ("País de residencia (ISO)", data.get("declarante_pais_residencia", "")),
        ("Domicilio en país de residencia", data.get("declarante_domicilio_pais", "")),
    ])

    # Representante fiscal (si existe)
    if data.get("representante_nif") or data.get("representante_nombre"):
        report.add_section("Representante Fiscal en España")
        report.add_fields([
            ("NIF Representante", data.get("representante_nif", "")),
            ("Nombre / Razón Social", data.get("representante_nombre", "")),
        ])

    # Inmueble
    report.add_section("Bien Inmueble")
    report.add_fields([
        ("Referencia Catastral", data.get("inmueble_referencia_catastral", "")),
        ("Dirección", data.get("inmueble_direccion", "")),
        ("Municipio", data.get("inmueble_municipio", "")),
        ("Provincia", data.get("inmueble_provincia", "")),
        ("Fecha de adquisición", data.get("fecha_adquisicion", "")),
        ("Valor de adquisición", f"{float(data.get('valor_adquisicion', 0)):.2f} €" if data.get("valor_adquisicion") else "—"),
        ("Fecha de transmisión", data.get("fecha_transmision", "")),
        ("Valor de transmisión", f"{float(data.get('valor_transmision', 0)):.2f} €" if data.get("valor_transmision") else "—"),
    ])

    # Liquidación
    incremento = data.get("incremento_patrimonial", 0)
    tipo = data.get("tipo_gravamen_aplicable", 0)
    cuota = data.get("cuota_resultante", 0)
    retencion_211 = data.get("retencion_modelo_211", 0)
    cuota_dif = data.get("cuota_diferencial", 0)

    signo = "A INGRESAR" if float(cuota_dif or 0) >= 0 else "A DEVOLVER"

    report.add_calculation_table([
        ("Valor transmisión", f"{float(data.get('valor_transmision', 0)):.2f} €"),
        ("Valor adquisición", f"{float(data.get('valor_adquisicion', 0)):.2f} €"),
        ("Incremento patrimonial", f"{float(incremento or 0):.2f} €"),
        ("Tipo gravamen aplicable", f"{float(tipo or 0):.2f}%"),
        ("Cuota resultante", f"{float(cuota or 0):.2f} €"),
        ("Retención M211 (3%)", f"{float(retencion_211 or 0):.2f} €"),
        (f"Cuota diferencial ({signo})", f"{abs(float(cuota_dif or 0)):.2f} €", True),
        ("Ejercicio / Período", f"{data.get('ejercicio', '')} / {data.get('periodo', '')}"),
    ], title="Liquidación — Casillas Modelo 210")

    if not data.get("fecha_adquisicion"):
        report.add_warning("Fecha y valor de adquisición no encontrados — completar manualmente")
    if not data.get("declarante_nif"):
        report.add_warning("NIF del declarante (vendedor no residente) no encontrado")

    report.add_footer(Path(doc["path"]).name, doc.get("sha256", ""))

    return report.save()
