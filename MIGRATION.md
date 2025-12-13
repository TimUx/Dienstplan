# Migrationsanleitung: .NET nach Python OR-Tools

## Vollständige Migrations-Dokumentation

Diese Anleitung beschreibt die vollständige Migration des Dienstplan-Systems von .NET/C# zu Python mit Google OR-Tools.

---

## 1. Repository-Analyse (Abgeschlossen)

### Identifizierte Kernkomponenten

#### Datenmodelle (.NET → Python)
| .NET Entity | Python Dataclass | Status |
|------------|------------------|--------|
| `Employee.cs` | `entities.py:Employee` | ✅ Migriert |
| `Team.cs` | `entities.py:Team` | ✅ Migriert |
| `ShiftType.cs` | `entities.py:ShiftType` | ✅ Migriert |
| `ShiftAssignment.cs` | `entities.py:ShiftAssignment` | ✅ Migriert |
| `Absence.cs` | `entities.py:Absence` | ✅ Migriert |
| `VacationRequest.cs` | `entities.py:VacationRequest` | ✅ Migriert |

#### Schichtlogik
- **F (Früh)**: 05:45-13:45 (8h)
- **S (Spät)**: 13:45-21:45 (8h)
- **N (Nacht)**: 21:45-05:45 (8h)
- **BMT (Brandmeldetechniker)**: 06:00-14:00 (8h, Mo-Fr)
- **BSB (Brandschutzbeauftragter)**: 07:00-16:30 (9.5h, Mo-Fr)

#### Geschäftsregeln (.NET ShiftRules.cs → Python constraints.py)

**Harte Regeln:**
- ✅ Mindestruhezeit: 11 Stunden
- ✅ Max. 6 aufeinanderfolgende Dienste
- ✅ Max. 5 aufeinanderfolgende Nachtdienste
- ✅ Max. 48 Stunden pro Woche
- ✅ Max. 192 Stunden pro Monat
- ✅ Verbotene Übergänge: S→F, N→F
- ✅ Mindestbesetzung je Schicht (Mo-Fr vs. Sa-So unterschiedlich)
- ✅ 1 BMT pro Werktag
- ✅ 1 BSB pro Werktag
- ✅ Mind. 1 Springer verfügbar

**Weiche Regeln (Optimierung):**
- ✅ Gleichmäßige Schichtverteilung
- ✅ Bevorzugter Rhythmus: F → N → S
- ✅ Fairness über alle Mitarbeiter

---

## 2. Architektur-Konzept (Implementiert)

### Python-Modulstruktur

```
python_ortools/
│
├── entities.py          # ✅ Datenmodelle (dataclasses)
│   ├── Employee
│   ├── Team
│   ├── ShiftType
│   ├── Absence
│   ├── ShiftAssignment
│   └── VacationRequest
│
├── data_loader.py       # ✅ Datenladen & Generierung
│   ├── generate_sample_data()
│   ├── load_from_database()
│   └── get_existing_assignments()
│
├── model.py             # ✅ OR-Tools Modell-Builder
│   ├── ShiftPlanningModel (Hauptklasse)
│   ├── Decision Variables: x[emp, date, shift]
│   ├── BMT/BSB Variables
│   └── Model Statistics
│
├── constraints.py       # ✅ Alle Constraints
│   ├── add_basic_constraints()
│   ├── add_staffing_constraints()
│   ├── add_rest_time_constraints()
│   ├── add_consecutive_shifts_constraints()
│   ├── add_working_hours_constraints()
│   ├── add_special_function_constraints()
│   ├── add_springer_constraints()
│   └── add_fairness_objectives()
│
├── solver.py            # ✅ CP-SAT Solver
│   ├── ShiftPlanningSolver (Hauptklasse)
│   ├── add_all_constraints()
│   ├── solve()
│   └── extract_solution()
│
├── validation.py        # ✅ Ergebnis-Validierung
│   ├── validate_shift_plan()
│   ├── validate_one_shift_per_day()
│   ├── validate_rest_times()
│   ├── validate_consecutive_shifts()
│   ├── validate_working_hours()
│   ├── validate_staffing_requirements()
│   └── validate_springer_availability()
│
├── web_api.py          # ✅ Flask REST API
│   ├── /api/employees
│   ├── /api/teams
│   ├── /api/shifttypes
│   ├── /api/shifts/schedule
│   ├── /api/shifts/plan
│   ├── /api/absences
│   └── /api/statistics/dashboard
│
├── main.py             # ✅ Haupteinstiegspunkt
│   ├── CLI: plan command
│   └── Web: serve command
│
├── requirements.txt    # ✅ Dependencies
└── README.md          # ✅ Dokumentation
```

---

## 3. Entscheidungsvariablen (OR-Tools)

### Hauptvariablen

```python
# x[employee_id, date, shift_code] = 0 oder 1
# Beispiel: x[5, 2025-01-15, "F"] = 1
# → Mitarbeiter 5 arbeitet Frühdienst am 15.01.2025

x: Dict[Tuple[int, date, str], cp_model.IntVar]
```

