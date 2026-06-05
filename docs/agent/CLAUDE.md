# Agent notes (documentation)

These rules apply to any AI assistant editing **documentation** in this repository (Wiki sources, GitHub Pages HTML, markdown under `docs/`).

## Scope

- Prefer facts from `src/`, `schema.sql`, and `docs/DATABASE.md`. Do not describe [ROADMAP.md](../ROADMAP.md) items as already shipped.
- Bilingual Wiki and long-form Pages: keep **English first**, then **Russian**, separated by a horizontal rule (`---`) on Wiki pages; match the style of [docs/DATABASE.md](../DATABASE.md).
- Do not invent benchmark milliseconds; qualitative comparisons only unless measured externally and cited.

## Style

- No emojis in repository files.
- Minimal comments in code; documentation may use headings and lists freely.
- Avoid duplicating the README verbatim; link to README for install flags and variable tables when detail would only repeat.

## Outputs

- Wiki sources live in [`wiki/`](../../wiki/). GitHub Wiki is synced from that folder via the separate `*.wiki.git` remote (see [CURSOR.md](CURSOR.md)).
