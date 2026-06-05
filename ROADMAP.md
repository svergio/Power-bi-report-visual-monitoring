# Roadmap

Planned work in coarse sprints. Scope may shift; nothing here is promised until shipped.

## Sprint 1 — Visual detection depth

- Richer visual detection (tuning, regions, thresholds as needed).
- User-behavior scripts (e.g. clicks, navigation) before capture.
- Behavior scripts for RLS / role-specific views.
- OCR-based validation where text must match expected content.

## Sprint 2 — Data and API probes

- REST API monitoring (health, contracts, latency).
- MySQL (or broader relational source) monitoring patterns.

## Sprint 3 — Operations and integrations

- Cluster-style operation (multi-node scheduling, shared queue).
- Kubernetes deployment manifests / Helm chart.
- Standalone deployment mode (minimal dependencies).
- Zabbix integration (metrics / triggers).
- Grafana integration (dashboards, alerts).
