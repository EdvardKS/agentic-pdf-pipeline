"""
Exportador Modelo 600 - Región de Murcia (PACO)
Genera un JSON normalizado listo para adaptar al formato de importación del
programa PACO cuando el cliente facilite la especificación técnica.
"""

import json
from pathlib import Path


def _float(value) -> float:
    try:
        return float(str(value).replace(",", ".").replace(" ", ""))
    except (ValueError, TypeError):
        return 0.0


def export(data: dict, output_dir: str, doc: dict) -> str:
    """
    Genera un fichero JSON por documento y lo guarda en output_dir.
    Devuelve la ruta del fichero generado.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    stem = Path(doc["path"]).stem
    output_path = Path(output_dir) / f"{stem}.json"

    valor = _float(data.get("valor_inmueble", 0))
    pct_transmitido = _float(data.get("porcentaje_transmitido", 100))
    tipo_gravamen = _float(data.get("tipo_gravamen", 8))

    base_imponible = valor * pct_transmitido / 100
    cuota = base_imponible * tipo_gravamen / 100

    output = {
        "modelo": "600",
        "comunidad": "Región de Murcia",
        "formato": "PACO_normalizado_v1",
        "nota": "JSON normalizado pendiente de adaptar al formato de importación de PACO",
        "presentacion": {
            "fecha_devengo": data.get("fecha_devengo", ""),
            "tipo_documento": data.get("tipo_documento", ""),
            "numero_protocolo": data.get("numero_protocolo", ""),
            "ejercicio_protocolo": data.get("ejercicio_protocolo", ""),
            "notario": data.get("notario", "")
        },
        "sujeto_pasivo": {
            "nif": data.get("sujeto_pasivo_nif", ""),
            "apellido1": data.get("sujeto_pasivo_apellido1", ""),
            "apellido2": data.get("sujeto_pasivo_apellido2", ""),
            "nombre": data.get("sujeto_pasivo_nombre", ""),
            "domicilio": data.get("sujeto_pasivo_domicilio", ""),
            "municipio": data.get("sujeto_pasivo_municipio", ""),
            "provincia": data.get("sujeto_pasivo_provincia", ""),
            "cp": data.get("sujeto_pasivo_cp", ""),
            "porcentaje_participacion": data.get("sujeto_pasivo_porcentaje", "100")
        },
        "transmitente": {
            "nif": data.get("transmitente_nif", ""),
            "apellido1": data.get("transmitente_apellido1", ""),
            "apellido2": data.get("transmitente_apellido2", ""),
            "nombre": data.get("transmitente_nombre", ""),
            "domicilio": data.get("transmitente_domicilio", "")
        },
        "bien_inmueble": {
            "descripcion": data.get("inmueble_descripcion", ""),
            "referencia_catastral": data.get("inmueble_referencia_catastral", ""),
            "direccion": data.get("inmueble_direccion", ""),
            "municipio": data.get("inmueble_municipio", ""),
            "provincia": data.get("inmueble_provincia", ""),
            "cp": data.get("inmueble_cp", "")
        },
        "liquidacion": {
            "valor_inmueble": data.get("valor_inmueble", ""),
            "porcentaje_transmitido": data.get("porcentaje_transmitido", "100"),
            "base_liquidable": round(base_imponible, 2),
            "tipo_gravamen": data.get("tipo_gravamen", "8"),
            "cuota": round(cuota, 2),
            "total_ingresar": round(cuota, 2)
        },
        "origen_documento": {
            "archivo_origen": Path(doc["path"]).name,
            "sha256": doc.get("sha256", "")
        }
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"  → Exportado: {output_path}")
    return str(output_path)
