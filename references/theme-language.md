# Theme Language

Each bundled theme must own a distinct typography, geometry, Hero, and chart language. Color changes alone do not constitute a new theme.

| Theme | Canonical composition | Typography voice | Geometry and section language | Chart language |
| --- | --- | --- | --- | --- |
| `canghai` | operating review | modern display + monospaced evidence | glass cards, glow rules, aurora Hero | neon palette, smooth lines, no grid |
| `cangshan` | dashboard | neutral corporate sans + DIN numerals | structured cards, firm rules, slab Hero | restrained corporate palette, dashed grid |
| `dailan` | dashboard | condensed editorial sans | square ledger cards, banded Hero | ledger palette, solid grid, no symbols |
| `hupo` | newsletter | warm serif reading face | paper cards, bookmark headings, sunset Hero | warm palette, dotted grid, rounded bars |
| `luoli` | dashboard | high-contrast display serif | framed cards, spotlight Hero | luxe palette, dotted grid, diamond points |
| `moyi` | dashboard | monochrome grotesk + mono labels | zero-radius cards, indexed sections, mono grid | black-led palette, solid grid, restrained marks |
| `mushanzi` | operating review | contemporary sans + mono evidence | crystal cards, beam headings, nebula Hero | spectral palette, dashed grid, diamond points |
| `qianzi` | newsletter | fashion serif + refined sans | editorial cards, double rules, lavender wash | couture palette, no grid, smooth lines |
| `qiuli` | newsletter | Chinese book serif | chapter cards, centered headings, parchment Hero | harvest palette, dotted grid, firm lines |
| `songye` | kanban | technical DIN + system sans | compact technical cards, rail headings, blueprint Hero | technical palette, solid grid, rectangular marks |
| `wanying` | newsletter | rounded friendly gothic | pill cards, petal headings, blossom Hero | soft blossom palette, dashed grid, smooth lines |
| `yanzhi` | dashboard | bold display sans | angular cards, slash rules, diagonal Hero | high-energy palette, no grid, diamond points |
| `yuanshan` | kanban | humanist Optima-style display | airy cards, fine rules, horizon Hero | atmospheric palette, dashed grid, smooth lines |
| `zhuqing` | kanban | compact DIN + system sans | cut-corner cards, stamp headings, bamboo grid | bamboo palette, solid grid, rectangular marks |

The contract lives in each `assets/templates/<theme>.json` file:

- `typography`: `display`, `body`, `numeric`, and `label` offline font stacks.
- `geometry`: card and section styles, radii, border weight, and shadows.
- `hero.style`: the opening visual motif.
- `chart`: palette, grid, curve, symbol, bar radius, area opacity, donut proportion, and legend position.

When adding a theme, add a genuinely new signature in all four areas and update the automated visual baseline.
