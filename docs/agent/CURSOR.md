# Cursor agent: Wiki and doc maintenance

In this repository the **Cursor assistant** is expected to help maintain:

- [`wiki/`](../../wiki/) — Markdown sources for [GitHub Wiki](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki)
- [docs/index.html](../index.html) — GitHub Pages long article (EN/RU), including **SEO** metadata in `<head>` (title, description, canonical, Open Graph, structured data where appropriate)
- Cross-links in [README.md](../../README.md) and [CHANGELOG.md](../../CHANGELOG.md) when documentation navigation changes

Human maintainers own product code in `src/`; agents should not change runtime behaviour unless explicitly asked.

## Sync GitHub Wiki from `wiki/`

1. Clone the wiki remote (SSH or HTTPS): `git clone https://github.com/svergio/Power-bi-report-visual-monitoring.wiki.git`
2. Copy all files from this repo’s `wiki/` directory into the clone root (`Home.md`, `_Sidebar.md`, and every `*.md` page).
3. `git add -A`, `git commit`, `git push` inside the wiki clone.

Keep slugs aligned with filenames (hyphens preserved for pages like `Architecture-and-pipeline`).

## Git attribution (co-authored-by)

For commits that **only** touch documentation trees (`wiki/**`, `docs/**` including `docs/agent/**` and Pages HTML, plus a short `[Unreleased]` note in `CHANGELOG.md` when documenting that wave), the commit message **may** end with:

```
Co-authored-by: Cursor <cursoragent@cursor.com>
```

Do **not** add that trailer for commits that change application logic under `src/` or other production code. Do **not** change the user’s global `git config`; primary author remains the local Git user.
