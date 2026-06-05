# Limitations and comparisons

---

## English

### Versus Microsoft Usage Metrics

Usage Metrics answers **consumption**: which workspaces, reports, and pages users opened, how often, and from where. It is invaluable for adoption analytics. It does **not** assert that a given report page still *looks* like the approved reference after a model or theme change. Visual monitoring is orthogonal: fewer PII concerns if you run it from a service account on synthetic schedules, but you must still respect licensing and data residency policies.

### Versus Performance Analyzer

Performance Analyzer (typically in Power BI Desktop) exposes DAX and visual timings for an *interactive* author session. It helps optimize measure cost. The monitor here runs **unattended** in a headless browser against *published* URLs and stores **bitmap-level** outcomes. You might use Analyzer to fix a slow measure, then rely on visual monitoring to catch accidental layout regressions that Analyzer was never meant to detect.

### When visual-only monitoring is insufficient

- The business cares about **row-level correctness** (revenue totals, tax lines) regardless of pixel layout. Pair visual checks with dbt tests, reconciliation SQL, or semantic-layer assertions.
- The report intentionally shows **identical tiles** while a tooltip or drillthrough carries the bug. Pure full-page screenshots may miss deep interactions unless you extend the tool (roadmap: scripted clicks).
- **RLS** or dynamic role names cause different renders per user; your baseline must use credentials that match the population you care about.

### When warehouse-heavy SQL checks are preferable

- You already have a **single golden aggregate** that must match between systems (e.g., finance close). A SQL diff is direct and cheap if the query is indexed.
- You need **sub-second** alerting on facts streaming through Kafka; screenshot pipelines operate on human-scale latencies.

### Cost and risk notes

Headless Chrome consumes CPU/RAM; many wide dashboards at aggressive intervals can contend with other workloads on the same VM. Screenshots may contain sensitive figures &mdash; encrypt disks, restrict file permissions, and exclude `Data/` from backups that leave your trust zone.

### Search engines and duplicate text

The [GitHub Pages](https://svergio.github.io/Power-bi-report-visual-monitoring/) article and this Wiki intentionally **overlap in topic** but split depth: the HTML page is a single long EN/RU landing for people arriving from web search; the Wiki splits the same themes into linkable pages for operators editing in GitHub. Prefer **cross-linking** instead of pasting identical paragraphs everywhere, and keep factual claims aligned with `src/` so both surfaces stay trustworthy.

### Roadmap disclaimer

Features such as user gesture scripts, OCR text assertions, REST/MySQL probes, clustered scheduling, Zabbix, and Grafana integrations appear in [ROADMAP.md](https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/ROADMAP.md) as **future** direction. This page describes the **shipped** visual detection scope only.

---

## Русский

### Против Usage Metrics

Usage Metrics отвечает на вопрос **потребления**: какие рабочие области, отчёты и страницы открывали, как часто, откуда. Это аналитика внедрения. Он **не** утверждает, что страница отчёта *выглядит* как утверждённый эталон после смены модели или темы. Визуальный мониторинг ортогонален: при сервисной учётке и синтетическом расписании можно снизить PII по сравнению с логами пользователей, но лицензирование и резидентность данных всё равно нужно соблюдать.

### Против Performance Analyzer

Performance Analyzer (обычно в Desktop) показывает тайминги DAX и визуалов в **интерактивной** сессии автора. Это оптимизация мер. Наш монитор крутится **без участия человека** в headless-браузере по **опубликованным** URL и сохраняет **растровый** итог. Analyzer помогает ускорить меру; визуальный монитор ловит, например, регресс вёрстки, для которой Analyzer не предназначен.

### Когда одного визуала мало

- Бизнесу важна **корректность на уровне строк** (выручка, налоги) независимо от пикселей. Добавьте dbt-тесты, сверочный SQL или проверки семантического слоя.
- Отчёт **нарочно** выглядит так же, а баг в тултипе или drillthrough &mdash; полноэкранный снимок может не увидеть глубину (roadmap: сценарии кликов).
- **RLS** и динамические роли дают разный рендер; baseline снимайте под теми правами, которые репрезентативны.

### Когда выгоднее тяжёлый SQL

- Есть **один золотой агрегат**, который должен совпасть между системами; запрос индексирован и дёшев.
- Нужен **субсекундный** сигнал по потоку фактов; пайплайн скриншотов живёт на человеческих масштабах задержки.

### Риски и стоимость

Headless Chrome жрёт CPU/RAM; много широких дашбордов с агрессивным интервалом конкурируют с другими задачами на ВМ. На снимках могут быть чувствительные цифры &mdash; шифруйте диск, ограничьте права на `Data/`, не включайте этот каталог в бэкапы вне зоны доверия.

### Поисковики и дублирование текста

[GitHub Pages](https://svergio.github.io/Power-bi-report-visual-monitoring/) и эта Wiki **пересекаются по темам**, но по ролям: HTML &mdash; один длинный лендинг EN/RU для входа из поиска; Wiki &mdash; разбиение на страницы со ссылками для эксплуатации в GitHub. Лучше **перекрёстные ссылки**, чем копипаста одних и тех же абзацев; формулировки должны совпадать с фактами из `src/`, чтобы обе поверхности оставались согласованными.

### Про roadmap

Скрипты жестов, OCR, REST/MySQL, кластер, Zabbix, Grafana &mdash; в [ROADMAP.md](https://github.com/svergio/Power-bi-report-visual-monitoring/blob/main/ROADMAP.md) как **будущее**. Здесь описан только **текущий** объём визуальной детекции.
