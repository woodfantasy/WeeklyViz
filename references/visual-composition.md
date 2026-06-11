# Visual Composition

Use this guide before writing `report-model.json`. A strong weekly report is a decision surface, not a formatted source dump.

## Composition Plan

Write a short plan with:

1. **Decision headline**: the one conclusion a reader should retain.
2. **Proof objects**: 3-5 metrics, charts, tables, or delivery outcomes that prove the headline.
3. **Section rhythm**: choose where the page changes pace between KPI, chart, card grid, list, risk, and next-action views.
4. **Density**: choose `compact`, `balanced`, or `spacious`.
5. **Traceability treatment**: default to summarized source markers. Expand source labels only when audit visibility is central.

## Claim, Evidence, Action

For each major business item, prefer this structure when sources support it:

- `body`: what changed and why it matters.
- `metrics`: compact evidence that is useful without a chart.
- `outcome`: the verified result of the work.
- `next`: the next decision, milestone, or experiment.

Do not repeat the same sentence in all four fields. Omit unsupported fields instead of filling them with generic language.

## Layout Selection

- `cards`: default for mixed workstreams with medium-length descriptions.
- `grid`: use for short, parallel business lines where comparison matters.
- `list`: use for sequential delivery plans, technical detail, or items that require more reading width.

Avoid more than two consecutive sections with the same visual rhythm when another faithful proof object is available.

## Density Rules

### Compact

- Best for operating reviews and multi-business weekly reports.
- Keep KPI notes to one or two lines.
- Prefer 2-column business cards and 4-column progress blocks on wide screens.
- Use `details`, `metrics`, and `insight_points` to increase evidence density without adding prose.

### Balanced

- Best for general team reports.
- Allow more explanation in the summary and section cards.
- Keep a mix of 2-column charts and cards.

### Spacious

- Best for short editorial reports with few metrics.
- Use larger headings and fewer sections.
- Do not use spacious mode to hide weak information architecture.

## Count-Aware Layout

- 1 KPI may stand alone; 2-3 should form one balanced row.
- 4-6 KPIs should form a compact matrix rather than a desktop single-column stack.
- For 7 or more KPIs, promote only the decision set and place supporting metrics in detail cards or a table.
- A business card should normally contain a claim plus at least one of: evidence, verified outcome, next action.
- Remove empty kanban columns. Do not reserve equal width for absent content.
- Use a wide final card only to resolve an odd row when it adds hierarchy, not as decorative filler.

## Reference Use

Treat a reference report as a quality bar, not a template to copy blindly.

Extract:

- hierarchy and page rhythm
- card density and proof placement
- typography contrast
- use of brand assets
- interaction ideas

Reject:

- fixed-width layouts that break on mobile
- initial `contenteditable=true`
- decorative assets without provenance
- visible source clutter
- functionality that cannot round-trip through the report model

## Whole-Page Test

Capture a full-page screenshot at 1440px and inspect it at thumbnail size.

The page should show:

- a clear opening claim
- immediate evidence near the top
- distinct section rhythms
- no orphan card or unexplained blank column
- balanced chart and commentary areas
- a concise ending with risks and next actions

Then capture 390px. Cards must stack, text must remain horizontal and readable, and no fixed desktop grid may survive by shrinking into narrow columns.

Treat 10px as the floor for metadata and 12px as the practical floor for sustained reading. If the page only fits by going smaller, reduce repetition or change composition.
