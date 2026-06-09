# Chart Selection

Select a chart only when it answers a named business question. Every chart requires a title, question, unit, source references, and a short insight.

| Type | Use when | Do not use when |
|---|---|---|
| KPI card | One current value deserves emphasis | A time series or category comparison is the real question |
| Progress / bullet | Comparing actual with a target | There is no target or comparable baseline |
| Line / area | Showing chronological change, normally with at least 4 periods | Categories are unordered |
| Vertical bar | Comparing a modest number of categories | Labels are long or ranking is central |
| Horizontal bar | Ranking categories or showing long labels | Time is the primary axis |
| Grouped bar | Comparing the same metric across groups or periods | More than 3-4 series make it crowded |
| Stacked bar | Showing composition and total together | Exact comparison of inner segments matters |
| Donut / pie | A meaningful whole has 2-6 nonnegative parts | Values do not sum to a whole, slices are close, or precision matters |
| Waterfall | Explaining positive and negative contributions to net change | Values are independent categories |
| Funnel | Showing ordered stages in a conversion process | Stages are not sequential |
| Scatter | Testing the relationship between two numeric variables | There are too few observations |
| Heatmap | Showing intensity across a category-by-time or matrix grid | Exact lookup is the main need |
| Timeline | Showing milestones, dates, and delivery state | Comparing magnitudes |
| Table | Exact lookup, mixed units, or many categories | A clear visual pattern is more important |

## Guardrails

- Keep units consistent within a series.
- Preserve zero on bar-chart value axes unless a documented exception is necessary.
- Sort ranking bars intentionally; keep chronological charts chronological.
- Represent progress above 100% without hiding the overachievement value.
- Use color plus labels or symbols for status.
- Do not chart unsupported numbers extracted from qualitative prose.
- Prefer a donut over a pie for report dashboards, but apply the same part-to-whole restrictions.
