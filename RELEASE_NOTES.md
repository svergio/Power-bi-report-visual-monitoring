## Only visual detection

This release keeps the monitoring scope **visual**: render, compare to baseline, persist history. See the changelog for packaging history; **0.2.0** adds public documentation and a GitHub Pages landing site.

### Highlights

- GitHub Pages: [https://svergio.github.io/Power-bi-report-visual-monitoring/](https://svergio.github.io/Power-bi-report-visual-monitoring/)
- Bilingual README (English SEO lead + full Russian section)
- `docs/DATABASE.md` and English `COMMENT ON` in `schema.sql`
- `ROADMAP.md` for upcoming sprints

### Deploy Pages

In the repository **Settings → Pages**: set **Source** to **GitHub Actions**. Pushes to `main` run `.github/workflows/pages.yml` and publish the `docs/` directory.

### Known limitations

- No distributed queue yet (Redis profile in compose is reserved)
- Roadmap items (user scripts, OCR, REST/MySQL probes, k8s, Zabbix, Grafana) are not implemented in this tag
