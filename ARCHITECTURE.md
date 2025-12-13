# Architektur-Dokumentation

## Übersicht

Das Dienstplan-System ist eine Python-basierte Anwendung zur automatischen Schichtplanung mit Google OR-Tools als Constraint-Solver. Die Architektur folgt klaren Prinzipien der Trennung von Verantwortlichkeiten.

## Architekturprinzipien

### 1. Modulare Struktur

```
┌─────────────────────────────────────────────────────────┐
│                     Web Layer                            │
│                    (web_api.py)                          │
│  - Flask REST API                                        │
│  - Static File Serving (wwwroot/)                       │
│  - CORS Configuration                                    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  Application Layer                       │
│                    (main.py)                             │
│  - CLI Interface                                         │
│  - Server Orchestration                                  │
│  - Command Routing                                       │
└──────────────────────┬──────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌────────────────┐
│  Solver     │ │   Model     │ │  Validation    │
│ (solver.py) │ │ (model.py)  │ │(validation.py) │
│             │ │             │ │                │
│ - OR-Tools  │ │ - Variables │ │ - Rule Check   │
│ - Config    │ │ - Objective │ │ - Reporting    │
│ - Execute   │ │ - Problem   │ │ - Verify       │
└──────┬──────┘ └──────┬──────┘ └────────┬───────┘
       │               │                  │
       │               ▼                  │
       │      ┌──────────────────┐       │
       │      │   Constraints    │       │
       └──────┤ (constraints.py) │───────┘
              │                  │
              │ - Hard Rules     │
              │ - Soft Rules     │
              │ - Logic          │
              └────────┬─────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                    Data Layer                            │
│              (data_loader.py, entities.py)               │
│  - Database Access (SQLite)                              │
│  - Data Models                                           │
│  - Sample Data Generation                                │
└─────────────────────────────────────────────────────────┘
```

### 2. Komponentenbeschreibung

#### Web Layer
**Datei:** `web_api.py`

- **Zweck**: REST API und Web-Schnittstelle
- **Technologie**: Flask + Flask-CORS
- **Verantwortlichkeiten**:
  - HTTP Endpoints (REST API)
  - Static File Serving (HTML/CSS/JS)
  - Request/Response Handling
  - CORS-Konfiguration

**Hauptendpoints:**
- `/api/employees` - Mitarbeiterverwaltung
- `/api/teams` - Teamverwaltung
- `/api/shifts/*` - Schichtplanung und Abfrage
- `/api/statistics/*` - Statistiken und Reports
- `/api/absences` - Abwesenheitsverwaltung
- `/*` - Static Files (Web UI)

#### Application Layer
**Datei:** `main.py`

- **Zweck**: Haupteinstiegspunkt und Orchestrierung
- **Verantwortlichkeiten**:
  - CLI-Interface (argparse)
  - Server-Start
  - Kommando-Routing (plan, serve)
  - Parameter-Verarbeitung

**Kommandos:**
```bash
python main.py serve [--host HOST] [--port PORT] [--db PATH]
python main.py plan --start-date DATE --end-date DATE [--sample-data] [--db PATH]
```

#### Solver Layer
**Dateien:** `solver.py`, `model.py`, `constraints.py`

**solver.py:**
- OR-Tools CP-SAT Solver Konfiguration
- Solver-Parameter (Zeitlimit, Worker)
- Lösungsextraktion

**model.py:**
- Modellaufbau (Variablen, Zielfunktion)
- Problem-Formulierung
- Variable-Definition

**constraints.py:**
- Alle Geschäftsregeln als Constraints
- Harte Constraints (MUST)
- Weiche Constraints (SHOULD)

**Implementierte Constraints:**

*Harte Constraints:*
- Genau 1 Schicht pro Person und Tag (oder keine)
- Keine Arbeit während Abwesenheit
- Mindestbesetzung für alle Schichttypen
- Verbotene Schichtwechsel (Spät→Früh, Nacht→Früh)
- Ruhezeiten (11 Stunden minimum)
- Max. 6 aufeinanderfolgende Schichten
- Max. 5 aufeinanderfolgende Nachtschichten
- Max. 48h pro Woche
- Max. 192h pro Monat
- Mindestens 1 Springer verfügbar
- Qualifikations-Anforderungen (BMT/BSB)

*Weiche Constraints (Optimierung):*
- Faire Schichtverteilung
- Bevorzugter Rhythmus (Früh→Nacht→Spät)
- Minimierung von Abweichungen

#### Validation Layer
**Datei:** `validation.py`

- **Zweck**: Ergebnis-Validierung
- **Verantwortlichkeiten**:
  - Überprüfung aller Regeln
  - Fehlerreporting
  - Qualitätssicherung

