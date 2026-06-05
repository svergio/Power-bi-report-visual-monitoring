This **Wiki** is the Markdown companion to the repository and [GitHub Pages](https://svergio.github.io/Power-bi-report-visual-monitoring/). Install flags, environment variables, and day-to-day commands stay in the [README](https://github.com/svergio/Power-bi-report-visual-monitoring#readme); here we keep **architecture**, **operations**, and **limitations** in a form that is easy to edit in the GitHub Wiki UI or in `main` under [`wiki/`](https://github.com/svergio/Power-bi-report-visual-monitoring/tree/main/wiki).

Maintainer policy for AI-assisted doc edits (including when Cursor may appear as co-author on doc-only commits): [docs/agent/CURSOR.md](https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/docs/agent/CURSOR.md) in the main repository.

---

## English

### What this project is

**Power BI Report Visual Monitoring** is an open-source tool that renders published Power BI reports in a headless browser, captures screenshots, compares them to baselines using a quadtree / MSE pipeline plus perceptual hashing, stores history in PostgreSQL, and optionally keeps gzip-compressed XOR deltas for forensics. It targets teams that need a **repeatable visual contract** on dashboards without rewriting every KPI as warehouse SQL.

### Who it is for

Data platform and BI engineers who already run refresh checks and warehouse tests, but still see **silent regressions in the report layer** (layout, conditional formatting, filter interactions, or measures that return plausible but wrong numbers while looking fine at a glance). Operations teams that want an **append-only audit trail** tied to rendered pixels, not only gateway logs.

### How this Wiki is organized

Long narrative and SEO-oriented article (single HTML, EN + RU): [GitHub Pages](https://svergio.github.io/Power-bi-report-visual-monitoring/). This Wiki splits the same themes into **linked pages** so you can deep-link from issues and runbooks without scrolling a single megadoc.

### Wiki table of contents

| Page | Topics |
|------|--------|
| [Architecture and pipeline](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki/Architecture-and-pipeline) | Data flow, `Data/` layout, DDD layers, DB vs files, check statuses, glossary |
| [Operations and tuning](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki/Operations-and-tuning) | CLI bootstrap, Docker, env keys, diff tuning, incidents, first run vs production |
| [Limitations and comparisons](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki/Limitations-and-comparisons) | vs Usage Metrics / Performance Analyzer, when SQL wins, RLS, cost and PII |

### Quick links

| Resource | URL |
|----------|-----|
| README | https://github.com/svergio/Power-bi-report-visual-monitoring#readme |
| GitHub Pages (long EN/RU article) | https://svergio.github.io/Power-bi-report-visual-monitoring/ |
| Database schema (markdown) | https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/docs/DATABASE.md |
| DDL | https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/schema.sql |
| Roadmap | https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/ROADMAP.md |
| Contributing | https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/CONTRIBUTING.md |
| Agent doc policy | https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/docs/agent/CURSOR.md |

### Edit and sync workflow

1. Change files under `wiki/` on branch `main` (pull request) or edit directly in the GitHub Wiki UI. If you edit only in the Wiki UI, consider copying changes back to `main` so history stays in git.
2. To publish Wiki from this repo: clone `https://github.com/svergio/Power-bi-report-visual-monitoring.wiki.git` into a temporary directory.
3. Copy all `*.md` from `wiki/` in the main checkout into the **root** of the wiki clone (overwrite `Home.md`, `_Sidebar.md`, etc.).
4. Run `git status`, `git add -A`, `git commit -m "..."`, `git push` inside the wiki clone.
5. GitHub Pages updates automatically when `docs/` (including `index.html`) changes on the default branch via the existing workflow.

---

## Русский

### О чём проект

**Power BI Report Visual Monitoring** &mdash; открытый инструмент: headless-браузер рендерит опубликованные отчёты Power BI, делает снимки, сравнивает с baseline (quadtree / MSE + перцептивный хеш), пишет историю в PostgreSQL и при необходимости хранит gzip-сжатые XOR-дельты. Цель &mdash; **воспроизводимый визуальный контракт** по дашбордам без переписывания каждого KPI как SQL на витрине.

### Кому это нужно

Инженерам данных и BI, у которых уже есть проверки обновления и тесты на витрине, но остаются **тихие регрессы в слое отчёта** (вёрстка, условное форматирование, фильтры, меры с правдоподобным, но неверным результатом). Командам эксплуатации, которым нужен **журнал попыток** с привязкой к отрисованному растру, а не только лог шлюза.

### Как устроена эта Wiki

Длинная статья с упором на смысл и поиск (один HTML, EN + RU): [GitHub Pages](https://svergio.github.io/Power-bi-report-visual-monitoring/). Вики разбивает те же темы на **страницы со ссылками**, чтобы из тикетов и ранбуков вести на конкретный раздел без бесконечного скролла.

### Оглавление вики

| Страница | Темы |
|----------|------|
| [Architecture and pipeline](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki/Architecture-and-pipeline) | Поток данных, каталог `Data/`, слои DDD, БД и файлы, статусы, глоссарий |
| [Operations and tuning](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki/Operations-and-tuning) | CLI, Docker, переменные окружения, настройка diff, инциденты, первый запуск и прод |
| [Limitations and comparisons](https://github.com/svergio/Power-bi-report-visual-monitoring/wiki/Limitations-and-comparisons) | Сравнение с Usage Metrics / Performance Analyzer, когда нужен SQL, RLS, стоимость и PII |

### Быстрые ссылки

| Ресурс | URL |
|--------|-----|
| README | https://github.com/svergio/Power-bi-report-visual-monitoring#readme |
| GitHub Pages (длинная статья EN/RU) | https://svergio.github.io/Power-bi-report-visual-monitoring/ |
| Схема БД (markdown) | https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/docs/DATABASE.md |
| DDL | https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/schema.sql |
| Roadmap | https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/ROADMAP.md |
| Contributing | https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/CONTRIBUTING.md |
| Политика правок агентом | https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/docs/agent/CURSOR.md |

### Как править и синхронизировать

1. Правки в `wiki/` в основном репозитории (ветка `main`, PR) или через UI Wiki на GitHub. Если правите только в UI, имеет смысл перенести текст в `main`, чтобы оставался единый источник правды.
2. Публикация Wiki из репозитория: клон `https://github.com/svergio/Power-bi-report-visual-monitoring.wiki.git` во временный каталог.
3. Скопировать все `*.md` из каталога `wiki/` основного репозитория в **корень** клона вики (перезапись `Home.md`, `_Sidebar.md` и остальных страниц).
4. В каталоге вики: `git status`, `git add -A`, `git commit`, `git push`.
5. GitHub Pages обновляется при изменении `docs/` на дефолтной ветке согласно workflow в репозитории.

Подробнее для ассистентов Cursor: [docs/agent/CURSOR.md](https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/docs/agent/CURSOR.md).
