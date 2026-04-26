# Cursor Umsetzungsplan (ausfuehrbar)

Dieser Plan ist so geschrieben, dass du ihn direkt in Cursor nutzen kannst:
- pro Phase ein klarer Scope
- pro Phase ein Copy/Paste-Prompt fuer den Agenten
- klare Abnahmekriterien
- risikoarme Reihenfolge (kein Big-Bang)

---

## 0) Arbeitsweise in Cursor

Empfohlener Ablauf je Phase:
1. Neuen Branch erstellen (`feature/<phase-name>`).
2. Prompt der Phase 1:1 in Cursor einfuegen.
3. Agent arbeiten lassen bis:
   - Code angepasst
   - Tests/Lints ausgefuehrt
   - PR vorbereitet
4. PR reviewen und mergen.
5. Naechste Phase starten.

---

## Phase 1 - Security Baseline (P1)

### Ziel
- Zugriffsschutz vereinheitlichen
- sensible Daten absichern
- Datenintegritaet sichern

### Cursor Prompt (Copy/Paste)
```text
Setze Phase 1 (Security Baseline) um.

Scope:
1) Erstelle eine Security-Matrix fuer alle API-Endpunkte (auth required, role required, public only if intentional).
2) Setze Default-Auth-Verhalten fuer API-Routen durch und mache Public-Endpunkte explizit.
3) Stelle sicher, dass bei jeder SQLite-Connection Foreign Keys aktiv sind (PRAGMA foreign_keys=ON).
4) Haerte sensible Konfigurationen (insbesondere SMTP/Secrets) und entferne Klartext-Risiken so weit moeglich.
5) Fuehre targeted Tests aus und dokumentiere alle Aenderungen.

Wichtig:
- Keine funktionalen Regressionen.
- Minimal-invasive Aenderungen mit klaren Commits.
- Nach jeder groesseren Aenderung Tests/Lints laufen lassen.
- Am Ende: Branchname, Commit-Plan, durchgefuehrte Commands, PR-Text, Testhinweise liefern.
```

### Abnahmekriterien
- Keine unbeabsichtigt offenen sensitiven Endpunkte.
- FK-Enforcement aktiv (nicht nur bei DB-Init).
- Security-relevante Tests gruen.
- PR mit klarer Risikoanalyse vorhanden.

---

## Phase 2 - Frontend Foundation

### Ziel
- UI/UX konsistent
- wiederverwendbare Patterns
- weniger Wartungsaufwand

### Cursor Prompt (Copy/Paste)
```text
Setze Phase 2 (Frontend Foundation) um.

Scope:
1) Konsolidiere doppelte CSS-Regeln (Buttons/Badges/Tabs/Grids), ohne Layout-Regr.
2) Vereinheitliche Dialog- und Feedback-Flows im Frontend (kein Browser-Dialog-Mix in Kernflows).
3) Etabliere wiederverwendbare UI-Patterns fuer ActionBar/FormSection/EmptyState.
4) Sorge fuer saubere mobile Darstellung in den datenintensiven Verwaltungsseiten.
5) Fuehre UI-nahe Regressionstests/Smoke-Checks durch.

Wichtig:
- Keine unnoetigen visuellen Umbauten ausserhalb Scope.
- Bestehende Funktionen muessen erhalten bleiben.
- Aenderungen in logisch getrennte Commits splitten.
- Am Ende PR mit Vorher/Nachher-Beschreibung liefern.
```

### Abnahmekriterien
- Sichtbar konsistentere Verwaltungsseiten.
- Keine native `alert/confirm/prompt`-Reste in Kernmodulen.
- Keine Lint-Fehler in geaenderten Frontend-Dateien.

---

## Phase 3 - Schedule Performance

### Ziel
- schnelleres Laden/Interagieren in Woche/Monat/Jahr
- weniger Voll-Reloads

