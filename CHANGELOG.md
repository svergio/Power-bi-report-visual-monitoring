# Журнал изменений

Все значимые изменения проекта фиксируются в этом файле.

Формат основан на подходе Keep a Changelog.

## [Unreleased]

### Removed

- Устаревшие вспомогательные скрипты (`check_stress_test.sh`, `setup.sh`) и дубликаты шаблона окружения (`config.example.env`, `config_example.env`); единственный шаблон — `.env.example`.

## [0.2.0] - 2026-06-05

### Added

- GitHub Pages static site in `docs/` (`index.html`) with SEO-oriented rationale for visual monitoring; GitHub Actions workflow `pages.yml` to deploy the `docs/` folder.
- `docs/DATABASE.md` (English) describing tables, views, and `cleanup_old_checks`.
- `ROADMAP.md` with sprint-level plans.

### Changed

- `README.md`: English lead section (SEO, links to Pages and schema docs) plus full Russian documentation, including a database overview and a CLI table in Russian.
- `schema.sql`: comments and `COMMENT ON` translated to English and aligned with application behavior.
- Python: removed redundant package/class docstrings; CLI `--help` text in English; scheduler worker hint in English.

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
