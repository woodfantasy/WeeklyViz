# Design System

WeeklyViz uses responsive long-page reports with a calm editorial rhythm and restrained interaction.

Use [visual-composition.md](visual-composition.md) for page-level narrative and density decisions. This file governs tokens and component behavior.

## Templates

- **Executive**: compact leadership dashboard, neutral surfaces, high information density.
- **Editorial**: expressive lavender reference style, larger typography, richer section transitions.
- **Product Operations**: precise grid, technical labels, strong progress and status treatment.

Templates define visual language and canonical composition. Theme colors remain editable independently.

Each template has a `design` contract:

- `typography`: separate display, body, numeric, and label stacks.
- `geometry`: card shape, section treatment, radii, borders, and shadows.
- `hero`: a theme-specific opening motif.
- `chart`: palette, grid, curve, symbol, bar, area, donut, and legend behavior.

Keep these signatures distinct across the theme library. See [theme-language.md](theme-language.md).

## Tokens

Each report supplies `primary`, `accent`, `background`, `surface`, `text`, and `muted`. The runtime derives borders and subtle fills. Keep:

- Body text contrast at WCAG AA or better.
- Semantic colors independent from the brand palette.
- A system CJK font stack for offline reliability.
- Consistent spacing, radii, borders, and focus rings.

## Components

Prefer open sections, ruled lists, charts, and a small number of strong cards. Avoid nesting cards inside cards. KPI cards may be prominent; ordinary prose does not need a container.

Use continuous animation only when it communicates state. Respect `prefers-reduced-motion`. All controls need visible focus, labels, and keyboard operation.

- KPI `details` are short label-value evidence rows, not a second paragraph.
- Chart `insight_points` should explain peaks, troughs, variance, or decision implications.
- Section `outcome` records the verified result; `next` records the next action.
- Source markers stay summarized by default and expand through the source control.
- Avoid orphan cards. When a row has an odd final chart, use the wide chart composition with a dedicated takeaway panel.
- Format large numeric values for the reader's locale; do not expose schema unit names such as `integer` or `currency`.
- Keep metadata and badges at 10px or larger. Use 12-16px for recurring body copy and 30-48px for primary KPI values.

## Presentation Controls

`presentation` controls composition without changing business data:

- `density`: `compact`, `balanced`, or `spacious`.
- `section_layout`: default `cards`, `grid`, or `list`.
- `source_display`: `summary` or `expanded`.
- `show_toc`: whether to render the sticky report index.

Sections may override the global layout with their own `layout`.

## Responsive Behavior

- Wide: KPI grids may use 3 columns; progress grids may use 4 when the data count supports it.
- Medium: reduce to 2 columns and stack chart commentary.
- Mobile: use 1 column, preserve readable chart height, and allow tables to scroll.
- Never preserve a desktop multi-column card grid by squeezing columns below readable width.
- Never hide source notes, units, or chart meaning to make a layout fit.
- Operating-review filters and tabs must remain usable without clipping at 390px.

## Visual Regression

Run `npm run visual:test` after any template or runtime visual change. The browser audit renders all themes at 1440x1200, 1024x900, 768x900, and 390x844, checks computed font floors, overflow, clipped text, navigation targets, chart initialization, design attributes, and KPI responsiveness, then compares full-page screenshots against synthetic baselines.

Use `npm run visual:update` only for an intentional visual change after inspecting the generated output under `output/playwright/visual-regression/`.
