# Phase 3 Performance Notes

Diese Phase fuehrt SQL-fruehe Filterung im Endpunkt `GET /api/shifts/schedule` ein, um unnoetige Python-Nachfilterung zu reduzieren.

## Aenderungen

- Freigabe-Filter fuer Nicht-Admins direkt in SQL (`EXISTS` auf `ShiftPlanApprovals`).
- Optionale SQL-Filter fuer grosse Ansichten:
  - `teamId`
  - `employeeId`
- Antwortmetrik fuer einfache Vorher/Nachher-Messung:
  - `metrics.processingMs`
  - `metrics.assignmentsReturned`

## Messvorschlag

1. Referenz-Requests fuer Woche/Monat/Jahr mit produktionsnahen Daten senden.
2. `metrics.processingMs` ueber mehrere Laeufe mitteln.
3. Vergleich mit identischen Parametern vor/nach Deployment dokumentieren.
