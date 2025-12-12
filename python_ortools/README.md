# Python OR-Tools Migration - README

## Übersicht

Dies ist die vollständige Migration des Dienstplan-Systems von .NET nach Python mit Google OR-Tools als Constraint-Solver.

## Projektstruktur

```
python_ortools/
├── entities.py          # Datenmodelle (Employee, Team, Shift, etc.)
├── data_loader.py       # Datenladen (Datenbank & Sample-Daten)
├── model.py             # OR-Tools CP-SAT Modell
├── constraints.py       # Alle Constraint-Implementierungen
├── solver.py            # OR-Tools Solver-Konfiguration
├── validation.py        # Ergebnis-Validierung
├── web_api.py          # Flask REST API (kompatibel mit .NET UI)
├── main.py             # Haupteinstiegspunkt (CLI & Server)
└── requirements.txt    # Python-Abhängigkeiten
```

## Installation

### 1. Python-Umgebung einrichten

```bash
# Python 3.8+ erforderlich
python --version

# Virtuelle Umgebung erstellen (empfohlen)
python -m venv venv

# Aktivieren
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### 2. Abhängigkeiten installieren

```bash
cd python_ortools
pip install -r requirements.txt
```

## Verwendung

### CLI-Modus: Schichtplanung

```bash
# Mit Sample-Daten (zum Testen)
python main.py plan --start-date 2025-01-01 --end-date 2025-01-31 --sample-data

# Mit vorhandener Datenbank
python main.py plan --start-date 2025-01-01 --end-date 2025-01-31 --db ../dienstplan.db

# Mit Zeitlimit
python main.py plan --start-date 2025-01-01 --end-date 2025-01-31 --time-limit 600
```

### Web-Server-Modus

```bash
# Server starten (Port 5000)
python main.py serve

# Mit eigener Konfiguration
python main.py serve --host 0.0.0.0 --port 8080 --db ../dienstplan.db
```

Die bestehende Web-UI aus dem .NET-Projekt ist vollständig kompatibel mit diesem Backend!

## Kernfunktionalität

### Implementierte Regeln (Harte Constraints)

✅ **Grundregeln**
- Nur 1 Schicht pro Mitarbeiter und Tag
- Keine Arbeit während Abwesenheit

✅ **Mindestbesetzung**
- Früh: 4-5 Personen (Mo-Fr), 2-3 (Sa-So)
- Spät: 3-4 Personen (Mo-Fr), 2-3 (Sa-So)
- Nacht: 3 Personen (Mo-Fr), 2-3 (Sa-So)

✅ **Ruhezeiten**
- Minimum 11 Stunden zwischen Schichten
- Verbotene Übergänge: Spät→Früh, Nacht→Früh

✅ **Arbeitszeitbeschränkungen**
- Max. 6 aufeinanderfolgende Dienste
- Max. 5 aufeinanderfolgende Nachtdienste
- Max. 48 Stunden pro Woche
- Max. 192 Stunden pro Monat

✅ **Zusatzfunktionen**
- 1 BMT (Brandmeldetechniker) pro Werktag (Mo-Fr)
- 1 BSB (Brandschutzbeauftragter) pro Werktag (Mo-Fr)
- Nur qualifizierte Mitarbeiter

✅ **Springer-Logik**
- Mindestens 1 Springer muss verfügbar bleiben
- Teamübergreifender Einsatz möglich

### Optimierungsziele (Weiche Constraints)

✅ **Fairness**
- Gleichmäßige Schichtverteilung über alle Mitarbeiter
- Bevorzugter Rhythmus: Früh → Nacht → Spät

## Technische Details

### OR-Tools CP-SAT Solver

Das System verwendet den **CP-SAT (Constraint Programming - Satisfiability)** Solver von Google OR-Tools:

- **Entscheidungsvariablen**: `x[employee_id, date, shift_code]` (Boolean)
- **Zusatzfunktions-Variablen**: `bmt[employee_id, date]`, `bsb[employee_id, date]`
- **Constraints**: Alle Regeln als lineare Constraints formuliert
- **Objective**: Minimierung der Fairness-Abweichungen

### Datenbankkompatibilität

Das System ist **vollständig kompatibel** mit der SQLite-Datenbank des .NET-Projekts:

- Liest Mitarbeiter, Teams, Abwesenheiten
- Schreibt Schichtzuweisungen zurück
- Verwendet gleiche Tabellenstruktur
- Migration ohne Datenverlust möglich

### REST API

Die Flask-basierte REST API implementiert alle Endpoints der .NET-Version:

- `GET /api/employees` - Alle Mitarbeiter
- `GET /api/employees/springers` - Alle Springer
- `GET /api/teams` - Alle Teams
- `GET /api/shifttypes` - Alle Schichtarten
- `GET /api/shifts/schedule` - Schichtplan für Zeitraum
- `POST /api/shifts/plan` - Automatische Planung
- `GET /api/absences` - Alle Abwesenheiten
- `GET /api/statistics/dashboard` - Dashboard-Statistiken

**Die bestehende Web-UI (HTML/CSS/JS) funktioniert ohne Änderungen!**

## Migration von .NET nach Python

### Was bleibt gleich?

✅ **Datenbank**: SQLite-Struktur unverändert
✅ **Web-UI**: HTML, CSS, JavaScript 1:1 übernommen
✅ **REST API**: Alle Endpoints kompatibel
✅ **Geschäftsregeln**: Alle Regeln implementiert
✅ **Funktionalität**: Vollständiger Feature-Umfang

### Was ändert sich?

🔄 **Backend-Sprache**: C# → Python
🔄 **Solver**: Custom-Algorithmus → OR-Tools CP-SAT
🔄 **Web-Framework**: ASP.NET Core → Flask
🔄 **Deployment**: .exe → Python-Script

### Vorteile der Migration

✅ **Bessere Lösungsqualität**: OR-Tools findet optimale Lösungen
✅ **Flexibilität**: Einfach neue Constraints hinzufügen
✅ **Wartbarkeit**: Klarere Trennung von Regeln und Solver
✅ **Performance**: Parallele Solver-Worker
✅ **Open Source**: Vollständig mit Open-Source-Tools

## Produktionsbereitschaft

### Deployment-Optionen

**Option 1: Docker Container**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY python_ortools/ .
RUN pip install -r requirements.txt
CMD ["python", "main.py", "serve", "--host", "0.0.0.0"]
```