**Validierungen:**
- Schichtkonflikte
- Ruhezeiten
- Arbeitszeit-Limits
- Besetzungsstärken
- Springer-Verfügbarkeit

#### Data Layer
**Dateien:** `data_loader.py`, `entities.py`

**entities.py:**
- Datenmodelle (Dataclasses)
- Employee, Team, ShiftType, Absence, etc.
- Enum-Definitionen (AbsenceType)

**data_loader.py:**
- Datenbankzugriff (SQLite)
- Sample-Data-Generierung
- Daten-Import/-Export

**Datenmodelle:**
```python
@dataclass
class Employee:
    id: int
    vorname: str
    name: str
    personalnummer: str
    is_springer: bool
    team_id: Optional[int]
    is_bmt: bool = False  # Brandmeldetechniker
    is_bsb: bool = False  # Brandschutzbeauftragter

@dataclass
class Team:
    id: int
    name: str
    description: str

@dataclass
class ShiftType:
    id: int
    code: str
    name: str
    start_time: str
    end_time: str
    duration_hours: float

@dataclass
class Absence:
    id: int
    employee_id: int
    type: AbsenceType
    start_date: date
    end_date: date

@dataclass
class ShiftAssignment:
    id: int
    employee_id: int
    shift_type_id: int
    date: date
    is_manual: bool
    is_springer: bool
```

## 3. Datenfluss

### Schichtplanung (CLI)
```
main.py (CLI)
    ↓
data_loader.py (Load Data)
    ↓
model.py (Build Model)
    ↓
constraints.py (Add Rules)
    ↓
solver.py (Solve)
    ↓
validation.py (Verify)
    ↓
data_loader.py (Save Results)
```

### Web-Anfrage (API)
```
Client (Browser)
    ↓ HTTP Request
web_api.py (Flask Endpoint)
    ↓
data_loader.py (Database Query)
    ↓
web_api.py (JSON Response)
    ↓ HTTP Response
Client (Browser)
```

### Automatische Planung (API)
```
Client (Browser)
    ↓ POST /api/shifts/plan
web_api.py (Flask Endpoint)
    ↓
data_loader.py (Load Data)
    ↓
solver.py → model.py → constraints.py
    ↓
validation.py (Verify)
    ↓
data_loader.py (Save Results)
    ↓
web_api.py (JSON Response)
    ↓ HTTP Response
Client (Browser)
```

## 4. Technologie-Stack

### Backend
- **Python**: 3.9+
- **OR-Tools**: Google Constraint Programming Solver
- **Flask**: Web Framework
- **Flask-CORS**: Cross-Origin Resource Sharing

### Frontend
- **HTML5**: Struktur
- **CSS3**: Styling
- **JavaScript (Vanilla)**: Interaktivität
- **Fetch API**: AJAX-Requests

### Datenbank
- **SQLite**: Eingebettete Datenbank
- **Schema**: Kompatibel mit ursprünglicher .NET-Version

### Dependencies
```
ortools>=9.8.0        # Constraint Solver
Flask>=3.0.0          # Web Framework
flask-cors>=4.0.0     # CORS Support
```

## 5. Design-Patterns

### 1. Constraint Programming Pattern
- **Deklarative Problemformulierung**
- **Separation of Concerns**: Constraints getrennt von Solver
- **Composable**: Constraints können aktiviert/deaktiviert werden

### 2. Repository Pattern
- **data_loader.py** agiert als Data Access Layer
- Abstraktion der Datenbankzugriffe
- Wiederverwendbare Lade-/Speicher-Funktionen

### 3. Service Layer Pattern
- **web_api.py** als Service-Schicht
- Business-Logik (Solver) getrennt von API-Layer
- Klare Endpoint-Definition

### 4. Factory Pattern
- **create_app()** in web_api.py
- Konfigurierbare App-Erstellung
- Dependency Injection (db_path)

### 5. Command Pattern
- **main.py** CLI-Commands (serve, plan)
- Klare Kommando-Struktur
- Erweiterbar für neue Commands

## 6. Konfiguration

### Umgebungsvariablen
Keine Umgebungsvariablen erforderlich. Konfiguration über CLI-Parameter.

### CLI-Parameter

**Server-Modus:**
- `--host`: Host-Adresse (default: localhost)
- `--port`: Port-Nummer (default: 5000)
- `--db`: Datenbank-Pfad (default: dienstplan.db)

**Planungs-Modus:**
- `--start-date`: Start-Datum (ISO Format)
- `--end-date`: End-Datum (ISO Format)
- `--db`: Datenbank-Pfad (default: dienstplan.db)
- `--sample-data`: Verwende generierte Sample-Daten
- `--time-limit`: Solver-Zeitlimit in Sekunden (default: 300)

