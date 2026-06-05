This **Wiki** mirrors deep documentation in Markdown (bilingual EN / RU). The canonical code and full install guide remain in the [main repository README](https://github.com/svergio/Power-bi-report-visual-monitoring#readme). Long narrative and SEO-friendly landing: [GitHub Pages](https://svergio.github.io/Power-bi-report-visual-monitoring/).

**Edit workflow:** change files under `wiki/` in the main repo (pull request), then push to [`Power-bi-report-visual-monitoring.wiki.git`](https://github.com/svergio/Power-bi-report-visual-monitoring.wiki.git) (`Home.md`, `_Sidebar.md`, and linked pages), or edit pages in the GitHub Wiki UI (remember to back-port if you want version control in `main`).

---

## English

### What this project is

**Power BI Report Visual Monitoring** is an open-source tool that renders published Power BI reports in a headless browser, captures screenshots, compares them to baselines using a quadtree / MSE pipeline plus perceptual hashing, stores history in PostgreSQL, and optionally keeps gzip-compressed XOR deltas for forensics. It targets teams that need a **repeatable visual contract** on dashboards without rewriting every KPI as warehouse SQL.

### Wiki table of contents

| Page | Topics |
|------|--------|
| [Architecture and pipeline](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki/Architecture-and-pipeline) | Data flow, `Data/` layout, DDD layers, DB vs files |
| [Operations and tuning](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki/Operations-and-tuning) | CLI bootstrap, Docker, env keys, diff tuning, incidents |
| [Limitations and comparisons](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki/Limitations-and-comparisons) | vs Usage Metrics / Performance Analyzer, when SQL wins, RLS |

### Quick links

| Resource | URL |
|----------|-----|
| README | https://github.com/svergio/Power-bi-report-visual-monitoring#readme |
| GitHub Pages (long EN/RU article) | https://svergio.github.io/Power-bi-report-visual-monitoring/ |
| Database schema (markdown) | https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/docs/DATABASE.md |
| DDL | https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/schema.sql |
| Roadmap | https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/ROADMAP.md |
| Contributing | https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/CONTRIBUTING.md |

---

## Русский

### О чём проект

**Power BI Report Visual Monitoring** &mdash; открытый инструмент: headless-браузер рендерит опубликованные отчёты Power BI, делает снимки, сравнивает с baseline (quadtree / MSE + перцептивный хеш), пишет историю в PostgreSQL и при необходимости хранит gzip-сжатые XOR-дельты. Цель &mdash; **воспроизводимый визуальный контракт** по дашбордам без переписывания каждого KPI как SQL на витрине.

### Оглавление вики

| Страница | Темы |
|----------|------|
| [Architecture and pipeline](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki/Architecture-and-pipeline) | Поток данных, каталог `Data/`, слои DDD, БД и файлы |
| [Operations and tuning](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki/Operations-and-tuning) | CLI, Docker, переменные окружения, настройка diff, инциденты |
| [Limitations and comparisons](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki/Limitations-and-comparisons) | Сравнение с Usage Metrics / Performance Analyzer, когда нужен SQL, RLS |

### Быстрые ссылки

| Ресурс | URL |
|--------|-----|
| README | https://github.com/svergio/Power-bi-report-visual-monitoring#readme |
| GitHub Pages (длинная статья EN/RU) | https://svergio.github.io/Power-bi-report-visual-monitoring/ |
| Схема БД (markdown) | https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/docs/DATABASE.md |
| DDL | https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/schema.sql |
| Roadmap | https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/ROADMAP.md |
| Contributing | https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/CONTRIBUTING.md |

### Как править

Исходники страниц лежат в основном репозитории в каталоге `wiki/`. После изменений &mdash; push в [wiki.git](https://github.com/svergio/Power-bi-report-visual-monitoring.wiki.git) или правка через UI Wiki с последующим переносом в `main`, если нужен единый источник правды.