**Option 2: Systemd Service (Linux)**
```ini
[Unit]
Description=Dienstplan Python OR-Tools
After=network.target

[Service]
Type=simple
User=dienstplan
WorkingDirectory=/opt/dienstplan/python_ortools
ExecStart=/opt/dienstplan/venv/bin/python main.py serve
Restart=always

[Install]
WantedBy=multi-user.target
```

**Option 3: PyInstaller (Standalone Executable)**
```bash
pip install pyinstaller
pyinstaller --onefile --add-data "web_api.py:." main.py
```

### Empfohlene Konfiguration

- **Python Version**: 3.9 oder höher
- **Arbeitsspeicher**: Minimum 2 GB RAM
- **CPU**: Multi-Core empfohlen (Solver nutzt Parallelisierung)
- **Datenbank**: SQLite (für <1000 Mitarbeiter ausreichend)

## Tests & Validierung

### Komponententests

```bash
# Model-Test
python model.py

# Solver-Test
python solver.py

# Validierung-Test
python validation.py

# Data-Loader-Test
python data_loader.py
```

### Integration testen

```bash
# Vollständiger Planungslauf
python main.py plan --start-date 2025-01-01 --end-date 2025-01-31 --sample-data

# Web-Server starten und manuell testen
python main.py serve
# Browser: http://localhost:5000
```

## Fehlerbehebung

### Problem: OR-Tools kann nicht importiert werden
```bash
pip uninstall ortools
pip install ortools --no-cache-dir
```

### Problem: Keine Lösung gefunden
- Zeitlimit erhöhen: `--time-limit 600`
- Datum-Bereich verkleinern (z.B. 2 Wochen statt Monat)
- Constraints prüfen (zu viele Abwesenheiten?)

### Problem: Web-UI zeigt keine Daten
- Datenbank-Pfad korrekt? `--db ../dienstplan.db`
- CORS-Problem? Flask-CORS ist installiert
- Port bereits belegt? `--port 8080` verwenden

## Erweiterungen

### Neue Constraint hinzufügen

In `constraints.py`:
```python
def add_my_new_constraint(model, x, employees, dates, shift_codes):
    for emp in employees:
        for d in dates:
            # Ihre Logik hier
            model.Add(...)
```

In `solver.py` aktivieren:
```python
add_my_new_constraint(model, x, employees, dates, shift_codes)
```

### Neue API-Endpoint hinzufügen

In `web_api.py`:
```python
@app.route('/api/myendpoint', methods=['GET'])
def my_endpoint():
    # Ihre Logik hier
    return jsonify({...})
```

## Support & Entwicklung

Dieses Python-OR-Tools-Backend ist eine vollständige, produktionsreife Migration des .NET-Systems mit erweiterten Solver-Funktionen.

**Entwickler**: Migration von Timo Braun's .NET-Version
**OR-Tools**: Google Optimization Tools
**Lizenz**: MIT (wie Original)

## Vergleich: .NET vs. Python OR-Tools

| Feature | .NET Version | Python OR-Tools |
|---------|--------------|-----------------|
| Solver | Custom-Algorithmus | Google OR-Tools CP-SAT |
| Lösungsqualität | Heuristisch | Optimal/Near-Optimal |
| Performance | Gut | Sehr gut (parallel) |
| Wartbarkeit | Mittel | Hoch (deklarativ) |
| Erweiterbarkeit | Komplex | Einfach |
| Deployment | .exe | Script/Container |
| Dependencies | .NET 10 Runtime | Python 3.8+ |

---

**Version 2.0 - Python OR-Tools Migration**
© 2025 Fritz Winter Eisengießerei GmbH & Co. KG