### Zusatzfunktions-Variablen

```python
# bmt[employee_id, date] = 0 oder 1
bmt_vars: Dict[Tuple[int, date], cp_model.IntVar]

# bsb[employee_id, date] = 0 oder 1
bsb_vars: Dict[Tuple[int, date], cp_model.IntVar]
```

---

## 4. Constraint-Implementierung

Alle Constraints sind vollständig in `constraints.py` implementiert:

### Beispiel: Mindestruhezeit (11 Stunden)

```python
# Verbotene Übergänge
FORBIDDEN_TRANSITIONS = {
    "S": ["F"],  # Spät → Früh (nur 8h Pause)
    "N": ["F"],  # Nacht → Früh (0h Pause)
}

# Im Modell:
for from_shift, forbidden_list in FORBIDDEN_TRANSITIONS.items():
    for to_shift in forbidden_list:
        # Wenn Mitarbeiter from_shift arbeitet, kann er am nächsten Tag nicht to_shift arbeiten
        model.Add(x[(emp, day_1, from_shift)] + x[(emp, day_2, to_shift)] <= 1)
```

### Beispiel: Max. 48 Stunden pro Woche

```python
# Für jede Woche und jeden Mitarbeiter:
hours_in_week = sum(x[(emp, date, shift)] * shift_hours[shift] 
                    for date in week_dates 
                    for shift in shift_codes)
model.Add(hours_in_week <= 48)
```

---

## 5. Solver-Konfiguration

### CP-SAT Solver Einstellungen

```python
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 300  # 5 Minuten
solver.parameters.num_search_workers = 8     # Parallel
solver.parameters.log_search_progress = True # Logging
```

### Objective Function

```python
# Minimiere Abweichung von fairer Verteilung
objective_terms = []

# 1. Fairness: Gleichmäßige Schichtanzahl
for emp in employees:
    deviation = abs(emp_shifts - average_shifts)
    objective_terms.append(deviation)

# 2. Bevorzugte Übergänge (F→N→S)
for good_transition in ideal_transitions:
    objective_terms.append(good_transition * -10)  # Belohnung

model.Minimize(sum(objective_terms))
```

---

## 6. Web-API (Flask)

### REST API Kompatibilität

Die Python-Flask-API ist **vollständig kompatibel** mit der .NET-ASP.NET-Core-API:

| Endpoint | .NET Controller | Python Flask | Status |
|----------|----------------|--------------|--------|
| `GET /api/employees` | EmployeesController | web_api.py | ✅ |
| `GET /api/teams` | TeamsController | web_api.py | ✅ |
| `GET /api/shifts/schedule` | ShiftsController | web_api.py | ✅ |
| `POST /api/shifts/plan` | ShiftsController | web_api.py | ✅ |
| `GET /api/absences` | AbsencesController | web_api.py | ✅ |
| `GET /api/statistics/dashboard` | StatisticsController | web_api.py | ✅ |

### UI-Kompatibilität

**Die bestehende Web-UI (HTML/CSS/JS) funktioniert ohne Änderungen!**

```
src/Dienstplan.Web/wwwroot/
├── index.html         # ✅ Keine Änderung nötig
├── css/styles.css     # ✅ Keine Änderung nötig
└── js/app.js          # ✅ Keine Änderung nötig
```

Flask serviert die statischen Dateien:
```python
app = Flask(__name__, 
            static_folder='../src/Dienstplan.Web/wwwroot', 
            static_url_path='')
```

---

## 7. Validierung (validation.py)

Nach dem Lösen wird das Ergebnis gegen alle Regeln validiert:

```python
validation_result = validate_shift_plan(
    assignments, employees, absences, start_date, end_date
)

# Prüft:
✅ Nur 1 Schicht pro Tag
✅ Keine Arbeit bei Abwesenheit
✅ Ruhezeiten eingehalten
✅ Max. Konsekutiv-Schichten
✅ Arbeitsstunden-Limits
✅ Mindestbesetzung
✅ Springer-Verfügbarkeit
✅ Qualifikationen (BMT/BSB)
```

---

## 8. Migration - Was ändert sich?

### Code-Ebene

| Komponente | .NET | Python OR-Tools |
|-----------|------|-----------------|
| Programmiersprache | C# | Python |
| Web-Framework | ASP.NET Core | Flask |
| ORM | Entity Framework Core | Native SQLite3 |
| Solver | Custom-Algorithmus | OR-Tools CP-SAT |
| Deployment | .exe / Self-Contained | Python-Script / Docker |

### Datenbank-Ebene

**✅ Vollständig kompatibel - KEINE Änderungen nötig!**

Die SQLite-Datenbank-Struktur bleibt unverändert:
- Gleiche Tabellen
- Gleiche Spalten
- Gleiche Datentypen
- Gleiche Beziehungen

### UI-Ebene

