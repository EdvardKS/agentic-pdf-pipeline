"""
Exportador de datos de clientes en formato CSV.

Una ejecución = un CSV con todos los clientes de todos los PDFs procesados.
Nombre del fichero: clientes_{YYYYMMDD_HHMMSS}.csv
Formato: UTF-8 con BOM (compatible con Excel en Windows)

La función export() se llama una vez por PDF.
Abre el CSV en modo 'a' (append) y añade filas.
Si el fichero no existe aún, escribe la cabecera primero.
"""

import csv
from pathlib import Path
from datetime import datetime

CSV_COLUMNS = [
    "archivo_origen",
    "rol",
    "nombre_completo",
    "es_representante_de",
    "tipo_doc_identidad",
    "nif_nie_cif",
    "numero_pasaporte",
    "fecha_nacimiento",
    "nacionalidad",
    "pais_residencia",
    "estado_civil",
    "profesion",
    "domicilio_completo",
    "municipio_domicilio",
    "provincia_domicilio",
    "codigo_postal",
    "pais_domicilio",
    "domicilio_notificacion_espana",
    "es_no_residente",
]


def init_csv(output_dir: str, timestamp: str = None) -> str:
    """
    Crea el fichero CSV con cabecera y devuelve la ruta.
    Llamar una vez antes del bucle de documentos.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = str(Path(output_dir) / f"clientes_{ts}.csv")

    # Escribir cabecera con UTF-8 BOM para compatibilidad con Excel
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()

    return csv_path


def export(data: dict, output_dir: str, doc: dict, csv_path: str = None) -> dict:
    """
    Añade las filas de clientes del documento al CSV acumulativo.

    data: {"clientes": [...]}
    doc: {"path": "...", "sha256": "..."}
    csv_path: ruta del CSV de la sesión (creado con init_csv)

    Si csv_path no se pasa, se crea uno nuevo (útil para tests).
    """
    clientes = data.get("clientes", [])
    archivo_origen = Path(doc["path"]).name

    if not csv_path:
        csv_path = init_csv(output_dir)

    rows_written = 0

    with open(csv_path, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")

        for cliente in clientes:
            row = {col: "" for col in CSV_COLUMNS}
            row["archivo_origen"] = archivo_origen

            for col in CSV_COLUMNS:
                if col == "archivo_origen":
                    continue
                val = cliente.get(col, "")
                if isinstance(val, bool):
                    row[col] = "true" if val else "false"
                else:
                    row[col] = str(val) if val is not None else ""

            writer.writerow(row)
            rows_written += 1

    print(f"  → CSV: {csv_path}  (+{rows_written} filas de {archivo_origen})")
    return {"csv": csv_path, "rows": rows_written}
