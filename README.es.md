[[English](README.md) | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | Español | [Português](README.pt.md) | [Français](README.fr.md)

<p align="center">
  <img src="assets/logo.svg" width="128" height="128" alt="WeeklyViz Logo">
</p>

<h1 align="center">WeeklyViz</h1>

<p align="center">
  <strong>Generador de Informes Semanales HTML Offline y Skill de Agente Profesional</strong>
</p>

<p align="center">
  <a href=""><img src="https://img.shields.io/badge/version-0.11-blue.svg" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
  <a href=""><img src="https://img.shields.io/badge/platform-Codex_/_Claude_Code-purple.svg" alt="Platform"></a>
</p>

<p align="center">
  Convierta actualizaciones de texto, hojas de cálculo y documentos en <strong>informes semanales HTML offline profesionales, adaptables, editables y con trazabilidad de origen</strong>.
</p>

Es un Claude Skill y herramienta independiente construida bajo la especificación [Agent Skills](https://agentskills.io). Combina la extracción estructurada de datos con un sistema de diseño de nivel editorial para transformar texto de trabajo, KPIs y gráficos en informes ejecutivos pulidos. Diseñado para ayudar a desarrolladores, managers de producto y operaciones a eliminar los informes semanales desordenados de copiar y pegar y entregar reportes visuales de alto impacto.

---

## ✨ Capacidades Clave

| Capacidad | Descripción |
|------------|-------------|
| 📊 **Extracción Multifuente** | Procesa automáticamente archivos `.xlsx`, `.csv`, `.docx`, `.md`, `.markdown` y `.txt` para extraer métricas, tablas, texto y listas de progreso. |
| 🛡️ **Validación Estricta** | Garantiza la integridad mediante un esquema JSON (`report.schema.json`) que valida tipos de datos, series temporales, proporciones y etiquetas antes de renderizar. |
| 🎨 **Sistema de Diseño Editorial** | Ofrece tres temas integrados (`Executive`, `Editorial`, `Product Operations`) con diseños adaptables y sin dependencias de red externas (100% offline). |
| 🔗 **Trazabilidad de Origen** | Vincula automáticamente cada KPI, barra de progreso, gráfico y lista con su archivo y línea de origen mediante IDs hash estables. |
| ✏️ **Edición Interactiva** | El HTML generado permite editar textos y números en línea, cambiar colores de temas y exportar directamente a formato impreso o PDF. |
| 📈 **Integración de Apache ECharts** | Incluye un motor de ECharts local (`echarts.min.js`) para renderizar gráficos de línea, barra, rosca, embudo y cascada sin conexión. |
| 🔍 **Verificación de Calidad** | Incluye un script de validación de accesibilidad y estructura HTML (`validate_html.mjs`) para garantizar el correcto comportamiento offline. |

---

## 🚀 Inicio Rápido

### 1. Instalar la Skill

<details>
<summary><b>Claude Code</b></summary>

Coloque la carpeta `weeklyviz/` dentro de `.claude/skills/` en la raíz de su proyecto:

```bash
git clone https://github.com/woodfantasy/WeeklyViz.git .claude/skills/weeklyviz
```
</details>

<details>
<summary><b>Cursor</b></summary>

Coloque la carpeta `weeklyviz/` dentro de `.cursor/skills/` en la raíz de su proyecto:

```bash
git clone https://github.com/woodfantasy/WeeklyViz.git .cursor/skills/weeklyviz
```
</details>

### 2. Flujo de Trabajo Básico

#### Paso 1: Extraer Datos
```bash
python3 scripts/weeklyviz.py extract \
  --input path/to/metrics.xlsx path/to/updates.md \
  --output source-bundle.json
```

#### Paso 2: Crear el Modelo del Informe
Defina el archivo `report-model.json` siguiendo el esquema [report.schema.json](references/report.schema.json).

#### Paso 3: Validar y Renderizar
```bash
# Validar estructura y restricciones de gráficos
python3 scripts/weeklyviz.py validate --report report-model.json

# Generar HTML
python3 scripts/weeklyviz.py render --report report-model.json --output weekly-report.html

# Validar accesibilidad
node scripts/validate_html.mjs weekly-report.html
```

---

## 📋 Versiones de Lanzamiento

*   **v0.11.0** (2026-06-09)
    - Estructura de directorios aplanada a la raíz para la instalación y ejecución estándar de agentes.
    - Diseño y actualización premium de la plantilla `Editorial` con fondos de puntos, barra de estilo macOS, sombras sólidas desplazadas, listas de puntos y barras laterales.
    - Política de seguridad para excluir datos locales sensibles de Shiji en el repositorio público.
*   **v0.1.0** (2026-06-09)
    - Versión inicial.
    - Extractor de datos para CSV, XLSX, DOCX, MD y texto plano.
    - Validador de esquemas y comprobador estricto para ECharts.
    - Generación de informes HTML interactivos autocontenidos offline.