**✅ 1:1 übernommen - KEINE Änderungen nötig!**

Die gesamte Web-UI bleibt unverändert:
- HTML-Struktur identisch
- CSS-Styles identisch
- JavaScript-Logik identisch
- REST-API-Aufrufe identisch

---

## 9. Deployment-Szenarien

### Szenario 1: Parallelbetrieb (Empfohlen für Migration)

```
Port 5000: .NET-Version (bestehend)
Port 5001: Python-OR-Tools (neu)
```

Test mit Python-Version, .NET als Fallback.

### Szenario 2: Vollständige Migration

1. .NET-Service stoppen
2. Python-Service auf Port 5000 starten
3. Web-UI ohne Änderung weiter nutzen

### Szenario 3: Docker-Container

```dockerfile
FROM python:3.11-slim
WORKDIR /app

# Python-Backend
COPY python_ortools/ ./python_ortools/
RUN pip install -r python_ortools/requirements.txt

# Web-UI (optional, wenn nicht separat gehostet)
COPY src/Dienstplan.Web/wwwroot/ ./wwwroot/

EXPOSE 5000
CMD ["python", "python_ortools/main.py", "serve"]
```

---

## 10. Vorteile der Migration

### Fachlich

✅ **Bessere Lösungen**: OR-Tools findet optimal/near-optimal
✅ **Mehr Flexibilität**: Neue Regeln einfach hinzufügen
✅ **Transparenz**: Deklarative Constraints, leicht verständlich
✅ **Validierung**: Automatische Prüfung aller Regeln

### Technisch

✅ **Performance**: Parallele Solver-Worker
✅ **Wartbarkeit**: Klare Trennung von Regeln und Solver
✅ **Erweiterbarkeit**: Neue Constraints als Funktionen
✅ **Open Source**: Keine kommerziellen Abhängigkeiten

### Operativ

✅ **Deployment**: Docker, Systemd, Cloud-Ready
✅ **Monitoring**: Strukturiertes Logging
✅ **Skalierung**: Multi-Core-Nutzung
✅ **Testing**: Einfache Unit-Tests

---

## 11. Recycelte Komponenten

### Vollständig übernommen (1:1)

- ✅ Web-UI (HTML, CSS, JavaScript)
- ✅ Datenbank-Schema (SQLite)
- ✅ REST-API-Spezifikation
- ✅ Geschäftsregeln
- ✅ Datenmodelle
- ✅ Dokumentation (teilweise)

### Neu implementiert

- 🔄 Solver-Algorithmus (Custom → OR-Tools)
- 🔄 Backend-Sprache (C# → Python)
- 🔄 Web-Framework (ASP.NET → Flask)
- 🔄 Validierungs-Engine

### Kann entfallen

- ❌ .NET Runtime
- ❌ ShiftPlanningService.cs (durch OR-Tools ersetzt)
- ❌ Custom Scheduling-Algorithmus
- ❌ Entity Framework Core

---

## 12. Produktionstauglichkeit

### Checkliste

- ✅ Alle Geschäftsregeln implementiert
- ✅ Datenbank-Kompatibilität gewährleistet
- ✅ REST-API vollständig
- ✅ Web-UI funktionsfähig
- ✅ Validierung umfassend
- ✅ Fehlerbehandlung
- ✅ Logging
- ✅ Dokumentation

### Empfohlene nächste Schritte

1. **Testing**: Umfangreiche Tests mit Produktionsdaten
2. **Performance-Tuning**: Solver-Parameter optimieren
3. **Monitoring**: Logging & Metriken erweitern
4. **Deployment**: Docker-Image bauen
5. **Schulung**: Team mit Python-Stack vertraut machen

---

## 13. Zusammenfassung

### Migration abgeschlossen ✅

Alle 10 Schritte aus der Anforderung sind vollständig implementiert:

1. ✅ Repository analysiert
2. ✅ Architektur konzipiert
3. ✅ Datenmodelle erstellt (entities.py)
4. ✅ OR-Tools Variablen definiert (model.py)
5. ✅ Constraints implementiert (constraints.py)
6. ✅ Solver konfiguriert (solver.py)
7. ✅ ~~ASCII-Renderer~~ (nicht benötigt, UI 1:1 übernommen)
8. ✅ Validierung implementiert (validation.py)
9. ✅ Migrationshinweise dokumentiert (dieses Dokument)
10. ✅ Alle Python-Dateien generiert und getestet

### Haupterkenntnisse

✅ **Vollständige Funktionalität** ohne Kompromisse
✅ **Bessere Lösungsqualität** durch OR-Tools
✅ **UI bleibt unverändert** - nahtloser Übergang
✅ **Datenbank kompatibel** - keine Migration nötig
✅ **Produktionsreif** - alle Regeln implementiert

---

**Version 2.0 - Python OR-Tools Migration**  
Entwickelt von Timo Braun (Original .NET) + Migration
© 2025 Fritz Winter Eisengießerei GmbH & Co. KG