### Solver-Konfiguration
In `solver.py`:
```python
solver.parameters.max_time_in_seconds = 300  # 5 Minuten
solver.parameters.num_search_workers = 8     # Parallele Worker
solver.parameters.log_search_progress = True # Logging
```

## 7. Datenbankschema

### Tabellen
- **Employees**: Mitarbeiter
- **Teams**: Teams
- **ShiftTypes**: Schichtarten
- **ShiftAssignments**: Schichtzuweisungen
- **Absences**: Abwesenheiten
- **VacationRequests**: Urlaubsanträge
- **ShiftExchanges**: Diensttausch
- **AspNetUsers**: Benutzer (Identity)
- **AspNetRoles**: Rollen (Identity)

### Wichtige Relationen
```
Employees ───┐
             ├──→ ShiftAssignments
ShiftTypes ──┘

Employees ──→ Absences

Employees ──→ Teams
```

## 8. Skalierbarkeit

### Horizontale Skalierung
- Mehrere Flask-Instanzen hinter Load Balancer
- Shared SQLite-Datenbank oder Migration zu PostgreSQL/MySQL
- Stateless API-Design

### Vertikale Skalierung
- OR-Tools nutzt mehrere CPU-Cores (num_search_workers)
- Speicher-Anforderungen: ~100MB + 10MB pro 100 Mitarbeiter/Monat
- Optimierungen für größere Probleminstanzen möglich

### Performance-Optimierungen
- **Solver**: Zeitlimit anpassen
- **Datenbank**: Indizes auf häufig abgefragte Spalten
- **Web**: Caching für statische Daten
- **API**: Paginierung für große Listen

## 9. Sicherheit

### Implementiert
- ✅ Cookie-basierte Authentifizierung (über Web UI)
- ✅ Rollenbasierte Autorisierung
- ✅ SQL-Injection-Schutz (Parametrisierte Queries)
- ✅ CORS-Konfiguration

### Empfohlene Erweiterungen
- [ ] HTTPS (via Reverse Proxy)
- [ ] Rate Limiting
- [ ] Input Validation (strict)
- [ ] API Token Authentication
- [ ] Audit Logging

## 10. Testing

### Unit Tests
- Jede Komponente einzeln testbar
- Mock-Data für isolierte Tests
- `pytest` Framework empfohlen

### Integration Tests
- CLI-Tests mit Sample-Data
- API-Tests mit HTTP-Requests
- End-to-End-Tests

### Test-Strategien
```python
# Model-Test
python model.py

# Solver-Test mit Sample-Data
python main.py plan --start-date 2025-01-01 --end-date 2025-01-31 --sample-data

# Validation-Test
python validation.py
```

## 11. Deployment-Optionen

### Docker Container
**Vorteile:**
- Isolierte Umgebung
- Einfaches Deployment
- Reproduzierbare Builds

### Systemd Service
**Vorteile:**
- Native Linux-Integration
- Automatischer Neustart
- Log-Management

### Cloud-Plattformen
**Unterstützte Plattformen:**
- Heroku
- AWS Elastic Beanstalk
- Google Cloud Run
- Azure App Service

## 12. Monitoring & Logging

### Logging
Flask Standard-Logging:
```python
app.logger.info("Message")
app.logger.warning("Warning")
app.logger.error("Error")
```

### Monitoring
Empfohlene Tools:
- **Prometheus**: Metriken
- **Grafana**: Dashboards
- **Sentry**: Error Tracking

## 13. Erweiterbarkeit

### Neue Constraints hinzufügen
1. Funktion in `constraints.py` erstellen
2. In `solver.py` aufrufen
3. In `validation.py` prüfen

### Neue API-Endpoints
1. Route in `web_api.py` definieren
2. Business-Logik implementieren
3. JSON-Response zurückgeben

### Neue Datenmodelle
1. Dataclass in `entities.py` erstellen
2. Lade-/Speicher-Funktionen in `data_loader.py`
3. API-Endpoints in `web_api.py`

## 14. Migration von .NET

### Beibehaltene Konzepte
- ✅ Datenbank-Schema
- ✅ REST API-Struktur
- ✅ Web UI (HTML/CSS/JS)
- ✅ Geschäftsregeln

### Neue Konzepte
- 🆕 Constraint Programming (OR-Tools)
- 🆕 Deklarative Regel-Definition
- 🆕 Optimale Lösungsfindung
- 🆕 Python-basierte Architektur

### Vorteile der neuen Architektur
- ✅ Einfachere Wartung
- ✅ Bessere Lösungsqualität
- ✅ Flexible Erweiterbarkeit
- ✅ Plattformunabhängigkeit

---

**Version 2.0 - Python Edition**

Entwickelt von **Timo Braun** mit ❤️ für effiziente Schichtverwaltung

© 2025 Fritz Winter Eisengießerei GmbH & Co. KG
