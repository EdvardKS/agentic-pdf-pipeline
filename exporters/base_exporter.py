"""
Helpers comunes para todos los exportadores.

- build_filename(): construye el nombre de fichero estándar
- save_json(): guarda el JSON normalizado
- PDFReport: clase base para generar PDFs de resumen con reportlab
"""

import json
from pathlib import Path
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor, black, white, grey
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# Colores corporativos
COLOR_HEADER = HexColor("#1a3a5c") if REPORTLAB_AVAILABLE else None
COLOR_SECTION = HexColor("#2e6da4") if REPORTLAB_AVAILABLE else None
COLOR_ALT_ROW = HexColor("#eef4fb") if REPORTLAB_AVAILABLE else None
COLOR_WARN = HexColor("#e07b00") if REPORTLAB_AVAILABLE else None


def build_filename(data: dict, model_config: dict) -> str:
    """
    Construye el nombre base del fichero: {nif}_{YYYY}_{MM}_{DD}

    nif_principal según el modelo:
      - aeat_211: retenedor_nif (si vacío → transmitente_nr_nif)
      - aeat_210: declarante_nif
      - *_600: sujeto_pasivo_nif (si vacío → transmitente_nif)

    fecha: fecha_transmision > fecha_devengo > hoy
    """
    model_name = model_config.get("name", "")

    # Seleccionar NIF principal
    if "aeat_211" in model_name:
        nif = data.get("retenedor_nif", "") or data.get("transmitente_nr_nif", "")
    elif "aeat_210" in model_name:
        nif = data.get("declarante_nif", "") or data.get("transmitente_nr_nif", "")
    else:
        nif = data.get("sujeto_pasivo_nif", "") or data.get("transmitente_nif", "")

    nif = str(nif).strip().replace(" ", "").replace("-", "").upper()
    if not nif:
        nif = "SIN_NIF"

    # Seleccionar fecha
    fecha = (
        data.get("fecha_transmision") or
        data.get("fecha_devengo") or
        datetime.now().strftime("%Y-%m-%d")
    )

    # Normalizar fecha a partes
    try:
        parts = str(fecha).strip().split("-")
        if len(parts) == 3:
            anio, mes, dia = parts[0], parts[1], parts[2]
        else:
            anio = datetime.now().strftime("%Y")
            mes = datetime.now().strftime("%m")
            dia = datetime.now().strftime("%d")
    except Exception:
        anio = datetime.now().strftime("%Y")
        mes = datetime.now().strftime("%m")
        dia = datetime.now().strftime("%d")

    return f"{nif}_{anio}_{mes}_{dia}"


