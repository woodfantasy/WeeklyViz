---
name: weeklyviz
description: Generate professional, responsive, editable, source-traceable offline HTML weekly reports from XLSX, CSV, DOCX, Markdown, text, pasted content, or Feishu/Lark exports. Use when Codex needs to turn work updates, operating metrics, project progress, risks, or next-week plans into a polished visual report with appropriate charts, adaptive themes, local editing, and reliable HTML export.
---

# WeeklyViz

Create reports through the bundled data model and renderer. Do not hand-write the final HTML or invent missing metrics.

## Workflow

1. Gather all source files. For Feishu/Lark, use an available connector to retrieve document or sheet content; otherwise request DOCX, XLSX, Markdown, or pasted text.
2. Extract sources:

   ```bash
   python3 scripts/weeklyviz.py extract --input <files...> --output source-bundle.json
   ```

3. Read `source-bundle.json` and write a short composition plan before modeling. Define the report's decision headline, 3-5 proof objects, business-section rhythm, risks, next actions, and intended density. Read [visual-composition.md](references/visual-composition.md).
4. Write `report-model.json` conforming to [report.schema.json](references/report.schema.json). Use optional KPI `details`, chart `insight_points`, and section-item `outcome`, `metrics`, and `next` when the source supports them.
5. Attach `source_refs` to every KPI, progress metric, and chart. For a derived value, also set `derived: true` and record `formula`. Never infer unsupported numeric values from prose.
6. Read [chart-selection.md](references/chart-selection.md) before selecting charts. Prefer a table or prose when the data does not justify a chart.
7. Validate and render:

   ```bash
   python3 scripts/weeklyviz.py validate --report report-model.json
   python3 scripts/weeklyviz.py render --report report-model.json --output weekly-report.html
   node scripts/validate_html.mjs weekly-report.html
   ```

8. Open the HTML in a browser and capture full-page desktop and mobile screenshots. Judge the whole-page rhythm at thumbnail size, then verify editing, chart updates, source expansion, theme changes, reset, autosave, print/PDF, export, and reopen behavior. Follow [qa-checklist.md](references/qa-checklist.md).

## Report Organization

Use this narrative order when the source supports it:

1. Executive summary
2. Core KPIs
3. Goal progress
4. Trends and variance
5. Business or project progress
6. Risks and blockers
7. Next-week priorities
8. Collapsible source notes

Omit empty sections. Keep the summary decision-oriented and explain important changes without restating every value.

Each major business card should answer, when supported by sources:

- What changed or shipped?
- What evidence proves it?
- What happens next?

Do not force every source paragraph into the visible report. Preserve detail in source notes and prioritize the information needed to make a decision.

## Templates And Themes

Choose a concrete theme from `assets/templates/` based on audience, business context, and desired tone:

- Executive themes: `cangshan`, `dailan`, `luoli`, `moyi`.
- Editorial themes: `hupo`, `mushanzi`, `qianzi`, `qiuli`, `wanying`.
- Product and operations themes: `songye`, `yanzhi`, `yuanshan`, `zhuqing`.

The legacy names `executive`, `editorial`, and `product-operations` remain compatibility aliases for `cangshan`, `qianzi`, and `songye`. Prefer a concrete theme ID for new reports so the full theme library is used deliberately.

Choose the report layout independently through `presentation.layout`:

- `dashboard`: dense KPI and operating reviews for leadership.
- `newsletter`: narrative, brand-led, or editorial reporting.
- `kanban`: delivery status, project execution, and operational workflows.

A theme controls visual language; a layout controls page composition. Do not assume that an executive-colored theme must use the dashboard layout, or that an editorial theme must use the newsletter layout.

Honor explicit brand colors. Otherwise use the selected theme defaults. Keep semantic success, warning, and risk colors stable. Read [design-system.md](references/design-system.md) when adapting palettes or adding components.

Set `presentation.density` deliberately:

- `compact`: dense multi-business or operating reviews.
- `balanced`: general weekly reports.
- `spacious`: short, narrative-led reports with few proof objects.

Use card or grid sections only when items are independently scannable. Use list layout for sequential workstreams or long technical explanations.

## File Naming Convention

When creating report models or output HTML files (especially when generating multiple layouts or variations for comparison), use this standardized naming convention so the page layout, section layout, and style theme are immediately clear:

*   **Format**: `<project>-<page_layout>-<section_layout>-<theme_template>-model.json`
*   **Format**: `<project>-<page_layout>-<section_layout>-<theme_template>-report.html`

Examples:
*   `red-shiji-dashboard-cards-cangshan-model.json` / `red-shiji-dashboard-cards-cangshan-report.html`
*   `red-shiji-dashboard-table-yanzhi-model.json` / `red-shiji-dashboard-table-yanzhi-report.html`
*   `red-shiji-kanban-kanban-yuanshan-model.json` / `red-shiji-kanban-kanban-yuanshan-report.html`
*   `red-shiji-newsletter-list-hupo-model.json` / `red-shiji-newsletter-list-hupo-report.html`
*   `red-shiji-newsletter-cards-editorial-model.json` / `red-shiji-newsletter-cards-editorial-report.html`

## Input Notes

- Supported: `.xlsx`, `.csv`, `.docx`, `.md`, `.markdown`, `.txt`.
- Multiple files may be extracted together.
- Legacy `.xls`, PDF, and PPT are not supported in v1. Ask for conversion instead of silently dropping them.
- Extraction is deterministic and uses Python's standard library.

## Bundled Resources

- `scripts/weeklyviz.py`: extract, validate, and render.
- `scripts/validate_html.mjs`: validate output structure, accessibility hooks, offline behavior, and embedded model integrity.
- `references/`: model schema, chart rules, design system, and QA checklist.
- `assets/runtime/`: self-contained report CSS and editing runtime.
- `assets/vendor/echarts.min.js`: pinned Apache ECharts runtime for offline charts.
- `evals/fixtures/`: representative source and report-model fixtures.
