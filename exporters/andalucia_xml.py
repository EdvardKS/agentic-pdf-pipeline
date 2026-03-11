"""
Exportador Modelo 600 - Andalucía
Genera un XML estructurado con los campos mapeados a las casillas del formulario
SURWEB de la Junta de Andalucía (ITP/AJD).
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path


def _sub(parent, tag, text=""):
    el = ET.SubElement(parent, tag)
    el.text = str(text) if text is not None else ""
    return el


def export(data: dict, output_dir: str, doc: dict) -> str:
    """
    Genera un fichero XML por documento y lo guarda en output_dir.
    Devuelve la ruta del fichero generado.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    stem = Path(doc["path"]).stem
    output_path = Path(output_dir) / f"{stem}.xml"

    root = ET.Element("Modelo600Andalucia")
    root.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    root.set("version", "1.0")

    # --- Datos de presentación ---
    presentacion = ET.SubElement(root, "Presentacion")
    _sub(presentacion, "FechaDevengo", data.get("fecha_devengo", ""))
    _sub(presentacion, "TipoDocumento", data.get("tipo_documento", ""))
    _sub(presentacion, "NumeroProtocolo", data.get("numero_protocolo", ""))
    _sub(presentacion, "EjercicioProtocolo", data.get("ejercicio_protocolo", ""))
    _sub(presentacion, "Notario", data.get("notario", ""))

    # --- Sujeto Pasivo (adquirente) ---
    sujeto = ET.SubElement(root, "SujetoPasivo")
    _sub(sujeto, "NIF", data.get("sujeto_pasivo_nif", ""))
    _sub(sujeto, "Apellido1", data.get("sujeto_pasivo_apellido1", ""))
    _sub(sujeto, "Apellido2", data.get("sujeto_pasivo_apellido2", ""))
    _sub(sujeto, "Nombre", data.get("sujeto_pasivo_nombre", ""))
    _sub(sujeto, "Domicilio", data.get("sujeto_pasivo_domicilio", ""))
    _sub(sujeto, "Municipio", data.get("sujeto_pasivo_municipio", ""))
    _sub(sujeto, "Provincia", data.get("sujeto_pasivo_provincia", ""))
    _sub(sujeto, "CodigoPostal", data.get("sujeto_pasivo_cp", ""))
    _sub(sujeto, "PorcentajeParticipacion", data.get("sujeto_pasivo_porcentaje", "100"))

    # --- Transmitente ---
    transmitente = ET.SubElement(root, "Transmitente")
    _sub(transmitente, "NIF", data.get("transmitente_nif", ""))
    _sub(transmitente, "Apellido1", data.get("transmitente_apellido1", ""))
    _sub(transmitente, "Apellido2", data.get("transmitente_apellido2", ""))
    _sub(transmitente, "Nombre", data.get("transmitente_nombre", ""))
    _sub(transmitente, "Domicilio", data.get("transmitente_domicilio", ""))

    # --- Bien Inmueble ---
    inmueble = ET.SubElement(root, "BienInmueble")
    _sub(inmueble, "Descripcion", data.get("inmueble_descripcion", ""))
    _sub(inmueble, "ReferenciaCatastral", data.get("inmueble_referencia_catastral", ""))
    _sub(inmueble, "Direccion", data.get("inmueble_direccion", ""))
    _sub(inmueble, "Municipio", data.get("inmueble_municipio", ""))
    _sub(inmueble, "Provincia", data.get("inmueble_provincia", ""))
    _sub(inmueble, "CodigoPostal", data.get("inmueble_cp", ""))

    # --- Liquidación (casillas) ---
    liquidacion = ET.SubElement(root, "Liquidacion")
    _sub(liquidacion, "Casilla69_ValorTotalBien", data.get("valor_inmueble", ""))
    _sub(liquidacion, "PorcentajeTransmitido", data.get("porcentaje_transmitido", "100"))

    valor = _float(data.get("valor_inmueble", 0))
    pct_transmitido = _float(data.get("porcentaje_transmitido", 100))
    tipo_gravamen = _float(data.get("tipo_gravamen", 8))

    base_imponible = valor * pct_transmitido / 100
    cuota = base_imponible * tipo_gravamen / 100

    _sub(liquidacion, "Casilla72_BaseLiquidable", f"{base_imponible:.2f}")
    _sub(liquidacion, "TipoGravamen", data.get("tipo_gravamen", ""))
    _sub(liquidacion, "Casilla74_Cuota", f"{cuota:.2f}")
    _sub(liquidacion, "Casilla80_TotalIngresar", f"{cuota:.2f}")

    # --- Metadata de origen ---
    origen = ET.SubElement(root, "OrigenDocumento")
    _sub(origen, "ArchivoOrigen", Path(doc["path"]).name)
    _sub(origen, "SHA256", doc.get("sha256", ""))

    xml_str = minidom.parseString(
        ET.tostring(root, encoding="unicode")
    ).toprettyxml(indent="  ", encoding=None)

    # minidom añade declaración XML; la escribimos con encoding utf-8
    with open(output_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        # Saltar la primera línea que añade minidom (su propia declaración)
        lines = xml_str.split("\n")
        f.write("\n".join(lines[1:]))

    print(f"  → Exportado: {output_path}")
    return str(output_path)


def _float(value) -> float:
    try:
        return float(str(value).replace(",", ".").replace(" ", ""))
    except (ValueError, TypeError):
        return 0.0
