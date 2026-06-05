# Журнал изменений

Все значимые изменения проекта фиксируются в этом файле.

Формат основан на подходе Keep a Changelog.

## [Unreleased]

### Added

- `docs/agent/CLAUDE.md` and `docs/agent/CURSOR.md`: policy for AI-assisted documentation, Wiki sync, optional `Co-authored-by` on doc-only commits; README links.
- Wiki: expanded `Home.md`; Architecture / Operations / Limitations enriched (statuses, first-run vs prod, SEO/duplicate-text note); cross-links to agent policy.
- GitHub Pages `docs/index.html`: SEO metadata (canonical, hreflang, robots, keywords, Open Graph, Twitter card, JSON-LD `SoftwareApplication`); nav links to `docs/agent`.

### Added (RU)

- `docs/agent/CLAUDE.md` и `docs/agent/CURSOR.md`: политика правок документации агентом, синк Wiki, опциональный `Co-authored-by` для doc-only коммитов; ссылки в README.
- Wiki: расширен `Home.md`; страницы Architecture / Operations / Limitations дополнены; ссылки на политику агента.
- GitHub Pages `docs/index.html`: SEO в `<head>`; навигация на `docs/agent`.

### Changed

- Documentation: `docs/DATABASE.md`, `docs/index.html` (GitHub Pages), `ROADMAP.md`, and `RELEASE_NOTES.md` are now **bilingual (EN/RU)**; README and CHANGELOG cross-links updated.

### Changed (RU)

- Документация: `docs/DATABASE.md`, `docs/index.html` (GitHub Pages), `ROADMAP.md`, `RELEASE_NOTES.md` — **двуязычные (EN/RU)**; обновлены перекрёстные ссылки в README и CHANGELOG.

### Removed

- Устаревшие вспомогательные скрипты (`check_stress_test.sh`, `setup.sh`) и дубликаты шаблона окружения (`config.example.env`, `config_example.env`); единственный шаблон — `.env.example`.

## [0.2.0] - 2026-06-05

### Added

- GitHub Pages static site in `docs/` (`index.html`) with bilingual **EN/RU** rationale for visual monitoring; GitHub Actions workflow `pages.yml` to deploy the `docs/` folder.
- `docs/DATABASE.md` (**EN/RU**) describing tables, views, and `cleanup_old_checks`.
- `ROADMAP.md` (**EN/RU**) with sprint-level plans.

### Added (RU)

- Статический сайт GitHub Pages в `docs/` (`index.html`) с двуязычным текстом **EN/RU**; workflow `pages.yml` для публикации каталога `docs/`.
- `docs/DATABASE.md` (**EN/RU**) с описанием таблиц, представлений и `cleanup_old_checks`.
- `ROADMAP.md` (**EN/RU**) с планом по спринтам.

### Changed

- `README.md`: English lead section (SEO, links to Pages and schema docs) plus full Russian documentation, including a database overview and a CLI table in Russian.
- `schema.sql`: comments and `COMMENT ON` translated to English and aligned with application behavior.
- Python: removed redundant package/class docstrings; CLI `--help` text in English; scheduler worker hint in English.

### Changed (RU)

- `README.md`: английский блок (SEO, ссылки на Pages и схему) и полная русская документация, включая обзор БД и таблицу CLI.
- `schema.sql`: комментарии и `COMMENT ON` на английском, согласованы с кодом.
- Python: убраны лишние docstrings пакетов/классов; тексты `argparse` на английском; подсказка планировщика на английском.

## [0.1.0] - 2026-05-14

### Added

- Открытая упаковка проекта (`setup.py`, `setup.cfg`, `MANIFEST.in`)
- Конфигурация из окружения: `.env.example`
- Публичные примеры `reports.json` и `example_reports.json`
- CI: линтер, тесты, проверка типов, security scan
- Начальные тесты конфигурации и загрузки отчётов
- Документация для участников и метаданные репозитория

### Changed

- Убраны захардкоженные значения инфраструктуры и учётные данные
- Скрипты монитора и инициализации БД переведены на настройки из окружения
- Обновлён README: быстрый старт, архитектура, требования, устранение неполадок