### Cursor Prompt (Copy/Paste)
```text
Setze Phase 3 (Schedule Performance) um.

Scope:
1) Reduziere unnoetige Full-Reloads im Schedule-Frontend (inkrementelle UI-Updates, wo sicher moeglich).
2) Pruefe API-Seite: Filter/Pagination frueher in SQL statt spaet in Python.
3) Optimiere Datenaufbereitung fuer Ferien/Abwesenheiten in grossen Ansichten.
4) Fuehre messbare Vorher/Nachher-Vergleiche fuer Ladezeit/Interaktion durch (mind. einfache Metriken).
5) Sicherstellen, dass Planungslogik unveraendert korrekt bleibt.

Wichtig:
- Kein Funktionsverlust im Planungsworkflow.
- API-Kontrakte nur aendern, wenn unbedingt noetig und dokumentiert.
- Tests fuer Schichten/Planung unbedingt laufen lassen.
```

### Abnahmekriterien
- Spuerbar weniger UI-Lags im Dienstplan.
- Gleichbleibende fachliche Ergebnisse.
- Dokumentierte Messwerte (vorher/nachher).

---

## Phase 4 - Backend Service Layer & Maintainability

### Ziel
- klare Trennung von Routing und Business-Logik
- besser testbar und erweiterbar

### Cursor Prompt (Copy/Paste)
```text
Setze Phase 4 (Backend Maintainability) um.

Scope:
1) Extrahiere zentrale Business-Logik aus Routern in Services (thin routers).
2) Vereinheitliche Error-Handling (einheitliches Fehlerformat, keine unkontrollierten str(e)-Leaks).
3) Vereinheitliche Datenzugriffsmuster (Repository-Strategie klar und konsistent).
4) Verbessere Logging-Struktur fuer Betrieb und Fehleranalyse.
5) Bestehende API-Tests anpassen/erweitern.

Wichtig:
- Refactoring ohne fachliche Verhaltensaenderung.
- Kleine, reviewbare Commits.
- Keine "grossen Umbenennungswellen" ohne Mehrwert.
```

### Abnahmekriterien
- Router deutlich schlanker.
- Einheitliches Fehlerverhalten.
- Testabdeckung fuer refaktorierte Pfade vorhanden.

---

## Phase 5 - Ops, Monitoring, Skalierung

### Ziel
- produktiver Betrieb stabil
- Lastspitzen beherrschbar
- Skalierungsfaehigkeit vorbereiten

### Cursor Prompt (Copy/Paste)
```text
Setze Phase 5 (Ops/Monitoring) um.

Scope:
1) Definiere und implementiere Kernmetriken fuer API, DB, Solver-Jobs.
2) Verbessere Job-Lifecycle-Handling (Cleanup, Cancel-Verhalten, Ressourcenfreigabe).
3) Erstelle ein technisches Runbook fuer Lastspitzen/Fehlerfaelle.
4) Lege eine konkrete Entscheidungsvorlage fuer Queue/Worker-Entkopplung vor.
5) Dokumentiere Betriebs-KPIs und Alert-Schwellen.

Wichtig:
- Fokus auf Betriebsfaehigkeit und Diagnose.
- Keine unnötigen Architekturwechsel in dieser Phase.
```

### Abnahmekriterien
- Metriken und klare Betriebs-KPIs vorhanden.
- Job-Runtime stabiler und nachvollziehbarer.
- Runbook fuer Team nutzbar.

---

## Commit- und PR-Regeln (fuer jede Phase)

- Maximal 2-4 Commits pro Phase.
- Commit-Typen konsequent (`fix:`, `refactor:`, `ci:`, `docs:`).
- Jeder PR enthaelt:
  - Summary (Was/Warum)
  - Testplan
  - Risiken/Rollback

Beispiel-PR-Template:
```text
## Summary
- ...

## Test plan
- [x] ...
- [ ] ...

## Risks / rollback
- ...
```

---

## Empfehlung fuer den Start

Starte mit **Phase 1**, dann **Phase 3** (Performance) und parallel kleinere Teile von **Phase 2**.  
So minimierst du zuerst Produktionsrisiken und lieferst frueh sichtbaren Nutzen.

