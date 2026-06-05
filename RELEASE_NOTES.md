## Only visual detection (EN)

This release keeps the monitoring scope **visual**: render, compare to baseline, persist history. See the changelog for packaging history; **0.2.0** adds public documentation and a GitHub Pages landing site.

### Highlights

- GitHub Pages: [https://svergio.github.io/Power-bi-report-visual-monitoring/](https://svergio.github.io/Power-bi-report-visual-monitoring/) (bilingual EN/RU on the landing page)
- Bilingual README (English SEO lead + full Russian section)
- `docs/DATABASE.md` (EN/RU) and English `COMMENT ON` in `schema.sql`
- `ROADMAP.md` (EN/RU) for upcoming sprints

### Deploy Pages

In the repository **Settings → Pages**: set **Source** to **GitHub Actions**. Pushes to `main` run `.github/workflows/pages.yml` and publish the `docs/` directory.

### Known limitations

- No distributed queue yet (Redis profile in compose is reserved)
- Roadmap items (user scripts, OCR, REST/MySQL probes, k8s, Zabbix, Grafana) are not implemented in this tag

---

## Только визуальная детекция (RU)

Объём релиза по-прежнему **визуальный**: рендер, сравнение с baseline, сохранение истории. История упаковки — в changelog; **0.2.0** добавляет публичную документацию и лендинг GitHub Pages.

### Основное

- GitHub Pages: [https://svergio.github.io/Power-bi-report-visual-monitoring/](https://svergio.github.io/Power-bi-report-visual-monitoring/) (лендинг EN/RU)
- Двуязычный README (английский блок для SEO + полная русская часть)
- `docs/DATABASE.md` (EN/RU), комментарии `COMMENT ON` в `schema.sql` на английском
- `ROADMAP.md` (EN/RU) по спринтам

### Публикация Pages

**Settings → Pages** репозитория: источник **GitHub Actions**. Push в `main` запускает `.github/workflows/pages.yml` и публикует каталог `docs/`.

### Ограничения

- Распределённой очереди пока нет (профиль Redis в compose зарезервирован)
- Пункты roadmap (скрипты пользователя, OCR, REST/MySQL, k8s, Zabbix, Grafana) в этом теге не реализованы
