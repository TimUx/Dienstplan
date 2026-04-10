# Bug-Fix-Prompts & Fehlerprotokoll

**Dokument-Typ:** Zentrales Fehler- und Lösungsregister  
**Letzte Aktualisierung:** April 2026  
**Quellen:** `tests/integration/test_solver.py`, `tests/integration/test_solver_2026.py`

Dieses Dokument sammelt alle dokumentierten Fehler, Fehlermuster und die dazugehörigen Fix-Suggestion-Prompts aus den Integrationstests des Schichtplanungs-Solvers. Jeder Eintrag enthält:

- **Fehler-ID** – eindeutige Referenz
- **Szenario** – kurze Beschreibung des auslösenden Testszenarios
- **Fehlerprotokoll** – was passiert, wenn der Fehler auftritt
- **Betroffene Komponente** – Funktion / Modul im Quellcode
- **Fix-Suggestion-Prompt** – fertiger Prompt für den Entwickler
- **Testquelle** – welche Testfunktion den Fehler abdeckt

---

## Inhaltsverzeichnis

1. [FS-001 – Strukturelle Unterbesetzung (2 Mitarbeiter)](#fs-001--strukturelle-unterbesetzung-2-mitarbeiter)
2. [FS-002 – Alle Mitarbeiter eine ganze Woche abwesend](#fs-002--alle-mitarbeiter-eine-ganze-woche-abwesend)
3. [FS-003 – Ruhezeit über Monatsgrenze (S→F, Jan/Feb 2025)](#fs-003--ruhezeit-über-monatsgrenze-sf-janfeb-2025)
4. [FS-004 – Doppelte Abwesenheits-IDs mit Überlappung](#fs-004--doppelte-abwesenheits-ids-mit-überlappung)
5. [FS-005 – Einzel-Tag-Planungszeitraum](#fs-005--einzel-tag-planungszeitraum)
6. [FS-006 – Alle Mitarbeiter ohne Teamzuordnung](#fs-006--alle-mitarbeiter-ohne-teamzuordnung)
7. [FS-007 – Extremes Zeitlimit (1 Sekunde)](#fs-007--extremes-zeitlimit-1-sekunde)
8. [FS-2026-01 – Reduzierte Besetzung Januar 2026 (10 Mitarbeiter)](#fs-2026-01--reduzierte-besetzung-januar-2026-10-mitarbeiter)
9. [FS-2026-02 – Alle Mitarbeiter volle Woche abwesend (Januar 2026)](#fs-2026-02--alle-mitarbeiter-volle-woche-abwesend-januar-2026)
10. [FS-2026-03 – S→F Ruhezeit über Jan/Feb-2026-Grenze](#fs-2026-03--sf-ruhezeit-über-janfeb-2026-grenze)
11. [FS-2026-04 – Starke Unterbesetzung Februar 2026 (6 Mitarbeiter)](#fs-2026-04--starke-unterbesetzung-februar-2026-6-mitarbeiter)
12. [FS-2026-05 – N→F Ruhezeit über Feb/März-2026-Grenze](#fs-2026-05--nf-ruhezeit-über-febmärz-2026-grenze)
13. [FS-2026-06 – Krankmeldungswelle März 2026 (8 gleichzeitige AU)](#fs-2026-06--krankmeldungswelle-märz-2026-8-gleichzeitige-au)
14. [FS-2026-07 – Minimale Besetzung März 2026 (5 Mitarbeiter)](#fs-2026-07--minimale-besetzung-märz-2026-5-mitarbeiter)

---

## FS-001 – Strukturelle Unterbesetzung (2 Mitarbeiter)

| Feld | Wert |
|------|------|
| **Fehler-ID** | FS-001 |
| **Testdatei** | `tests/integration/test_solver.py` |
| **Testfunktion** | `test_solver_structurally_understaffed` |
| **Betroffene Komponente** | `solver.py` → `add_staffing_constraints()`, Fallback-Kaskade |
| **Status** | Erwartet: `FALLBACK_L1`, `FALLBACK_L2` oder `EMERGENCY` |

### Fehlerprotokoll

Mit nur 2 Mitarbeitern und `min_staff_weekday=3` pro Schicht (3 Schichten × 3 = 9 Stellen/Tag) kann die Mindestbesetzung strukturell nicht erreicht werden. Der Solver darf nicht abstürzen oder `None` zurückgeben – er muss graceful in einen Fallback-Modus wechseln.

### Fix-Suggestion-Prompt

> Mindestens so viele Mitarbeiter konfigurieren wie `min_staff_weekday` + `min_staff_weekend` über alle Schichttypen gefordert werden. In `add_staffing_constraints()` prüfen, ob bei struktureller Unterbesetzung korrekt von Hard- auf Soft-Constraints gewechselt wird. Der Test erwartet einen der Statuses `FALLBACK_L1`, `FALLBACK_L2` oder `EMERGENCY` – falls der Solver stattdessen `OPTIMAL` oder `FEASIBLE` zurückgibt, ist die Fallback-Erkennung defekt.

---

## FS-002 – Alle Mitarbeiter eine ganze Woche abwesend

| Feld | Wert |
|------|------|
| **Fehler-ID** | FS-002 |
| **Testdatei** | `tests/integration/test_solver.py` |
| **Testfunktion** | `test_solver_all_employees_absent_entire_week` |
| **Betroffene Komponente** | `solver.py` → `_build_complete_schedule()` / `complete_schedule`-Logik |
| **Planungszeitraum** | Januar 2025, KW3: 13.01.–19.01.2025 |

### Fehlerprotokoll

Wenn alle 17 Mitarbeiter für eine volle Woche im Urlaub sind, darf `complete_schedule` für keinen Mitarbeiter einen Schicht-Code zurückgeben – stattdessen muss für jeden Mitarbeiter an jedem Abwesenheitstag der Wert `"ABSENT"` stehen. Falls ein Schicht-Code erscheint, wertet `_build_complete_schedule()` Abwesenheiten nicht mit höchster Priorität aus.

### Fix-Suggestion-Prompt

> Prüfe vor dem Solve, ob in einer Woche weniger als `min_staff_weekday` verfügbare Mitarbeiter existieren, und warne den Dispatcher vorab. In `_build_complete_schedule()` sicherstellen, dass Abwesenheits-Einträge vor Schicht-Zuweisungen geprüft werden:
>
> ```python
> if (emp_id, d) in absence_set:
>     code = "ABSENT"
> ```

---

## FS-003 – Ruhezeit über Monatsgrenze (S→F, Jan/Feb 2025)

| Feld | Wert |
|------|------|
| **Fehler-ID** | FS-003 |
| **Testdatei** | `tests/integration/test_solver.py` |
| **Testfunktion** | `test_solver_rest_time_cross_month_boundary` |
| **Betroffene Komponente** | `model.py` → `add_rest_time_constraints()`, `previous_employee_shifts` |
| **Betroffene Schichtfolge** | S (31.01.) → F (01.02.) = nur 8 h Ruhezeit, Minimum 11 h |

### Fehlerprotokoll

4 Mitarbeiter hatten am letzten Januar-Tag einen S-Dienst (Ende 21:45 Uhr). Am ersten Februar-Tag dürfen sie keinen F-Dienst erhalten (Beginn 05:45 Uhr = nur 8 h Pause). Die Verletzung tritt auf, wenn `previous_employee_shifts` nicht korrekt in `add_rest_time_constraints()` eingebunden wird.

### Fix-Suggestion-Prompt

> Übergib dem Solver stets `previous_employee_shifts` mit dem vollständigen letzten Monat, damit Ruhezeit-Grenzen über Monatsgrenzen korrekt eingehalten werden. Prüfe in `add_rest_time_constraints()`, ob das Key-Format `(employee_id, date)` → `shift_code` konsistent mit dem internen Constraint-Code ist. Falls der Test fehlschlägt, im Code nach `previous_employee_shifts` suchen und sicherstellen, dass S-Dienste vom Vortag als Constraint für den Folgetag registriert werden.

---

## FS-004 – Doppelte Abwesenheits-IDs mit Überlappung

| Feld | Wert |
|------|------|
| **Fehler-ID** | FS-004 |
| **Testdatei** | `tests/integration/test_solver.py` |
| **Testfunktion** | `test_solver_duplicate_absence_ids` |
| **Betroffene Komponente** | `model.py` → Preprocessing vor `ShiftPlanningModel`-Konstruktion |

### Fehlerprotokoll

Zwei `Absence`-Objekte teilen dieselbe `id=999` für denselben Mitarbeiter mit überlappenden Zeiträumen (06.–10.01. und 08.–14.01.). Der Solver darf nicht abstürzen. Doppelte Constraints im CP-SAT-Modell können zu inkonsistenten Einschränkungen oder einem INFEASIBLE-Status führen.

### Fix-Suggestion-Prompt

> Im Preprocessing (vor `ShiftPlanningModel`-Konstruktion) Abwesenheits-Duplikate per `{employee_id, date}`-Set deduplizieren, um doppelte Constraint-Registrierungen im CP-SAT-Modell zu vermeiden. Beispiel:
>
> ```python
> seen = set()
> deduplicated = []
> for absence in absences:
>     for day_offset in range((absence.end_date - absence.start_date).days + 1):
>         key = (absence.employee_id, absence.start_date + timedelta(days=day_offset))
>         if key not in seen:
>             seen.add(key)
>             deduplicated.append(absence)
>             break
> ```

---

## FS-005 – Einzel-Tag-Planungszeitraum

| Feld | Wert |
|------|------|
| **Fehler-ID** | FS-005 |
| **Testdatei** | `tests/integration/test_solver.py` |
| **Testfunktion** | `test_solver_single_day_planning_period` |
| **Betroffene Komponente** | `model.py` → Wochenerweiterungs-Logik in `ShiftPlanningModel` |
| **Testdatum** | Mittwoch, 15.01.2025 |

### Fehlerprotokoll

Bei einem Planungszeitraum von genau 1 Tag kann die Wochenerweiterungs-Logik in `ShiftPlanningModel` einen negativen Datumsbereich erzeugen und abstürzen. `complete_schedule` muss für jeden Mitarbeiter genau diesen einen Tag enthalten.

### Fix-Suggestion-Prompt

> Sicherstellen, dass die Wochenerweiterungs-Logik in `ShiftPlanningModel` auch für 0- oder 1-Tages-Spannen korrekt funktioniert (kein negativer Datumsbereich). Prüfe, ob `end_date < start_date` nach der Erweiterung möglich ist, und füge eine Guard-Bedingung ein:
>
> ```python
> extended_start = min(start_date, extended_start)
> extended_end = max(end_date, extended_end)
> ```

---

## FS-006 – Alle Mitarbeiter ohne Teamzuordnung

| Feld | Wert |
|------|------|
| **Fehler-ID** | FS-006 |
| **Testdatei** | `tests/integration/test_solver.py` |
| **Testfunktion** | `test_solver_all_employees_without_team` |
| **Betroffene Komponente** | `solver.py` → Springer-Fallback, Team-Constraint-Generierung |

### Fehlerprotokoll

Alle Mitarbeiter haben `team_id=None`, die Teams-Liste ist leer. Der Solver muss ein gültiges Ergebnis zurückgeben (ggf. leer). Ein Absturz oder `None`-Rückgabe zeigt an, dass Team-Constraints ohne Guard aufgerufen werden.

### Fix-Suggestion-Prompt

> Mindestens 1 Fallback-Team oder generische Springer-Schicht-Zuweisung für teamlose Mitarbeiter implementieren, um die Planungsqualität zu verbessern. In der Constraint-Generierung prüfen, ob `team.employees` leer ist, bevor Team-spezifische Constraints hinzugefügt werden.

---

## FS-007 – Extremes Zeitlimit (1 Sekunde)

| Feld | Wert |
|------|------|
| **Fehler-ID** | FS-007 |
| **Testdatei** | `tests/integration/test_solver.py` |
| **Testfunktion** | `test_solver_time_limit_exhaustion` |
| **Betroffene Komponente** | `solver.py` → `solve_shift_planning()`, Emergency-Greedy-Fallback |

### Fehlerprotokoll

Bei `time_limit_seconds=1` auf einem Standard-17-Mitarbeiter-Monatsdatensatz muss der Solver immer ein gültiges 3-Tupel zurückgeben (kein `None`, kein Exception). Der Emergency-Greedy-Fallback muss innerhalb des Budget-Restes ausgeführt werden.

### Fix-Suggestion-Prompt

> Für Produktionsanfragen immer mindestens 60 Sekunden Budget einplanen. Bei `time_limit_seconds < 30` eine Warnung an den Dispatcher loggen. Prüfen, ob die Fallback-Kaskade in `solve_shift_planning()` auch dann greift, wenn alle OR-Tools-Stages das Budget überschreiten:
>
> ```
> Stage 1 (OPTIMAL) → TIMEOUT
> Stage 2 (FALLBACK_L1) → TIMEOUT
> Stage 3 (FALLBACK_L2) → TIMEOUT
> Emergency Greedy → muss immer erfolgreich sein
> ```

---

## FS-2026-01 – Reduzierte Besetzung Januar 2026 (10 Mitarbeiter)

| Feld | Wert |
|------|------|
| **Fehler-ID** | FS-2026-01 |
| **Testdatei** | `tests/integration/test_solver_2026.py` |
| **Testfunktion** | `test_january_2026_reduced_staff_10_employees`, `test_january_2026_many_vacations` |
| **Betroffene Komponente** | `solver.py` → `add_staffing_constraints()`, Fallback-Kaskade |
| **Planungszeitraum** | Januar 2026, 10 Mitarbeiter in 2 Teams |

### Fehlerprotokoll

10 Mitarbeiter in 2 Teams können `min_staff_weekday=3` pro Schicht (3 Schichten × 3 = 9 Stellen/Tag) kaum erfüllen. Der Solver muss graceful in `FALLBACK_L1` oder `FALLBACK_L2` degradieren, anstatt zu crashen.

Zusätzlich: 6 gleichzeitige Urlaubs-Abwesenheiten (KW3: 12.–18.01.2026) testen, ob der Solver auf FALLBACK degradiert und keine Schichten in Abwesenheitstagen plant.

### Fix-Suggestion-Prompt

> 10 Mitarbeiter in 2 Teams können `min_staff_weekday=3` pro Schicht (3 Schichten × 3 = 9/Tag) kaum erfüllen. Der Solver muss graceful in `FALLBACK_L1` oder `FALLBACK_L2` degradieren. Prüfe, ob `add_staffing_constraints()` bei Unterbesetzung korrekt auf die Soft-Constraint-Schiene wechselt. Erhöhe notfalls `MIN_STAFFING_RELAXED_PENALTY_WEIGHT`, damit der Report die Unterbesetzung deutlich kennzeichnet.

---

## FS-2026-02 – Alle Mitarbeiter volle Woche abwesend (Januar 2026)

| Feld | Wert |
|------|------|
| **Fehler-ID** | FS-2026-02 |
| **Testdatei** | `tests/integration/test_solver_2026.py` |
| **Testfunktion** | `test_january_2026_all_absent_full_week` |
| **Betroffene Komponente** | `solver.py` → `_build_complete_schedule()` / `complete_schedule`-Logik |
| **Planungszeitraum** | Januar 2026, KW3: 12.–18.01.2026, alle 17 Mitarbeiter abwesend |

### Fehlerprotokoll

`complete_schedule` MUSS für jeden Mitarbeiter an jedem Abwesenheitstag `"ABSENT"` zurückgeben. Erscheint stattdessen ein Schicht-Code, liegt der Bug in `_build_complete_schedule()` (oder der äquivalenten Logik in `solve_shift_planning`), die Abwesenheiten nicht vor Schicht-Einträgen auswertet.

### Fix-Suggestion-Prompt

> Wenn alle 17 Mitarbeiter in KW3 (2026-01-12 bis 2026-01-18) im Urlaub sind, muss `complete_schedule` für jeden dieser Tage ausschließlich `"ABSENT"` zurückgeben. Validiere, dass `_build_complete_schedule()` Abwesenheiten vor Schicht-Einträgen auswertet. Falls nicht, füge eine explizite Prüfung hinzu:
>
> ```python
> if (emp_id, d) in absence_set:
>     code = "ABSENT"
> ```

---

## FS-2026-03 – S→F Ruhezeit über Jan/Feb-2026-Grenze

| Feld | Wert |
|------|------|
| **Fehler-ID** | FS-2026-03 |
| **Testdatei** | `tests/integration/test_solver_2026.py` |
| **Testfunktion** | `test_february_2026_rest_time_across_january_boundary` |
| **Betroffene Komponente** | `model.py` → `add_rest_time_constraints()`, `previous_employee_shifts` |
| **Betroffene Schichtfolge** | S (31.01.2026) → F (01.02.2026) = nur 8 h Ruhezeit, Minimum 11 h |

### Fehlerprotokoll

Mitarbeiter, die am 2026-01-31 einen S-Dienst hatten, dürfen am 2026-02-01 KEINEN F-Dienst bekommen (nur 8 h Ruhezeit). Die Grenzüberschreitung wird über `ShiftPlanningModel.previous_employee_shifts` kodiert. Schlägt der Test fehl, wird dieses Dictionary in `add_rest_time_constraints()` nicht korrekt verarbeitet.

### Fix-Suggestion-Prompt

> Mitarbeiter, die am 2026-01-31 einen S-Dienst hatten, dürfen am 2026-02-01 KEINEN F-Dienst bekommen (nur 8 h Ruhezeit). Stelle sicher, dass `ShiftPlanningModel.previous_employee_shifts` korrekt in `add_rest_time_constraints()` verarbeitet wird. Falls der Test fehlschlägt, prüfe, ob das Key-Format `(employee_id, date(2026, 1, 31))` → `"S"` konsistent mit dem internen Constraint-Code ist.

---

## FS-2026-04 – Starke Unterbesetzung Februar 2026 (6 Mitarbeiter)

| Feld | Wert |
|------|------|
| **Fehler-ID** | FS-2026-04 |
| **Testdatei** | `tests/integration/test_solver_2026.py` |
| **Testfunktion** | `test_february_2026_understaffed_6_employees` |
| **Betroffene Komponente** | `solver.py` → `solve_shift_planning()`, EMERGENCY-Greedy-Fallback |
| **Planungszeitraum** | Februar 2026, 6 Mitarbeiter in 2 Teams |

### Fehlerprotokoll

6 Mitarbeiter können 3 Schichten × `min_staff_weekday=3` (= 9 Stellen/Tag) nicht erfüllen. Das Ergebnis darf **nicht** `None` sein. Der Solver muss zu `FALLBACK` oder `EMERGENCY` degradieren und dennoch ein gültiges 3-Tupel zurückgeben.

### Fix-Suggestion-Prompt

> Nur 6 Mitarbeiter in 2 Teams für Februar 2026. Das Ergebnis darf NICHT `None` sein. Validiere den EMERGENCY-Fallback in `solve_shift_planning()` und dass `PlanningReport.status` einen der bekannten Werte enthält. Teste, ob `solve_shift_planning()` im EMERGENCY-Pfad immer einen nicht-leeren `PlanningReport` zurückgibt und der Greedy-Fallback zumindest alle Tage mit einem `"OFF"`-Eintrag füllt.

---

## FS-2026-05 – N→F Ruhezeit über Feb/März-2026-Grenze

| Feld | Wert |
|------|------|
| **Fehler-ID** | FS-2026-05 |
| **Testdatei** | `tests/integration/test_solver_2026.py` |
| **Testfunktion** | `test_march_2026_rest_time_across_february_boundary` |
| **Betroffene Komponente** | `model.py` → `add_rest_time_constraints()`, `previous_employee_shifts` |
| **Betroffene Schichtfolge** | N (28.02.2026) → F (01.03.2026) = 0 h Ruhezeit (N endet 05:45, F beginnt 05:45) |

### Fehlerprotokoll

N-Schicht endet um ~05:45 Uhr. F-Schicht beginnt um 05:45 Uhr. Ruhezeit = 0 h, Minimum 11 h. Die Grenzüberschreitung über die Feb/März-Grenze muss analog zu FS-2026-03 über `previous_employee_shifts` kodiert und in `add_rest_time_constraints()` ausgewertet werden.

### Fix-Suggestion-Prompt

> Mitarbeiter, die am 2026-02-28 einen N-Dienst hatten, dürfen am 2026-03-01 KEINEN F-Dienst erhalten (Ruhezeit < 11 h). Test wie FS-2026-03, jetzt über die Feb/März-Grenze. Überprüfe `add_rest_time_constraints()` auf korrekte Behandlung von N→F über die Feb/März-Grenze. Stelle sicher, dass das vorherige Schicht-Datum im Key-Format `(employee_id, date(2026, 2, 28))` korrekt gespeichert und abgerufen wird.

---

## FS-2026-06 – Krankmeldungswelle März 2026 (8 gleichzeitige AU)

| Feld | Wert |
|------|------|
| **Fehler-ID** | FS-2026-06 |
| **Testdatei** | `tests/integration/test_solver_2026.py` |
| **Testfunktion** | `test_march_2026_sick_leave_wave` |
| **Betroffene Komponente** | `solver.py` → `add_staffing_constraints()`, Fallback-Kaskade |
| **Planungszeitraum** | März 2026, 09.–20.03.2026, 8 von 17 Mitarbeitern krank (≈ 47 %) |

### Fehlerprotokoll

Mit 9 von 17 Mitarbeitern verfügbar muss der Solver dennoch einen gültigen Plan produzieren. Wenn er `None` zurückgibt oder einen Exception wirft, ist der Emergency-Fallback defekt. Meldet er `INFEASIBLE` ohne in den Greedy-Fallback zu wechseln, ist die Fallback-Kaskade unterbrochen.

### Fix-Suggestion-Prompt

> 8 gleichzeitige AU-Abwesenheiten (fast 50 % der Crew) ab 2026-03-09. Der Solver muss trotzdem eine gültige Liste zurückgeben. Prüfe, ob `add_staffing_constraints()` sicher auf FALLBACK degradiert, wenn die verfügbare Mannschaft die Mindestbesetzung nicht erreicht. Falls der Solver `INFEASIBLE` meldet ohne in den Greedy-Fallback zu wechseln, prüfe die Fallback-Kaskade in `solve_shift_planning()`.

---

## FS-2026-07 – Minimale Besetzung März 2026 (5 Mitarbeiter)

| Feld | Wert |
|------|------|
| **Fehler-ID** | FS-2026-07 |
| **Testdatei** | `tests/integration/test_solver_2026.py` |
| **Testfunktion** | `test_march_2026_minimal_staffing_edge_case` |
| **Betroffene Komponente** | `solver.py` → Fallback-Kaskade, Untergrenze der Crew-Größe |
| **Planungszeitraum** | März 2026, 5 Mitarbeiter in 2 Teams (31-Tage-Lauf) |

### Fehlerprotokoll

5 Mitarbeiter unterschreiten die Summe aller `min_staff_weekday`-Werte über alle Schichttypen (Standard = 9). Bei diesem Edge-Case wird immer ein FALLBACK-Status erwartet. Der Test validiert die Untergrenze der Crew-Größe für einen vollmonatlichen Planungslauf.

### Fix-Suggestion-Prompt

> Mindestens so viele Mitarbeiter konfigurieren wie die Summe aller `min_staff_weekday`-Werte über alle Schichttypen (= 9 Standard), um einen `OPTIMAL`- oder `FEASIBLE`-Status zu erreichen. Bei 5 Mitarbeitern wird immer ein `FALLBACK` erwartet. Prüfe, ob `add_staffing_constraints()` diese Untergrenze erkennt und korrekt auf Soft-Constraints wechselt.

---

## Zusammenfassung

| ID | Bereich | Hauptkomponente | Erwartetes Verhalten bei Fehler |
|----|---------|-----------------|--------------------------------|
| FS-001 | Unterbesetzung | `add_staffing_constraints()` | FALLBACK_L1/L2/EMERGENCY |
| FS-002 | Vollständige Abwesenheit | `_build_complete_schedule()` | `"ABSENT"` für alle Abwesenheitstage |
| FS-003 | Ruhezeit Monatsgrenze | `add_rest_time_constraints()` | Kein F nach S über Monatsgrenze |
| FS-004 | Doppelte Abwesenheits-IDs | Preprocessing | Kein Absturz, keine doppelten Constraints |
| FS-005 | 1-Tag-Planungszeitraum | Wochenerweiterungs-Logik | Gültige `complete_schedule` für 1 Tag |
| FS-006 | Kein Team | Springer-Fallback | Kein Absturz, gültiges Ergebnis |
| FS-007 | Zeitlimit 1 s | Emergency-Greedy-Fallback | Gültiges 3-Tupel, kein None |
| FS-2026-01 | Reduziert Jan 2026 | `add_staffing_constraints()` | FALLBACK, keine Abwesenheitsverletzung |
| FS-2026-02 | Alle abwesend Jan 2026 | `_build_complete_schedule()` | `"ABSENT"` für KW3 |
| FS-2026-03 | S→F Jan/Feb 2026 | `add_rest_time_constraints()` | Kein F nach S über Monatsgrenze |
| FS-2026-04 | Unterbesetzt Feb 2026 | Emergency-Greedy-Fallback | Kein None, gültiger Report |
| FS-2026-05 | N→F Feb/März 2026 | `add_rest_time_constraints()` | Kein F nach N über Monatsgrenze |
| FS-2026-06 | Krankmeldungswelle März 2026 | `add_staffing_constraints()` | Kein None, gültiger Plan |
| FS-2026-07 | 5 Mitarbeiter März 2026 | Fallback-Kaskade | FALLBACK-Status |

---

## Verwandte Dokumente

- [`docs/TESTDOKUMENTATION.md`](TESTDOKUMENTATION.md) – Vollständige Testdokumentation mit Screenshots und Ergebnissen
- [`docs/SHIFT_PLANNING_ALGORITHM.md`](SHIFT_PLANNING_ALGORITHM.md) – Algorithmische Details des Solvers
- [`tests/integration/test_solver.py`](../tests/integration/test_solver.py) – Integrationstests (2025)
- [`tests/integration/test_solver_2026.py`](../tests/integration/test_solver_2026.py) – Integrationstests (Jan–März 2026)
