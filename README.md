[中文](README.zh-CN.md) | English | [日本語](README.ja.md) | [한국어](README.ko.md) | [Español](README.es.md) | [Português](README.pt.md) | [Français](README.fr.md)

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
  Turn raw updates, spreadsheets, and documents into <strong>professional, responsive, editable, and source-traceable offline HTML weekly reports</strong> — in one shot, powered by your AI Agent.
</p>

A Claude Skill and standalone tool built on the [Agent Skills](https://agentskills.io) specification. It is designed to work seamlessly with AI Agents (such as Claude Code, Cursor, or Codex). Instead of running python scripts or coding yourself, you simply install the skill and let your AI Agent do all the heavy lifting.

---

## 🖼️ Example Output

<p align="center">
  <a href="assets/weeklyviz-multi-layout-showcase.jpg">
    <img src="assets/weeklyviz-multi-layout-showcase.jpg" width="860" alt="WeeklyViz multi-layout weekly report showcase">
  </a>
</p>

<p align="center"><sub>The same source data, rendered as editorial reports, executive dashboards, Kanban updates, and data tables. Every output is responsive, editable, traceable, and offline-ready. Click the image to view it at full resolution.</sub></p>

---

## ✨ Core Capabilities

| Capability | Description |
|------------|-------------|
| 📊 **Multi-Source Extraction** | Automatically parses and processes `.xlsx`, `.csv`, `.docx`, `.md`, and `.txt` files to extract raw metrics and update lists. |
| 🎨 **Multi-Layout Design System** | Includes 13 professional themes and multiple report layouts for editorial storytelling, executive dashboards, Kanban progress, and dense data views, all responsive and offline-ready. |
| 🔗 **Source Traceability** | Links every KPI, progress bar, chart, and list item back to its origin file and line location, ensuring complete data integrity. |
| ✏️ **Interactive Editing** | The output HTML is fully interactive: edit text and numbers inline, modify chart data, adjust theme colors, and save/print directly. |
| 📈 **ECharts Integration** | Pinned Apache ECharts runtime for rendering interactive lines, bars, donuts, and funnels offline. |

---

## 🚀 How to Use (Super Simple)

### 1. Install the Skill
Add WeeklyViz to your AI Agent's skill folder:

*   **Claude Code**: Clone this repository into `.claude/skills/weeklyviz` in your project root.
*   **Cursor**: Clone this repository into `.cursor/skills/weeklyviz` in your project root.
*   **Other Agents**: Place the repository under your agent's custom instructions path.

### 2. Just Ask Your Agent!
You do **not** need to run Python commands or write configuration files. Just hand your raw files (e.g. spreadsheets, notes, pastes) to your AI Agent and ask:

> *"Hey Claude, use WeeklyViz to generate a weekly report from my notes."*

The agent will automatically read your files, extract metrics, validate constraints, and compile the final offline HTML report (`weekly-report.html`) for you in one shot.

---

## 🛠️ Developer Details (Optional)

If you wish to run WeeklyViz manually via the command line:

```bash
# Extract raw data to source bundle
python3 scripts/weeklyviz.py extract --input notes.md data.xlsx --output source-bundle.json

# Validate report model schema
python3 scripts/weeklyviz.py validate --report report-model.json

# Compile into self-contained HTML
python3 scripts/weeklyviz.py render --report report-model.json --output weekly-report.html
```

---

## 📋 Release Versions

*   **v0.1.1** (2026-06-09)
    - Flattened directory hierarchy to root folder for standard agent execution and installation.
    - Redesigned and upgraded the `Editorial` template with Y2K-neutral layouts, glassmorphism, hard-offset shadows, dotted lists, and double sidebars.
    - Safe execution policy for separating user-sensitive weekly report data.
*   **v0.1.0** (2026-06-09)
    - Initial release of the WeeklyViz project.
