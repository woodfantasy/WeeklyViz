# QA Checklist

## Data

- Every KPI, progress item, and chart has valid `source_refs`.
- Derived values declare a formula.
- Units, dates, percentages, and period labels are internally consistent.
- No numeric claim was invented from qualitative text.
- Keep `evals/` fully synthetic. Never copy production reports, customer data, internal project names, or benchmark artifacts into fixtures or golden outputs.
- Require `metadata.synthetic: true` and explicit synthetic source notes for committed evaluation models.

## Visual

- Verify at 1440, 1024, 768, and 390 CSS pixels.
- Capture a 1440px full-page screenshot and inspect it at thumbnail size.
- Confirm the opening claim, proof objects, section rhythm, risks, and next actions are visually distinct.
- Check for orphan cards, unexplained blank columns, repeated section layouts, and excessive page height.
- Check section rhythm, type hierarchy, chart labels, table overflow, and long Chinese text.
- Confirm recurring body copy is at least 12px and metadata, units, status labels, and source markers are at least 10px.
- Confirm 4-6 KPIs form a compact matrix on desktop and a single readable column on mobile.
- Confirm no decision-relevant collection silently disappears. When duplicate metric detail is folded into KPI cards, preserve the corresponding values and units.
- Confirm empty kanban columns do not consume desktop width.
- Render every bundled theme discovered from `assets/templates/*.json`; do not limit coverage to the three legacy aliases.
- The expected theme set is `canghai`, `cangshan`, `dailan`, `hupo`, `luoli`, `moyi`, `mushanzi`, `qianzi`, `qiuli`, `songye`, `wanying`, `yanzhi`, `yuanshan`, and `zhuqing`.
- Confirm each theme retains a unique typography, geometry/Hero, and chart signature.
- Test each theme with its canonical parent layout, then test `dashboard`, `operating-review`, `newsletter`, and `kanban` with at least one representative theme from each style family.
- Confirm theme and layout are independent: overriding `presentation.layout` must not discard the selected theme tokens or break section rendering.
- Keep the HTML below 5 MB unless user-provided images explain the excess.

## Interaction

- Report starts read-only.
- Edit text, KPI data, chart data, and theme colors.
- Expand and collapse detailed source labels.
- Verify undo, reset, autosave, print/PDF, export, reopen, and exact data round-trip.
- Confirm charts redraw after resize and theme changes.

## Accessibility And Offline

- Navigate controls by keyboard and inspect focus styles.
- Verify semantic headings, landmarks, labels, ARIA chart descriptions, and status announcements.
- Test `prefers-reduced-motion`.
- Disconnect the network and reload.
- Confirm there are no external scripts, stylesheets, fonts, console errors, or `eval`.

## Automated Visual Gate

```bash
npm ci
npm run test:unit
npm run visual:test
```

`visual:test` renders all themes at 1440x1200, 1024x900, 768x900, and 390x844, performs structural browser checks, and compares full-page screenshots. Use `npm run visual:update` only after inspecting the generated changes and confirming that the fixture is synthetic.
