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
- Confirm all three templates render without clipping.
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