def save_json(data: dict, output_dir: str, filename_base: str) -> str:
    """Guarda el dict normalizado como JSON. Devuelve la ruta."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_path = Path(output_dir) / f"{filename_base}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return str(output_path)


# ---------------------------------------------------------------------------
# PDF report
# ---------------------------------------------------------------------------

class PDFReport:
    """
    Genera un PDF de resumen con layout de formulario fiscal.
    """

    def __init__(self, output_path: str, model_label: str, model_ref: str = ""):
        self.output_path = output_path
        self.model_label = model_label
        self.model_ref = model_ref
        self._elements = []
        self._styles = self._build_styles() if REPORTLAB_AVAILABLE else None

    def _build_styles(self):
        base = getSampleStyleSheet()
        styles = {
            "title": ParagraphStyle(
                "title",
                parent=base["Normal"],
                fontSize=14,
                fontName="Helvetica-Bold",
                textColor=white,
                alignment=TA_LEFT,
                spaceAfter=0,
            ),
            "subtitle": ParagraphStyle(
                "subtitle",
                parent=base["Normal"],
                fontSize=9,
                fontName="Helvetica",
                textColor=HexColor("#ccddee"),
                alignment=TA_LEFT,
                spaceAfter=0,
            ),
            "section": ParagraphStyle(
                "section",
                parent=base["Normal"],
                fontSize=10,
                fontName="Helvetica-Bold",
                textColor=white,
                spaceAfter=2,
                spaceBefore=4,
            ),
            "field_label": ParagraphStyle(
                "field_label",
                parent=base["Normal"],
                fontSize=8,
                fontName="Helvetica-Bold",
                textColor=HexColor("#1a3a5c"),
            ),
            "field_value": ParagraphStyle(
                "field_value",
                parent=base["Normal"],
                fontSize=9,
                fontName="Helvetica",
                textColor=black,
            ),
            "footer": ParagraphStyle(
                "footer",
                parent=base["Normal"],
                fontSize=7,
                fontName="Helvetica",
                textColor=grey,
                alignment=TA_CENTER,
            ),
            "warn": ParagraphStyle(
                "warn",
                parent=base["Normal"],
                fontSize=8,
                fontName="Helvetica-Bold",
                textColor=COLOR_WARN,
            ),
        }
        return styles

    def add_header(self, doc_origin: str = ""):
        """Cabecera del PDF con nombre del modelo."""
        if not REPORTLAB_AVAILABLE:
            return
        # Tabla de cabecera con fondo azul oscuro
        header_data = [
            [Paragraph(self.model_label, self._styles["title"])],
            [Paragraph(f"Referencia: {self.model_ref}" if self.model_ref else "Generado automáticamente", self._styles["subtitle"])],
        ]
        t = Table(header_data, colWidths=[17 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_HEADER),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ]))
        self._elements.append(t)
        self._elements.append(Spacer(1, 0.3 * cm))

    def add_section(self, title: str):
        """Separador de sección con fondo azul."""
        if not REPORTLAB_AVAILABLE:
            return
        t = Table([[Paragraph(title.upper(), self._styles["section"])]], colWidths=[17 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), COLOR_SECTION),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        self._elements.append(Spacer(1, 0.2 * cm))
        self._elements.append(t)

    def add_fields(self, fields: list[tuple]):
        """
        Añade una tabla de campos (label, value).
        fields: [(label, value), ...]
        """
        if not REPORTLAB_AVAILABLE:
            return
        rows = []
        for i, (label, value) in enumerate(fields):
            v = str(value) if value is not None else ""
            if not v:
                v = "—"
            row = [
                Paragraph(label, self._styles["field_label"]),
                Paragraph(v, self._styles["field_value"]),
            ]
            rows.append(row)

        t = Table(rows, colWidths=[6 * cm, 11 * cm])
        style = [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, HexColor("#dddddd")),
        ]
        # Filas alternas
        for i in range(0, len(rows), 2):
            style.append(("BACKGROUND", (0, i), (-1, i), COLOR_ALT_ROW))
        t.setStyle(TableStyle(style))
        self._elements.append(t)

    def add_calculation_table(self, rows: list[tuple], title: str = "Liquidación"):
        """
        Tabla de cálculos (label, importe).
        rows: [(label, value, bold?), ...]
        """
        if not REPORTLAB_AVAILABLE:
            return
        self.add_section(title)
        table_rows = []
        style_cmds = [
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, HexColor("#dddddd")),
        ]
        for i, row in enumerate(rows):
            label = row[0]
            value = row[1]
            bold = row[2] if len(row) > 2 else False
            fn = "Helvetica-Bold" if bold else "Helvetica"
            p_label = Paragraph(label, ParagraphStyle("cl", fontName=fn, fontSize=9, textColor=HexColor("#1a3a5c")))
            p_value = Paragraph(str(value) if value is not None else "—", ParagraphStyle("cv", fontName=fn, fontSize=9, alignment=TA_RIGHT))
            table_rows.append([p_label, p_value])
            if bold:
                style_cmds.append(("BACKGROUND", (0, i), (-1, i), HexColor("#dde8f5")))

        t = Table(table_rows, colWidths=[12 * cm, 5 * cm])
        t.setStyle(TableStyle(style_cmds))
        self._elements.append(t)

    def add_footer(self, doc_origin: str, sha256: str = ""):
        """Pie de página con referencia al PDF original."""
        if not REPORTLAB_AVAILABLE:
            return
        self._elements.append(Spacer(1, 0.5 * cm))
        self._elements.append(HRFlowable(width="100%", thickness=0.5, color=grey))
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        footer_text = (
            f"Generado: {now}  |  Origen: {doc_origin}  |  SHA256: {sha256[:16]}..."
            if sha256 else f"Generado: {now}  |  Origen: {doc_origin}"
        )
        self._elements.append(Paragraph(footer_text, self._styles["footer"]))

    def add_warning(self, text: str):
        if not REPORTLAB_AVAILABLE:
            return
        self._elements.append(Paragraph(f"⚠ {text}", self._styles["warn"]))

    def save(self) -> str:
        """Genera el PDF y lo guarda. Devuelve la ruta."""
        if not REPORTLAB_AVAILABLE:
            print("  [PDF] reportlab no instalado — saltando generación de PDF")
            return ""

        doc = SimpleDocTemplate(
            self.output_path,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )
        doc.build(self._elements)
        return self.output_path
