# MAM Solicitors — Agentic PDF Fiscal Pipeline
## Documentación técnica completa
Preguntar  -> Como validar que el json sea correcto.

---

## Índice

1. [Descripción del proyecto](#1-descripción-del-proyecto)
2. [Arquitectura del sistema](#2-arquitectura-del-sistema)
3. [Flujo del pipeline](#3-flujo-del-pipeline)
4. [Módulos y responsabilidades](#4-módulos-y-responsabilidades)
5. [Modelos fiscales soportados](#5-modelos-fiscales-soportados)
6. [Schemas de extracción](#6-schemas-de-extracción)
7. [Exportadores](#7-exportadores)
8. [Configuración](#8-configuración)
9. [Guía de uso](#9-guía-de-uso)
10. [Roadmap](#10-roadmap)
11. [Diagrama de flujo](#11-diagrama-de-flujo)

---

## 1. Descripción del proyecto

Sistema agentic de procesamiento de documentos PDF notariales para el despacho **MAM Solicitors**. El sistema lee escrituras de compraventa, herencias y donaciones en PDF, extrae los datos fiscales relevantes mediante IA local (Ollama), los normaliza y valida, y genera automáticamente los ficheros de salida necesarios para cumplimentar los modelos fiscales oficiales.

### Objetivos

- Automatizar la extracción de datos de escrituras notariales
- Generar borradores listos para revisar de los 5 modelos fiscales principales
- Reducir el tiempo de gestión de documentos en el despacho
- Operar completamente en local (sin datos a la nube) mediante Ollama

### Tecnología

| Componente | Tecnología |
|-----------|-----------|
| Orquestación | LangGraph (grafo de estados) |
| LLM extracción | Ollama (`llama3.1:8b`) |
| OCR | Ollama (`deepseek-ocr:3b`) |
| PDF lectura | PyMuPDF (fitz) |
| PDF generación | ReportLab |
| Servidor IA | Ollama en `http://192.168.200.134:11434` |

---

## 2. Arquitectura del sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    MAM Solicitors Pipeline                       │
│                                                                  │
│  ┌─────────┐    ┌──────────────┐    ┌─────────────────────┐    │
│  │  ./docs  │───▶│  searchDocs  │───▶│  manifest (SHA256)  │    │
│  │ (PDFs)  │    │  (discovery) │    │  (deduplicación)    │    │
│  └─────────┘    └──────────────┘    └──────────┬──────────┘    │
│                                                 │                │
│  ┌──────────────────────────────────────────────▼──────────┐   │
│  │                  MENU DE MODELOS                         │   │
│  │  1-Valencia 600  2-Murcia 600  3-Andalucía 600          │   │
│  │  4-AEAT 211      5-AEAT 210                             │   │
│  └──────────────────────────────┬───────────────────────────┘  │
│                                  │ schema + model_config         │
│  ┌───────────────────────────────▼───────────────────────────┐  │
│  │                  LANGGRAPH PIPELINE                        │  │
│  │                                                            │  │
│  │  extract_node ──▶ clean_node ──▶ schema_extract_node      │  │
│  │                                         │                  │  │
│  │                                   validate_node            │  │
│  │                                    (normalizar +           │  │
│  │                                     calcular derivados)    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                  │ validated_data                │
│  ┌───────────────────────────────▼───────────────────────────┐  │
│  │                    EXPORTADORES                            │  │
│  │                                                            │  │
│  │  outputs/<modelo>/                                         │  │
│  │    {nif}_{YYYY}_{MM}_{DD}.json  ← datos normalizados      │  │
│  │    {nif}_{YYYY}_{MM}_{DD}.pdf   ← informe visual          │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. Flujo del pipeline

```
PDF
 │
 ▼
[extract_node]
  ├── PyMuPDF extrae texto digital
  └── Si texto < 100 chars → Ollama OCR (deepseek-ocr:3b)
 │
 ▼
[clean_node]
  └── Normaliza espacios, saltos de línea
 │
 ▼
[schema_extract_node]
  ├── Construye prompt dinámico desde schema JSON
  ├── Llama a llama3.1:8b con temperatura=0
  ├── Parsea JSON de la respuesta
  ├── Valida campos requeridos
  └── Retry hasta 3 veces si falla validación
 │
 ▼
[validate_node]
  ├── Normaliza números (formato europeo/americano)
  ├── Normaliza fechas (múltiples formatos → YYYY-MM-DD)
  ├── Normaliza NIFs (mayúsculas, sin guiones)
  ├── Calcula campos derivados:
  │     • retencion_3pct = contraprestacion × 0.03
  │     • cuota_resultante = incremento × tipo_gravamen / 100
  │     • cuota_diferencial = cuota - retencion_211
  │     • periodo = trimestre de fecha_transmision
  │     • tipo_gravamen = 19% (UE) o 24% (resto)
  └── Registra warnings de campos críticos vacíos
 │
 ▼
[exporter]
  ├── {nif}_{YYYY}_{MM}_{DD}.json
  └── {nif}_{YYYY}_{MM}_{DD}.pdf
```

---

## 4. Módulos y responsabilidades

### Entrada y discovery

| Fichero | Responsabilidad |
|---------|----------------|
| `searchDocs.py` | Busca PDFs recursivamente en `./docs`, calcula SHA256 |
| `manifest.py` | Deduplicación por SHA256, genera `batches/batch_*.json` |

### Pipeline LangGraph

| Fichero | Responsabilidad |
|---------|----------------|
| `pipeline/graph/graph.py` | Construye el grafo: extract→clean→schema_extract→validate |
| `pipeline/graph/state.py` | Define `DocumentState` (TypedDict del estado del grafo) |
| `pipeline/graph/nodes.py` | `extract_node`, `clean_node` |
| `pipeline/graph/schema_extract_node.py` | Extracción LLM con retry (hasta 3 intentos) |
| `pipeline/graph/validate_node.py` | Normalización, cálculos derivados, warnings |

### Extracción LLM

| Fichero | Responsabilidad |
|---------|----------------|
| `pipeline/schema_loader.py` | Carga schema JSON, construye prompt dinámico |
| `pipeline/ollama_client.py` | Conexión a Ollama, valida modelos disponibles |
| `pipeline/preprocess.py` | Extracción de texto con PyMuPDF |
| `pipeline/ocr.py` | OCR con Ollama vision (deepseek-ocr:3b) |
| `pipeline/text_cleaner.py` | Limpieza de texto |

### Utilidades

| Fichero | Responsabilidad |
|---------|----------------|
| `pipeline/utils/normalizers.py` | `parse_number`, `normalize_date`, `normalize_nif`, `tipo_gravamen_irnr`, etc. |

### Exportadores

| Fichero | Genera |
|---------|--------|
| `exporters/base_exporter.py` | Helpers: `build_filename`, `save_json`, `PDFReport` |
| `exporters/aeat_211_boe.py` | JSON + PDF para Modelo 211 |
| `exporters/aeat_210_boe.py` | JSON + PDF para Modelo 210 |
| `exporters/andalucia_xml.py` | JSON + PDF para Modelo 600 Andalucía |
| `exporters/valencia_xml.py` | JSON + PDF para Modelo 600 Valencia |
| `exporters/murcia_json.py` | JSON + PDF para Modelo 600 Murcia |

### Configuración

| Fichero | Responsabilidad |
|---------|----------------|
| `.env` | Ollama host, nombres de modelos LLM |
| `models_registry.json` | Registro de modelos: schema, exporter, output_dir |
| `pipeline/schemas/*.schema.json` | Definición de campos a extraer por modelo |

---

## 5. Modelos fiscales soportados

### Modelo 600 — Impuesto sobre Transmisiones Patrimoniales y AJD

| Comunidad | Portal oficial | Exportador | Notas |
|-----------|---------------|-----------|-------|
| Andalucía | [SURWEB](https://www.juntadeandalucia.es/economiayhacienda/apl/surweb/modelos/modelo600/600.jsp) | `andalucia_xml.py` | Casillas confirmadas de documentación pública |
| Comunitat Valenciana | [SARA2600](https://sara-2-600.gva.es/sara_2_600-sara2600-frontend/) | `valencia_xml.py` | Estructura normalizada, pendiente validar con exportación real |
| Región de Murcia | [PACO CARM](https://etributos.carm.es/etributos) | `murcia_json.py` | JSON normalizado, pendiente formato PACO |

**Campos extraídos (comunes):**
- Sujeto pasivo: NIF, nombre, apellidos, domicilio, municipio, provincia, CP
- Transmitente: NIF, nombre, apellidos, domicilio
- Documento notarial: tipo, fecha, notario, número de protocolo
- Inmueble: descripción, referencia catastral, dirección, municipio, provincia
- Liquidación: valor, porcentaje transmitido, base imponible, tipo gravamen, cuota

### AEAT Modelo 211 — Retención no residentes

**Portal:** [AEAT M211](https://sede.agenciatributaria.gob.es/Sede/ayuda/consultas-informaticas/presentacion-declaraciones-ayuda-tecnica/modelo-211.html)

**Uso:** Comprador de inmueble a no residente debe retener e ingresar el 3% del precio de venta.

**Campos clave:**
- Retenedor (comprador): NIF, nombre, domicilio
- Transmitente NR (vendedor no residente): NIF/ID, nombre, país de residencia
- Inmueble: referencia catastral, dirección
- Liquidación: contraprestación, retención 3% (calculada automáticamente)

**Nombre de fichero:** `{nif_comprador}_{YYYY}_{MM}_{DD}.json`

### AEAT Modelo 210 — IRNR Incremento Patrimonial

**Portal:** [AEAT M210](https://sede.agenciatributaria.gob.es/Sede/ayuda/consultas-informaticas/presentacion-declaraciones-ayuda-tecnica/modelo-210.html)

**Uso:** Vendedor no residente declara la ganancia patrimonial y deduce la retención del M211.

**Campos clave:**
- Declarante (vendedor NR): NIF/ID, nombre, país, domicilio en el extranjero
- Representante fiscal: NIF, nombre (si lo hay)
- Inmueble: referencia catastral, dirección
- Liquidación: valor adquisición, valor transmisión, incremento, tipo gravamen (19%/24%), cuota, retención M211, cuota diferencial

**Tipo gravamen automático:** 19% para residentes UE/EEE, 24% para el resto.

**Nombre de fichero:** `{nif_vendedor_nr}_{YYYY}_{MM}_{DD}.json`

---

## 6. Schemas de extracción

Los schemas en `pipeline/schemas/` definen cómo el LLM debe extraer cada campo:

```json
{
  "document_type": "aeat_modelo_211",
  "fields": {
    "campo_nombre": {
      "type": "string|number|date",
      "format": "descripción del formato",
      "description": "qué es este campo",
      "required": true|false,
      "calculable": true|false,
      "rules": ["regla 1", "regla 2"],
      "examples": ["ejemplo1"],
      "text_examples": [{"text": "texto del doc", "value": "valor extraído"}]
    }
  }
}
```

**Campos `calculable: true`:** el LLM no necesita encontrarlos; el `validate_node` los calcula automáticamente (ej: `retencion_3pct`, `cuota_diferencial`).

**Campos `required: false`:** el LLM puede devolver cadena vacía sin que el pipeline lo rechace.

---

## 7. Exportadores

Todos los exportadores siguen la misma interfaz:

```python
def export(data: dict, output_dir: str, doc: dict) -> dict:
    # data: validated_data del pipeline
    # output_dir: directorio de salida del modelo
    # doc: metadata del PDF origen (path, sha256)
    # Retorna: {"json": "ruta.json", "pdf": "ruta.pdf"}
```

**Nombre de fichero estándar:** `{nif_principal}_{YYYY}_{MM}_{DD}`

El PDF generado con ReportLab incluye:
- **Cabecera** con nombre del modelo y referencia legal
- **Secciones** según bloques del formulario oficial
- **Tabla de liquidación** con casillas numeradas
- **Advertencias** de campos vacíos
- **Pie** con nombre del PDF origen, SHA256 y fecha de generación

---

## 8. Configuración

### `.env`
```
PICASSO=http://192.168.200.134:11434    # Ollama host
CHAT_MODEL=llama3.1:8b                  # Modelo de extracción
VISION_MODEL=deepseek-ocr:3b            # Modelo OCR
```

### `models_registry.json`
```json
{
  "1": {
    "name": "valencia_600",
    "label": "Modelo 600 - Comunidad Valenciana",
    "schema": "pipeline/schemas/valencia_600.schema.json",
    "exporter": "exporters.valencia_xml",
    "output_dir": "outputs/valencia_600"
  }
}
```

Para **añadir un nuevo modelo**, basta con:
1. Crear `pipeline/schemas/nuevo_modelo.schema.json`
2. Crear `exporters/nuevo_exporter.py` con función `export(data, output_dir, doc)`
3. Añadir entrada en `models_registry.json`

---

## 9. Guía de uso

### Instalación
```bash
pip install -r req.txt
pip install reportlab   # para generación de PDFs
```

### Ejecutar
```bash
python main.py
```

### Flujo de uso
1. Colocar los PDFs en `./docs/` (pueden estar en subcarpetas)
2. Ejecutar `python main.py`
3. Seleccionar el modelo fiscal del menú
4. El pipeline procesa todos los PDFs únicos
5. Los resultados se guardan en `outputs/<modelo>/`
   - `{nif}_{YYYY}_{MM}_{DD}.json` — datos normalizados
   - `{nif}_{YYYY}_{MM}_{DD}.pdf` — informe visual para revisión

### Directorios de salida
```
outputs/
├── valencia_600/
├── murcia_600/
├── andalucia_600/
├── aeat_211/
└── aeat_210/
```

### Notas sobre los PDFs oficiales
Los portales oficiales son aplicaciones web (AEAT usa ZUL/ZK; Andalucía usa SURWEB). **No existe fichero PDF oficial rellenable** para descarga. Los PDFs generados por este sistema son **borradores de revisión** con el mismo layout de secciones que el formulario oficial. El operario los usa de referencia para introducir los datos manualmente en el portal web oficial.

---

## 10. Roadmap

### Completado ✅
- [x] Discovery recursivo de PDFs con SHA256 y deduplicación
- [x] Pipeline LangGraph: extract → clean → schema_extract → validate
- [x] OCR con Ollama vision para PDFs escaneados
- [x] Extracción schema-driven con retry (hasta 3 intentos)
- [x] Menú de 5 modelos fiscales
- [x] Validación y normalización en nodo LangGraph (`validate_node`)
- [x] Cálculos derivados automáticos (retención 3%, tipo gravamen, cuota diferencial)
- [x] Exportación JSON por documento con nombre estándar
- [x] Generación de PDFs de resumen con ReportLab
- [x] Documentación técnica

### Pendiente 🔜
- [ ] **Integración PACO Murcia**: adaptar exportador al formato de importación real del programa PACO una vez el cliente facilite la especificación técnica
- [ ] **Validación XML Valencia**: confirmar estructura XML de importación del portal SARA2600 con una exportación real del sistema
- [ ] **Soporte múltiples sujetos pasivos**: escrituras con varios compradores/herederos (actualmente toma el primero)
- [ ] **Campos adicionales herencia**: fecha fallecimiento, valor catastral, reducción familiar
- [ ] **Interfaz web**: panel de control para subir PDFs y descargar resultados
- [ ] **Modelo más potente**: migrar a `gemma3:27b` o similar para mayor precisión en extracción
- [ ] **Tests automáticos**: batch de PDFs de prueba con valores esperados conocidos
- [ ] **Integración directa AEAT**: rellenar formulario web AEAT automáticamente via Playwright/Selenium

---

## 11. Diagrama de flujo

### Flujo principal
```
main.py
  │
  ├─ find_pdfs("./docs")
  │    └─ Busca *.pdf recursivamente
  │
  ├─ mark_duplicates()
  │    └─ SHA256 → marca duplicados
  │
  ├─ generate_manifest()
  │    └─ batches/batch_TIMESTAMP.json
  │
  ├─ user_menu()
  │    └─ Selección modelo (1-5 / 0=cancelar)
  │
  ├─ load_schema(schema_path)
  ├─ load_exporter(exporter_module)
  │
  └─ Para cada PDF no-duplicado:
       │
       ├─ build_graph()  [una sola vez]
       │
       ├─ graph.invoke(state)
       │    │
       │    ├─ extract_node
       │    │    ├─ PyMuPDF → texto digital
       │    │    └─ Si < 100 chars → OCR Ollama
       │    │
       │    ├─ clean_node
       │    │    └─ Normaliza espacios y saltos
       │    │
       │    ├─ schema_extract_node
       │    │    ├─ build_extraction_prompt(text, schema)
       │    │    ├─ llama3.1:8b (T=0, streaming)
       │    │    ├─ extract_json_from_response()
       │    │    ├─ validate_extraction()
       │    │    └─ Retry × 3 si validación falla
       │    │
       │    └─ validate_node
       │         ├─ parse_number() → corrige "38.570,34"
       │         ├─ normalize_date() → YYYY-MM-DD
       │         ├─ normalize_nif() → sin guiones, mayúsculas
       │         ├─ Calcula: retencion_3pct, cuota, periodo...
       │         └─ check_warnings() → avisa campos vacíos
       │
       └─ exporter(validated_data, output_dir, doc)
            ├─ build_filename() → "{nif}_{YYYY}_{MM}_{DD}"
            ├─ save_json() → .json
            └─ PDFReport.save() → .pdf
```

### Diagrama de estado LangGraph
```
         ┌─────────┐
         │  START  │
         └────┬────┘
              │
         ┌────▼─────────┐
         │ extract_node │  ← PDF → texto (OCR si necesario)
         └────┬─────────┘
              │
         ┌────▼──────────┐
         │  clean_node   │  ← Normaliza texto
         └────┬──────────┘
              │
         ┌────▼───────────────────┐
         │  schema_extract_node   │  ← LLM extrae JSON
         │  (max 3 intentos)      │
         └────┬───────────────────┘
              │
         ┌────▼──────────────┐
         │  validate_node    │  ← Normaliza + calcula
         └────┬──────────────┘
              │
         ┌────▼────┐
         │   END   │
         └─────────┘
```
