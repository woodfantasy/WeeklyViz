# WeeklyViz Quality Standard

Use this standard for report planning, implementation, visual review, and release decisions.

## Quality Bar

A strong WeeklyViz report should:

1. State one decision-relevant conclusion near the top.
2. Place 3-6 proof objects close to that conclusion.
3. Combine metrics with interpretation, verified outcomes, risks, or next actions.
4. Change visual rhythm across KPI, chart, workstream, risk, and action sections.
5. Preserve source traceability without turning provenance into the dominant visual layer.
6. Remain readable and functional at 1440px and 390px.

## Measurable Checks

- No decision-relevant modeled section is silently omitted by the selected default layout. A non-operating layout may fold duplicate metric detail into equivalent KPI cards.
- No unexplained blank desktop column or empty kanban lane remains.
- Four to six KPIs use two or three desktop columns, not one.
- Metadata and badges are at least 10px; recurring body copy is normally at least 12px.
- Desktop full-page height is driven by content, not repeated oversized cards.
- Mobile uses one readable content column, horizontal tab scrolling, and explicit table overflow.
- Navigation exposes only sections that exist and every control has an observable result.
- Large values use locale-appropriate compact formatting instead of schema unit names.

## Release Matrix

Render every theme with its canonical layout, then render one representative theme through all four layouts. Verify:

- 1440x1200 desktop top and full-page views
- 1024px and 768px intermediate widths
- 390x844 mobile full-page view
- HTML validation, offline reload, export/reopen, editing, reset, print, theme switching, source expansion, and chart resize

## Upgrade Priorities

### P0: Content Integrity

- Prevent layout defaults from dropping KPI, metric, progress, risk, or action collections.
- Keep numeric formatting, units, source references, and derived formulas trustworthy.
- Ensure gallery and evaluation outputs use collision-free filenames.

### P1: Adaptive Composition

- Make KPI, metric, chart, and kanban grids respond to item count.
- Remove empty columns and reduce repeated card rhythm.
- Keep operating-review navigation and controls usable on mobile.

### P2: Stronger Theme Identity

- Maintain theme-specific typography, geometry, Hero, chart styling, and section transitions through the template design contract.
- Keep shared component behavior and accessibility stable across themes.

### P3: Automated Visual Evaluation

- Run browser-based checks for overflow, computed font floors, clipped content, page height, dead navigation, chart initialization, responsive KPI composition, and screenshot diffs.
- Use only synthetic committed fixtures. Private reference reports may be reviewed locally but must never enter fixtures, screenshots, code, or documentation.

## Automated Gate

```bash
npm run test:unit
npm run visual:test
```

The visual gate covers every bundled theme at desktop and mobile sizes. Update baselines with `npm run visual:update` only after intentional review.
