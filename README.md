English | [中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt.md) | [Français](README.fr.md)

<p align="center">
  <img src="assets/logo.svg" width="128" height="128" alt="WeeklyViz Logo">
</p>

<h1 align="center">WeeklyViz</h1>

<p align="center">
  <strong>Professional Offline HTML Weekly Report Generator & Agent Skill</strong>
</p>

<p align="center">
  <a href=""><img src="https://img.shields.io/badge/version-0.1.1-blue.svg" alt="Version"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
  <a href=""><img src="https://img.shields.io/badge/platform-Codex_/_Claude_Code-purple.svg" alt="Platform"></a>
</p>

<p align="center">
  Turn raw updates, spreadsheets, and documents into <strong>professional, responsive, editable, and source-traceable offline HTML weekly reports</strong> — in one shot.
</p>

A Claude Skill and standalone tool built on the [Agent Skills](https://agentskills.io) specification. It combines structural data extraction with an editorial-grade design system to turn work prose, KPIs, and charts into a polished weekly executive briefing. Designed to help developers, product managers, and operations teams eliminate the "messy copy-paste" weekly update and deliver high-impact, visual reports.

---

## ✨ Core Capabilities

| Capability | Description |
|------------|-------------|
| 📊 **Multi-Source Extraction** | Automatically parses and processes `.xlsx`, `.csv`, `.docx`, `.md`, `.markdown`, and `.txt` files to extract raw metrics, tables, prose, and update lists. |
| 🛡️ **Strict Schema Validation** | Enforces a robust JSON schema (`report.schema.json`) checking data types, chronological series rules, part-to-whole proportions, and status labels before rendering. |
| 🎨 **Editorial Design System** | Features three built-in high-quality themes (`Executive`, `Editorial`, `Product Operations`) with responsive, typography-paired layouts and zero external network dependencies (fully offline). |
| 🔗 **Source Traceability** | Automatically links every KPI, progress bar, chart, and list item back to its origin file and line location using stable hash IDs, ensuring complete integrity. |
| ✏️ **Interactive Editing** | The rendered HTML is fully interactive: edit text and numbers inline, modify chart data, adjust theme colors, and download the edited model or print/PDF directly. |
| 📈 **Apache ECharts Integration** | Bundles a local, self-contained ECharts runtime (`echarts.min.js`) for rendering lines, bars, donuts, funnels, heatmaps, and waterfalls offline. |
| 🔍 **Systematic QA Checks** | Includes a headless HTML structure and accessibility validation script (`validate_html.mjs`) to verify keyboard focus, semantic HTML5, and offline reliability. |

---

## 🚀 Quick Start

### 1. Install the Skill

<details>
<summary><b>Claude Code</b></summary>

Place the `weeklyviz/` folder under `.claude/skills/` in your project root:

```bash
# Clone into your project's Skill directory
git clone https://github.com/woodfantasy/WeeklyViz.git .claude/skills/weeklyviz
```

Claude Code will automatically detect and load the Skill.
</details>

<details>
<summary><b>Cursor</b></summary>

Place the `weeklyviz/` folder under `.cursor/skills/` in your project root:

```bash
git clone https://github.com/woodfantasy/WeeklyViz.git .cursor/skills/weeklyviz
```

Cursor Agent mode will automatically read the Skill instructions from `SKILL.md`.
</details>

<details>
<summary><b>Codex / OpenClaw</b></summary>

For Codex, place the folder under the agent's instructions folder:
```bash
git clone https://github.com/woodfantasy/WeeklyViz.git agents/skills/weeklyviz
```

For OpenClaw, register the repository link:
```
Please learn this skill: https://github.com/woodfantasy/WeeklyViz
```
</details>

### 2. Basic Workflow

#### Step 1: Extract Data
Gather all your weekly spreadsheets, notes, or Markdown updates into a single folder and run the extraction script:

```bash
python3 scripts/weeklyviz.py extract \
  --input path/to/metrics.xlsx path/to/updates.md \
  --output source-bundle.json
```
This parses files and maps them to unique source hashes in `source-bundle.json`.

#### Step 2: Compose Report Model
Write a composition plan and construct a `report-model.json` following [report.schema.json](references/report.schema.json). Every KPI, progress bar, and chart must specify `source_refs` pointing back to the hashes inside `source-bundle.json`.

#### Step 3: Validate and Render HTML
Validate the report model and compile the final offline HTML report:

```bash
# Validate model structure and constraints
python3 scripts/weeklyviz.py validate --report report-model.json

# Render HTML
python3 scripts/weeklyviz.py render --report report-model.json --output weekly-report.html

# Validate HTML accessibility and assets offline
node scripts/validate_html.mjs weekly-report.html
```

---

## 📁 Project Structure

```
WeeklyViz/
├── README.md                      # English documentation
├── README.zh-CN.md                # Chinese documentation
├── .gitignore                     # Git ignore file
├── SKILL.md                       # Core instructions (the Skill's brain)
├── agents/
│   └── openai.yaml                # OpenAI Custom Agent configuration
├── scripts/
│   ├── weeklyviz.py               # Main CLI (extract, validate, render)
│   └── validate_html.mjs          # HTML structure & A11y validator
├── references/
│   ├── report.schema.json         # JSON Schema for report data models
│   ├── chart-selection.md         # Guidelines for choosing the right charts
│   ├── design-system.md           # Design system tokens and layouts
│   ├── visual-composition.md      # Composition density and rhythms
│   └── qa-checklist.md            # Quality assurance checklist
├── assets/
│   ├── logo.svg                   # Vector brand logo
│   ├── runtime/
│   │   ├── report.css             # Report styling
│   │   └── report.js              # Interactive inline editor
│   ├── templates/
│   │   ├── executive.json         # Executive dark mode template
│   │   ├── editorial.json         # Editorial lavender typography template
│   │   └── product-operations.json # Operative details & grid template
│   └── vendor/
│       └── echarts.min.js         # Apache ECharts runtime (pinned v5)
├── tests/
│   └── test_weeklyviz.py          # Python unittest suite
└── evals/
    ├── evals.json                 # Evaluation metadata
    ├── README.md                  # Test data policy
    ├── fixtures/
    │   └── report-model.json      # Synthetic report fixture
    └── weeklyviz-golden.html      # Compiled synthetic golden HTML
```

---

## 🔬 Command Reference & Standalone Tools

The command-line interface `weeklyviz.py` handles the local development loop:

```bash
# Display help and commands
python3 scripts/weeklyviz.py --help
```

### Extraction (`extract`)
- Extracts paragraphs from `.txt`, headers and sections from `.md`, tables from `.csv` and `.docx`, and sheets and formulas from `.xlsx`.
- Generates `generated_at`, `sources` array, and warnings for unsupported files (e.g. legacy `.xls`, PDF, `.ppt`).

### Validation (`validate`)
- Ensures `metadata.report_id`, `metadata.title`, and `metadata.period` are present.
- Validates ECharts specific constraints:
  - Line/Area charts require at least 4 chronological categories.
  - Pie/Donut charts require 2-6 categories, a single series, and non-negative values.
  - Funnels require sequential ordered stages.
- Validates that every metric references a valid source ID.

### Rendering (`render`)
- Compiles the template tokens, runtime JS, runtime CSS, vendor ECharts library, and the JSON model into a single self-contained HTML file.
- The compiled HTML contains no external HTTP requests and works entirely offline.

---

## 🏗️ Design System & Themes

WeeklyViz implements three default layouts optimized for different reporting targets (see [design-system.md](references/design-system.md)):

*   **Executive (`executive.json`)**: Neutral background with deep dark primary headers, optimized for executive dashboards with compact spacings.
*   **Editorial (`editorial.json`)**: Uses expressive typography with larger headings and a lavender-themed color palette.
*   **Product Operations (`product-operations.json`)**: A technical grid layout with distinct status borders, progress bars, and high contrast labels.

You can modify layouts globally or at a section level using:
- `density`: `compact`, `balanced`, or `spacious`.
- `section_layout`: `cards`, `grid`, or `list`.
- `source_display`: `summary` or `expanded`.

---

## 📋 Release Versions

*   **v0.1.1** (2026-06-09)
    - Flattened directory hierarchy to root folder for standard agent execution and installation.
    - Redesigned and upgraded the `Editorial` template with Y2K-neutral layouts, glassmorphism, hard-offset shadows, dotted lists, and double sidebars.
    - Safe execution policy for separating user-sensitive weekly report data.
*   **v0.1.0** (2026-06-09)
    - Initial release of the WeeklyViz project.
    - Full-featured parser CLI supporting CSV, XLSX, DOCX, MD, and Plain Text.
    - Model validator checking schema consistency and ECharts requirements.
    - Single-file HTML compilation with interactive client-side editing and ECharts components.
    - Pre-defined Executive, Editorial, and Product Operations templates.
    - Standalone HTML accessibility and structure checker.
