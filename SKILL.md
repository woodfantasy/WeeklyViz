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

3. Read `source-bundle.json` and write a short composition plan before modeling. Define the report's decision headline, 3-5 proof objects, business-section rhythm, risks, next actions, and intended density. Read [visual-composition.md](references/visual-composition.md) and [quality-standard.md](references/quality-standard.md).
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

- Executive themes: `canghai` (dark glassmorphism), `cangshan`, `dailan`, `luoli`, `moyi`.
- Editorial themes: `hupo`, `mushanzi`, `qianzi`, `qiuli`, `wanying`.
- Product and operations themes: `songye`, `yanzhi`, `yuanshan`, `zhuqing`.

The legacy names `executive`, `editorial`, and `product-operations` remain compatibility aliases for `cangshan`, `qianzi`, and `songye`. Prefer a concrete theme ID for new reports so the full theme library is used deliberately.

Choose the report layout independently through `presentation.layout`:

- `dashboard`: dense KPI and operating reviews for leadership.
- `operating-review`: detailed business reviews with sticky section navigation, metrics, OKRs, and requirements.
- `newsletter`: narrative, brand-led, or editorial reporting.
- `kanban`: delivery status, project execution, and operational workflows.

A theme controls visual language; a layout controls page composition. Do not assume that an executive-colored theme must use the dashboard layout, or that an editorial theme must use the newsletter layout.

Every theme owns an independent typography, geometry, Hero, and chart signature through its `design` object. Read [theme-language.md](references/theme-language.md) before modifying or adding a theme. Do not create palette-only variants.

### Content Classification and Selection (板式与主题决策指南)

Before writing the report composition, analyze the raw weekly updates and map them to the ideal layout and template:

| Content Type / 核心内容特征 | Target Layout / 推荐板式 | Target Template / 推荐配色模版 | Rationale / 决策考量 |
| :--- | :--- | :--- | :--- |
| **经营复盘与核心数据**：多维指标、目标、趋势和经营动作 | `operating-review` 或 `dashboard` | `canghai`, `cangshan`, or `dailan` | Use a compact evidence hierarchy and place the most decision-relevant metrics near the opening claim. |
| **版本迭代、研发里程碑与敏捷排期**：状态、负责人、截止时间和依赖关系 | `kanban` | `songye`, `yuanshan`, or `zhuqing` | Emphasize stage, ownership, verified outcome, and next action without preserving empty columns. |
| **故事性叙述、品牌通告或综合汇报**：文本较多、数据较少、强调阅读节奏 | `newsletter` | `qianzi`, `qiuli`, or `hupo` | Use editorial pacing, fewer proof objects, and stronger transitions between narrative sections. |

Honor explicit brand colors. Otherwise use the selected theme defaults. Keep semantic success, warning, and risk colors stable. Read [design-system.md](references/design-system.md) when adapting palettes or adding components.

Set `presentation.density` deliberately:

- `compact`: dense multi-business or operating reviews.
- `balanced`: general weekly reports.
- `spacious`: short, narrative-led reports with few proof objects.

Use card or grid sections only when items are independently scannable. Use list layout for sequential workstreams or long technical explanations.

### Adaptive Composition Contract

- 1-3 KPIs: use one compact row or a balanced asymmetric row.
- 4-6 KPIs: use a 2x2, 3x2, or responsive matrix. Never create a long single-column KPI stack on desktop.
- 7+ KPIs: promote 4-6 decision metrics and move the rest into metric detail or a table.
- Do not drop `kpis`, `metrics`, or `progress` merely because a detailed layout is selected.
- Omit empty kanban columns. Preserve an empty state only when the entire section has no items.
- Avoid more than two consecutive sections with the same card rhythm.
- Keep visible body text at 12px or larger where possible; metadata, status, units, and source markers must remain at least 10px.
- On mobile, stack content rather than shrinking desktop grids. Tables may scroll horizontally; cards and controls may not clip.

## File Naming Convention

When creating a single report, use:

*   **Format**: `<project>-<page_layout>-<timestamp>-model.json`
*   **Format**: `<project>-<page_layout>-<timestamp>-report.html`

For comparison galleries, include every varying dimension so files cannot overwrite one another:

*   **Format**: `<project>-<page_layout>-<section_layout>-<theme>-<timestamp>-model.json`
*   **Format**: `<project>-<page_layout>-<section_layout>-<theme>-<timestamp>-report.html`

## Input Notes

- Supported: `.xlsx`, `.csv`, `.docx`, `.md`, `.markdown`, `.txt`.
- Multiple files may be extracted together.
- Legacy `.xls`, PDF, and PPT are not supported in v1. Ask for conversion instead of silently dropping them.
- Extraction is deterministic and uses Python's standard library.

## Bundled Resources

- `scripts/weeklyviz.py`: extract, validate, and render.
- `scripts/validate_html.mjs`: validate output structure, accessibility hooks, offline behavior, and embedded model integrity.
- `scripts/visual_regression.mjs`: render every theme in Chrome, audit computed layout metrics, and compare full-page desktop/mobile baselines.
- `references/`: model schema, chart rules, design system, and QA checklist.
- `assets/runtime/`: self-contained report CSS and editing runtime.
- `assets/vendor/echarts.min.js`: pinned Apache ECharts runtime for offline charts.
- `evals/fixtures/`: representative source and report-model fixtures.
- `evals/visual-baselines/`: synthetic full-page visual baselines for all bundled themes.

## Skill Maintenance

After changing templates, report CSS, chart rendering, composition defaults, or runtime behavior:

```bash
npm ci
npm run test:unit
npm run visual:test
```

Use `npm run visual:update` only after reviewing all generated screenshots and intentionally accepting the new output. Baselines must use the committed synthetic fixture; never generate them from a production or benchmark report.
