# Roadmap / Дорожная карта

Planned work in coarse sprints. Scope may shift; nothing here is promised until shipped.

Планируемая работа крупными спринтами. Объём может меняться; до релиза ничего из списка не является обязательством.

---

## Sprint 1 — Visual detection depth / Спринт 1 — глубина визуальной детекции

**EN**

- Richer visual detection (tuning, regions, thresholds as needed).
- User-behavior scripts (e.g. clicks, navigation) before capture.
- Behavior scripts for RLS / role-specific views.
- OCR-based validation where text must match expected content.

**RU**

- Расширение визуальной детекции (настройка, области, пороги по необходимости).
- Сценарии поведения пользователя (клики, навигация) перед снимком.
- Сценарии для RLS / представлений под роль.
- OCR-валидация, где текст должен совпадать с эталоном.

---

## Sprint 2 — Data and API probes / Спринт 2 — данные и API

**EN**

- REST API monitoring (health, contracts, latency).
- MySQL (or broader relational source) monitoring patterns.

**RU**

- Мониторинг REST API (здоровье, контракты, задержки).
- Паттерны мониторинга MySQL (или других реляционных источников).

---

## Sprint 3 — Operations and integrations / Спринт 3 — эксплуатация и интеграции

**EN**

- Cluster-style operation (multi-node scheduling, shared queue).
- Kubernetes deployment manifests / Helm chart.
- Standalone deployment mode (minimal dependencies).
- Zabbix integration (metrics / triggers).
- Grafana integration (dashboards, alerts).

**RU**

- Работа в кластере (мультиузловой планировщик, общая очередь).
- Манифесты Kubernetes / Helm chart.
- Режим standalone (минимальные зависимости).
- Интеграция с Zabbix (метрики / триггеры).
- Интеграция с Grafana (дашборды, алерты).
