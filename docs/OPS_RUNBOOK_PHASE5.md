# Ops Runbook (Phase 5)

## Kernmetriken

- `planning_jobs_started`
- `planning_jobs_success`
- `planning_jobs_error`
- `planning_jobs_cancelled`
- `planning_jobs_cleaned_up`
- `uptime_seconds`

Die Metriken sind ueber `GET /api/ops/metrics` (Admin) und im Health-Payload verfuegbar.

## KPI- und Alert-Schwellen

- **Planungsfehlerquote**: `planning_jobs_error / planning_jobs_started`
  - Warnung: > 5% in 30 Minuten
  - Kritisch: > 10% in 30 Minuten
- **Cancel-Quote**: `planning_jobs_cancelled / planning_jobs_started`
  - Warnung: > 20% in 30 Minuten (Hinweis auf UX- oder Laufzeitprobleme)
- **Job-Cleanup**: `planning_jobs_cleaned_up`
  - Warnung: 0 ueber > 48h bei aktiver Nutzung
- **Verfuegbarkeit**: `GET /api/health` Status
  - Kritisch: != `healthy`

## Incident-Ablauf bei Lastspitzen

1. `GET /api/health` pruefen (DB-Status, Laufzeit, Version).
2. `GET /api/ops/metrics` pruefen (Error-/Cancel-Quote, Job-Druck).
3. Bei steigender Fehlerquote:
   - aktive Planungsjobs per Status-Endpunkt beobachten
   - fehlerhafte Zeitfenster/Teams isolieren
4. Bei anhaltender Ueberlast:
   - Planungsanfragen zeitlich staffeln
   - nicht kritische Export-/Batch-Operationen pausieren
5. Nach Stabilisierung:
   - Ursachen dokumentieren
   - Schwellwerte oder Kapazitaetsplanung anpassen

## Rollback-Hinweis

Bei Problemen mit den neuen Metrikpunkten koennen die Phase-5-Commits gezielt reverted werden, ohne fachliche Planungslogik zu veraendern.
