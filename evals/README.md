# Evaluation Data Policy

All fixtures, prompts, names, dates, progress updates, and metrics in this
directory are synthetic. They exist only to test WeeklyViz extraction,
validation, rendering, responsiveness, and interaction behavior.

Do not copy production reports, customer data, internal project names, or
benchmark artifacts into this directory. New golden models must set
`metadata.synthetic` to `true` and identify their sources as synthetic.

`visual-baselines/` contains full-page desktop and mobile screenshots generated
only from `fixtures/report-model.json`. Run `npm run visual:test` to compare
current output and `npm run visual:update` only after intentionally reviewing
and accepting a visual change.
