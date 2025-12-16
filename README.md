# Dienstplan - Automatisches Schichtverwaltungssystem

**Version 2.0 - Python Edition** | Entwickelt von Timo Braun

Ein flexibles System zur Verwaltung und automatischen Planung von Schichtdiensten für Unternehmen jeder Größe. Powered by **Google OR-Tools** Constraint-Solver für optimale Schichtverteilung.

**Flexibel skalierbar**: Das System unterstützt beliebige Anzahlen von Mitarbeitern und Teams - nicht nur auf 17 Mitarbeiter in 3 Teams beschränkt.

![Dienstplan Hauptansicht](docs/screenshots/00-main-view.png)

---

## 📑 Inhaltsverzeichnis

- [🎯 Funktionsumfang](#-funktionsumfang)
- [📸 Screenshots](#-screenshots)
- [🏗️ Architektur](#%EF%B8%8F-architektur)
- [🚀 Installation & Ausführung](#-installation--ausführung)
- [📖 API-Dokumentation](#-api-dokumentation)
- [🔧 Konfiguration](#-konfiguration)
- [🧪 Tests](#-tests)
- [🔐 Sicherheit & Authentifizierung](#-sicherheit--authentifizierung)
- [🐳 Deployment](#-deployment)
- [🛠️ Entwicklung](#%EF%B8%8F-entwicklung)
- [🤝 Beitragen](#-beitragen)
- [📊 Migration von .NET zu Python](#-migration-von-net-zu-python)
- [🗺️ Roadmap](#%EF%B8%8F-roadmap)
- [📚 Dokumentation](#-dokumentation)
- [📄 Lizenz](#-lizenz)
- [🙋 Support & Kontakt](#-support--kontakt)

---

## 🎯 Funktionsumfang

### Mitarbeiterverwaltung
- **Pflichtfelder**: Vorname, Name, Personalnummer
- **Erweiterte Daten**: Geburtsdatum, Funktion (z.B. Brandmeldetechniker, Brandschutzbeauftragter)
- **Teamzuordnung**: Mitarbeiter können Teams zugeordnet werden
- **Springer-System**: Markierung von Backup-Mitarbeitern für automatische Vertretung bei Ausfällen
- **Ferienjobber**: Unterstützung für temporäre Mitarbeiter (meist in Sommerferien)
- **Abwesenheiten**: Verwaltung von Krank, Urlaub, Lehrgang
- **Arbeitszeitregeln**: Maximal 192 Stunden pro Monat, 48 Stunden pro Woche

### Urlaubsverwaltung
- **Urlaubsanträge**: Mitarbeiter können Urlaubswünsche einreichen
- **Status-Workflow**: In Bearbeitung → Genehmigt/Nicht genehmigt
- **Bearbeitung**: Disponent/Admin kann Anträge genehmigen oder ablehnen
- **Automatische Umwandlung**: Genehmigte Anträge werden automatisch zu Abwesenheiten
- **Statusverfolgung**: Mitarbeiter können den Status ihrer Anträge einsehen

### Diensttausch-System
- **Dienste anbieten**: Mitarbeiter können einzelne Dienste zum Tausch anbieten
- **Tauschangebote annehmen**: Andere Mitarbeiter können Dienste anfragen
- **Genehmigungspflicht**: Alle Tausche müssen vom Disponent genehmigt werden
- **Automatische Umschichtung**: Nach Genehmigung wird der Dienst automatisch umgetauscht
- **Nachverfolgung**: Vollständige Historie aller Tauschangebote

### Schichtarten
- **Früh (F)**: 05:45–13:45 Uhr
- **Spät (S)**: 13:45–21:45 Uhr
- **Nacht (N)**: 21:45–05:45 Uhr
- **Zwischendienst (Z)**: 08:00–16:00 Uhr
- **Brandmeldetechniker (BMT)**: 06:00-14:00 Uhr (Mo-Fr)
- **Brandschutzbeauftragter (BSB)**: 07:00-16:30 Uhr (Mo-Fr, 9,5 Stunden)
- **Tagdienst (TD)**: Speziell für qualifizierte Mitarbeiter (automatisch für BMT/BSB)
- **Abwesenheiten**: K (Krank), U (Urlaub), L (Lehrgang)

### Schichtbesetzung
**Montag–Freitag:**
- Früh: 4–5 Personen
- Spät: 3–4 Personen
- Nacht: 3 Personen

**Wochenende:**
- Alle Schichten: 2-3 Personen (Minimum 2, Maximum 3)

### Automatische Schichtplanung mit OR-Tools
Das System verwendet **Google OR-Tools CP-SAT Solver** für optimale Schichtplanung und beachtet folgende Regeln:

**Harte Constraints (müssen eingehalten werden):**
- ✅ Nur 1 Schicht pro Mitarbeiter und Tag
- ✅ Keine Arbeit während Abwesenheit
- ✅ Mindestbesetzung für alle Schichten
- 🚫 Verbotene Wechsel: Spät → Früh, Nacht → Früh
- ⏰ Gesetzliche Ruhezeiten (11 Stunden Minimum)
- 📊 Maximal 6 aufeinanderfolgende Schichten
- 🌙 Maximal 5 aufeinanderfolgende Nachtschichten
- ⏱️ Maximal 48 Stunden pro Woche
- 📅 Maximal 192 Stunden pro Monat
- 🔧 Mindestens 1 Springer muss verfügbar bleiben
- 🎯 1 BMT (Brandmeldetechniker) pro Werktag
- 🎯 1 BSB (Brandschutzbeauftragter) pro Werktag

**Weiche Constraints (werden optimiert):**
- ⚖️ Gleichmäßige Schichtverteilung über alle Mitarbeiter
- 🔄 Bevorzugter Rhythmus: Früh → Nacht → Spät
- 📊 Faire Workload-Verteilung

### Dashboard & Statistiken
- 📊 Arbeitsstunden pro Mitarbeiter
- 📈 Schichtverteilung pro Team
- 📅 Fehltageübersicht
- 💼 Team-Workload Analyse
- 📆 Samstags-/Sonntagsdienste je Mitarbeiter (Nur Disponent/Admin)

### Änderungsverfolgung
- 📝 Jede Schichtänderung wird protokolliert
- 👤 Wer hat die Änderung vorgenommen?
- 🕐 Wann wurde die Änderung vorgenommen?

### Web-Schnittstelle
- 📱 Responsive Design (Desktop & Smartphone)
- 📆 Ansichten: Woche, Monat, Jahr
- 🔐 Authentifizierung und Autorisierung
- 👀 Lesezugriff für alle Mitarbeiter
- ⚡ Performante REST API

## 📸 Screenshots

### Anmeldung
![Anmeldedialog](docs/screenshots/00-login-modal.png)
*Sichere Anmeldung mit Rollenbasierter Zugriffskontrolle (Admin, Disponent, Mitarbeiter)*

### Dienstplan-Ansicht (Woche) - Administrator
![Dienstplan Wochenansicht Administrator](docs/screenshots/03-schedule-week-admin.png)
*Wochenansicht mit vollem Funktionsumfang nach Administrator-Anmeldung*

### Dienstplan-Ansicht (Monat)
![Dienstplan Monatsansicht](docs/screenshots/04-schedule-month-admin.png)
*Monatsansicht für besseren Überblick über längere Zeiträume*

### Dienstplan-Ansicht (Jahr)
![Dienstplan Jahresansicht](docs/screenshots/05-schedule-year-admin.png)
*Jahresansicht für die Langzeitplanung*

### Mitarbeiterverwaltung
![Mitarbeiterverwaltung](docs/screenshots/06-employees-list.png)
*Übersicht aller Mitarbeiter mit Teams, Personalnummern und Springer-Kennzeichnung*

### Urlaubsverwaltung
![Urlaubsanträge](docs/screenshots/07-vacation-requests.png)
*Verwaltung von Urlaubsanträgen mit Status-Workflow (In Bearbeitung, Genehmigt, Nicht genehmigt)*

### Diensttausch-System
![Diensttausch](docs/screenshots/08-shift-exchange.png)
*Mitarbeiter können Dienste zum Tausch anbieten - Genehmigung durch Disponent erforderlich*

### Statistiken & Auswertungen
![Statistiken](docs/screenshots/09-statistics.png)
*Umfassende Statistiken über Arbeitsstunden, Schichtverteilung, Fehltage und Team-Auslastung*

### Hilfe & Handbuch
![Handbuch](docs/screenshots/10-help-manual.png)
*Integriertes Benutzerhandbuch mit ausführlichen Anleitungen zu allen Funktionen*

### Administration
![Admin-Panel](docs/screenshots/11-admin-panel.png)
*Administrator-Panel mit Benutzerverwaltung, E-Mail-Einstellungen und globalen Systemparametern*

## 🏗️ Architektur

### Projektstruktur
```
Dienstplan/
├── entities.py          # Datenmodelle (Employee, Team, Shift, etc.)
├── data_loader.py       # Datenbankzugriff und Sample-Daten
├── model.py             # OR-Tools CP-SAT Modell
├── constraints.py       # Alle Constraint-Implementierungen
├── solver.py            # OR-Tools Solver-Konfiguration
├── validation.py        # Ergebnis-Validierung
├── web_api.py          # Flask REST API
├── main.py             # Haupteinstiegspunkt (CLI & Server)
├── requirements.txt    # Python-Abhängigkeiten
├── wwwroot/            # Web UI (HTML/CSS/JavaScript)
├── docs/               # Dokumentation und Screenshots
└── .github/            # CI/CD Pipeline
```

### Technologie-Stack
- **Backend**: Python 3.9+
- **Solver**: Google OR-Tools CP-SAT
- **Database**: SQLite (einfach austauschbar)
- **Web Framework**: Flask mit Flask-CORS
- **Frontend**: Vanilla JavaScript, CSS3, HTML5
- **API**: REST mit JSON

### Vorteile der OR-Tools-Lösung
- ✅ **Optimale Lösungen**: CP-SAT findet provably optimale oder near-optimale Lösungen
- ✅ **Flexibilität**: Neue Constraints einfach hinzufügbar
- ✅ **Wartbarkeit**: Klare Trennung von Geschäftslogik und Solver
- ✅ **Performance**: Parallele Solver-Worker für schnellere Berechnung
- ✅ **Skalierbarkeit**: Handhabt große Probleminstanzen effizient

## 🚀 Installation & Ausführung

### Option 1: Windows Standalone Executable (Empfohlen für Windows-Nutzer) 🎯

**Keine Installation erforderlich!** Einfach herunterladen und starten.

#### Download
Laden Sie die neueste Version von den [GitHub Releases](https://github.com/TimUx/Dienstplan/releases) herunter:
- **Dienstplan-Windows-v2.0.x.zip**

#### Installation & Start
1. ZIP-Datei entpacken
2. Doppelklick auf `Dienstplan.exe`
3. Der Webserver startet automatisch und öffnet Ihren Browser
4. Fertig! Das System ist unter `http://localhost:5000` erreichbar

**Vorteile:**
- ✅ Keine Python-Installation erforderlich
- ✅ Keine manuellen Abhängigkeiten
- ✅ Automatischer Browser-Start
- ✅ Sofort einsatzbereit
- ✅ Persistente Datenbank in `data/` Ordner
- ✅ Produktionsfertig mit Admin-Benutzer

**Standard-Anmeldung:**
- E-Mail: `admin@fritzwinter.de`
- Passwort: `Admin123!`
- ⚠️ **WICHTIG**: Ändern Sie das Passwort nach der ersten Anmeldung!

#### Eigene Executable erstellen
Falls Sie die Executable selbst bauen möchten:

**Windows:**
```cmd
REM Mit leerer Datenbank (Standard, produktionsfertig)
build_windows.bat

REM Mit Beispieldaten (für Tests)
build_windows.bat --sample-data
```

**Linux/macOS:**
```bash
chmod +x build_executable.sh

# Mit leerer Datenbank (Standard, produktionsfertig)
./build_executable.sh

# Mit Beispieldaten (für Tests)
./build_executable.sh --sample-data
```

Die Executable enthält:
- Python Runtime (keine separate Installation nötig)
- Alle Python-Bibliotheken (Flask, OR-Tools, etc.)
- Web UI Dateien (wwwroot)
- Vorkonfigurierte SQLite-Datenbank (data/dienstplan.db)
- Automatischer Server-Start und Browser-Öffnung

### Option 2: Python-Installation (Für alle Betriebssysteme)

#### Voraussetzungen
- Python 3.9 oder höher
- pip (Python Package Manager)

#### Schnellstart

##### 1. Repository klonen
```bash
git clone https://github.com/TimUx/Dienstplan.git
cd Dienstplan
```

##### 2. Virtuelle Umgebung erstellen (empfohlen)
```bash
# Linux/macOS:
python3 -m venv venv
source venv/bin/activate

# Windows:
python -m venv venv
venv\Scripts\activate
```

##### 3. Abhängigkeiten installieren
```bash
pip install -r requirements.txt
```

##### 4. Datenbank initialisieren (Wichtig!)

Vor dem ersten Start müssen Sie die Datenbank initialisieren:

```bash
python main.py init-db --with-sample-data
```

Dies erstellt:
- ✅ Alle erforderlichen Datenbanktabellen
- ✅ Standard-Rollen (Admin, Disponent, Mitarbeiter)
- ✅ Admin-Benutzer (admin@fritzwinter.de / Admin123!)
- ✅ Standard-Schichttypen
- ✅ Beispiel-Teams (optional mit --with-sample-data)

**Ohne Sample-Daten:**
```bash
python main.py init-db
```

##### 5. Anwendung starten

**Web-Server-Modus:**
```bash
# Server starten (Standard: Port 5000)
python main.py serve

# Mit eigener Konfiguration
python main.py serve --host 0.0.0.0 --port 8080 --db dienstplan.db
```

##### 6. Browser öffnen
Navigieren Sie zu: `http://localhost:5000`

**Standard-Anmeldedaten:**
- E-Mail: `admin@fritzwinter.de`
- Passwort: `Admin123!`

⚠️ **WICHTIG**: Ändern Sie das Passwort nach der ersten Anmeldung!

---

**CLI-Modus: Schichtplanung**
```bash
# Mit Sample-Daten (zum Testen)
python main.py plan --start-date 2025-01-01 --end-date 2025-01-31 --sample-data

# Mit vorhandener Datenbank
python main.py plan --start-date 2025-01-01 --end-date 2025-01-31 --db dienstplan.db

# Mit Zeitlimit (in Sekunden)
python main.py plan --start-date 2025-01-01 --end-date 2025-01-31 --time-limit 600
```

### (Optional) Sample-Datenbank generieren

Sie können Testdaten direkt über die Python-CLI generieren:

```bash
# Schichtplanung mit automatisch generierten Sample-Daten
python main.py plan --start-date 2025-01-01 --end-date 2025-01-31 --sample-data
```

Dies erstellt automatisch:
- 3 Teams (Alpha, Beta, Gamma)
- 17 Mitarbeiter mit verschiedenen Rollen
- 4 Springer
- Beispiel-Abwesenheiten

## 📖 API-Dokumentation

### Authentifizierungs-Endpoints

#### Anmelden
```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "admin@fritzwinter.de",
  "password": "Admin123!",
  "rememberMe": true
}
```

Antwort:
```json
{
  "success": true,
  "user": {
    "email": "admin@fritzwinter.de",
    "fullName": "Administrator",
    "roles": ["Admin"]
  }
}
```

#### Aktuellen Benutzer abrufen
```http
GET /api/auth/current-user
```

#### Abmelden
```http
POST /api/auth/logout
```

### Mitarbeiter-Endpoints

#### Alle Mitarbeiter abrufen
```http
GET /api/employees
Authorization: Optional (öffentlich lesbar)
```

#### Mitarbeiter erstellen
```http
POST /api/employees
Content-Type: application/json
Authorization: Required (Admin oder Disponent)

{
  "vorname": "Max",
  "name": "Mustermann",
  "personalnummer": "12345",
  "isSpringer": false,
  "teamId": 1
}
```

#### Springer abrufen
```http
GET /api/employees/springers
Authorization: Optional (öffentlich lesbar)
```

### Schicht-Endpoints

#### Dienstplan anzeigen
```http
GET /api/shifts/schedule?startDate=2025-01-01&view=week
Authorization: Optional (öffentlich lesbar)
```
Parameter:
- `startDate`: Startdatum (ISO Format)
- `view`: week, month, oder year
- `endDate`: Optional, überschreibt view

#### Schichten automatisch planen
```http
POST /api/shifts/plan?startDate=2025-01-01&endDate=2025-01-31&force=false
Authorization: Required (Admin oder Disponent)
```

### Statistik-Endpoints

#### Dashboard-Statistiken
```http
GET /api/statistics/dashboard?startDate=2025-01-01&endDate=2025-01-31
Authorization: Optional (öffentlich lesbar)
```

#### Wochenend-Schicht-Statistiken (Nur Disponent/Admin)
```http
GET /api/statistics/weekend-shifts?startDate=2025-01-01&endDate=2025-12-31
Authorization: Required (Admin oder Disponent)
```

### Export-Endpoints

#### CSV-Export
```http
GET /api/shifts/export/csv?startDate=2025-01-01&endDate=2025-01-31
Authorization: Optional (öffentlich lesbar)
```

#### PDF-Export
```http
GET /api/shifts/export/pdf?startDate=2025-01-01&endDate=2025-01-31&view=month
Authorization: Optional (öffentlich lesbar)
```

#### Excel-Export
```http
GET /api/shifts/export/excel?startDate=2025-01-01&endDate=2025-01-31
Authorization: Optional (öffentlich lesbar)
```

### Abwesenheits-Endpoints

#### Abwesenheiten abrufen
```http
GET /api/absences?startDate=2025-01-01&endDate=2025-01-31
Authorization: Optional (öffentlich lesbar)
```

#### Abwesenheit erstellen
```http
POST /api/absences
Content-Type: application/json
Authorization: Required (Admin oder Disponent)

{
  "employeeId": 1,
  "type": 1,
  "startDate": "2025-01-15",
  "endDate": "2025-01-20",
  "notes": "Jahresurlaub"
}
```
Typen: 1=Urlaub, 2=Krank, 3=Lehrgang

#### Abwesenheit löschen
```http
DELETE /api/absences/{id}
Authorization: Required (Admin oder Disponent)
```

### Urlaubsantrags-Endpoints

#### Urlaubsanträge abrufen
```http
GET /api/vacationrequests
Authorization: Required (eigene Anträge oder Admin/Disponent für alle)
```

#### Urlaubsantrag erstellen
```http
POST /api/vacationrequests
Content-Type: application/json
Authorization: Required (alle authentifizierten Benutzer)

{
  "startDate": "2025-06-01",
  "endDate": "2025-06-14",
  "reason": "Sommerurlaub"
}
```

#### Urlaubsantrag genehmigen/ablehnen
```http
PUT /api/vacationrequests/{id}/status
Content-Type: application/json
Authorization: Required (Admin oder Disponent)

{
  "status": 2,
  "comment": "Genehmigt"
}
```
Status: 1=In Bearbeitung, 2=Genehmigt, 3=Abgelehnt

### Diensttausch-Endpoints

#### Verfügbare Tauschangebote
```http
GET /api/shiftexchanges/available
Authorization: Required (alle authentifizierten Benutzer)
```

#### Offene Tausch-Anfragen (Admin/Disponent)
```http
GET /api/shiftexchanges/pending
Authorization: Required (Admin oder Disponent)
```

#### Dienst zum Tausch anbieten
```http
POST /api/shiftexchanges
Content-Type: application/json
Authorization: Required (alle authentifizierten Benutzer)

{
  "shiftAssignmentId": 123,
  "reason": "Private Verpflichtung"
}
```

#### Diensttausch anfragen
```http
POST /api/shiftexchanges/{id}/request
Authorization: Required (alle authentifizierten Benutzer)
```

#### Diensttausch genehmigen/ablehnen
```http
PUT /api/shiftexchanges/{id}/process
Content-Type: application/json
Authorization: Required (Admin oder Disponent)

{
  "approve": true,
  "comment": "Tausch genehmigt"
}
```

### Team-Endpoints

#### Alle Teams abrufen
```http
GET /api/teams
Authorization: Optional (öffentlich lesbar)
```

#### Team erstellen
```http
POST /api/teams
Content-Type: application/json
Authorization: Required (Admin oder Disponent)

{
  "name": "Team Delta",
  "description": "Neue Schichtgruppe"
}
```

#### Team bearbeiten
```http
PUT /api/teams/{id}
Content-Type: application/json
Authorization: Required (Admin oder Disponent)
```

#### Team löschen
```http
DELETE /api/teams/{id}
Authorization: Required (nur Admin)
```

### Weitere Endpoints

Eine vollständige API-Referenz finden Sie in [MIGRATION.md](MIGRATION.md) oder im Benutzerhandbuch.

**API-Basis-URL:** `http://localhost:5000/api/`

**Authentifizierung:** Cookie-basierte Sessions nach Login

## 🔧 Konfiguration

### Datenbankverbindung
Die Anwendung verwendet standardmäßig eine SQLite-Datenbank namens `dienstplan.db` im aktuellen Verzeichnis.

Sie können einen anderen Pfad über die Kommandozeile angeben:
```bash
python main.py serve --db /pfad/zur/datenbank.db
```

### OR-Tools Solver-Einstellungen
In `solver.py` können folgende Parameter angepasst werden:
- **Zeitlimit**: Maximale Lösungszeit (Standard: 300 Sekunden)
- **Worker**: Anzahl paralleler Solver-Threads (Standard: 8)
- **Search Strategy**: Such-Strategie des Solvers

## 🧪 Tests

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

## 🔐 Sicherheit & Authentifizierung

### Rollenbasierte Autorisierung
- **Admin**: Volle Berechtigung - alle Funktionen
  - Mitarbeiter erstellen, bearbeiten, löschen
  - Schichtplanung durchführen
  - Abwesenheiten verwalten
  - Neue Benutzer registrieren
- **Disponent**: Schichtplanung und Bearbeitung
  - Mitarbeiter erstellen und bearbeiten
  - Schichtplanung durchführen
  - Abwesenheiten verwalten
- **Mitarbeiter**: Nur Lesezugriff
  - Dienstplan ansehen
  - Statistiken einsehen
  - Mitarbeiterliste ansehen

### Standard-Anmeldedaten
Bei der ersten Ausführung wird automatisch ein Administrator-Account erstellt:
- **E-Mail**: admin@fritzwinter.de
- **Passwort**: Admin123!

**WICHTIG**: Ändern Sie das Standard-Passwort nach der ersten Anmeldung!

### Sicherheitshinweise für Produktion
1. **Passwörter ändern**: Ändern Sie alle Standard-Passwörter
2. **HTTPS verwenden**: Setzen Sie einen Reverse Proxy (nginx, Apache) vor Flask
3. **CORS konfigurieren**: Beschränken Sie erlaubte Origins in `web_api.py`
4. **Datenbank schützen**: SQLite-Datei vor unbefugtem Zugriff schützen
5. **Regular Updates**: Halten Sie alle Python-Pakete aktuell

## 🐳 Deployment

### Option 1: Windows Standalone Executable (Empfohlen für Desktop) ⭐

Die einfachste Methode für Windows-Anwender:

1. Laden Sie das neueste Release von GitHub herunter
2. Entpacken Sie die ZIP-Datei
3. Starten Sie `Dienstplan.exe`

**Für Entwickler:** Erstellen Sie Ihre eigene Executable mit:
```bash
# Windows
build_windows.bat

# Linux/macOS
./build_executable.sh
```

Die Executable enthält:
- Python Runtime (keine separate Installation nötig)
- Alle Python-Bibliotheken (Flask, OR-Tools, etc.)
- Web UI Dateien (wwwroot)
- Automatischer Server-Start und Browser-Öffnung

### Option 2: Docker Container (Für Server-Deployment)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 5000
CMD ["python", "main.py", "serve", "--host", "0.0.0.0"]
```

```bash
docker build -t dienstplan .
docker run -p 5000:5000 -v ./data:/app/data dienstplan
```

### Option 3: Systemd Service (Linux Server)
```ini
[Unit]
Description=Dienstplan Python OR-Tools
After=network.target

[Service]
Type=simple
User=dienstplan
WorkingDirectory=/opt/dienstplan
ExecStart=/opt/dienstplan/venv/bin/python main.py serve
Restart=always

[Install]
WantedBy=multi-user.target
```

## 🛠️ Entwicklung

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

### Beispieldaten für Entwicklung
Siehe [docs/SAMPLE_DATA.md](docs/SAMPLE_DATA.md) für Details zu Beispieldaten und API-Aufrufen.

## 🤝 Beitragen

### Entwicklungsrichtlinien
- Clean Code Prinzipien beachten
- Tests für neue Features
- Dokumentation aktualisieren
- PR gegen `main` Branch

### Branch-Strategie
- `main`: Produktionsreifer Code
- Feature-Branches: `feature/beschreibung`
- Bugfix-Branches: `bugfix/beschreibung`

## 📊 Migration von .NET zu Python

Diese Version 2.0 ist eine vollständige Neuimplementierung des Schichtplanungssystems in Python mit Google OR-Tools. Die vorherige .NET-Version wurde vollständig durch diese Python-Implementierung ersetzt.

### Hauptunterschiede
- **Solver**: Custom-Algorithmus → Google OR-Tools CP-SAT
- **Sprache**: C# → Python
- **Framework**: ASP.NET Core → Flask
- **Lösungsqualität**: Heuristisch → Optimal/Near-Optimal

### Vorteile der Python-Version
- ✅ Bessere Lösungsqualität durch OR-Tools
- ✅ Einfachere Wartung und Erweiterung
- ✅ Plattformunabhängig
- ✅ Keine Runtime-Dependencies (.NET SDK nicht erforderlich)

Details zur Migration: [MIGRATION.md](MIGRATION.md)

## 📚 Dokumentation

Das Dienstplan-System verfügt über eine umfassende Dokumentation:

### 📘 Für Benutzer
- **[Benutzerhandbuch](BENUTZERHANDBUCH.md)** - Vollständige Anleitung für alle Funktionen mit Screenshots
- **[Schnellstart](docs/QUICKSTART.md)** - In 5 Minuten produktiv
- **[Windows Standalone Guide](docs/WINDOWS_EXECUTABLE.md)** - Anleitung für die Exe-Version

### 🔧 Für Administratoren
- **[Nutzungsanleitung](docs/USAGE_GUIDE.md)** - CLI-Befehle und API-Nutzung
- **[Schichtplanungsalgorithmus](docs/SHIFT_PLANNING_ALGORITHM.md)** - Details zum OR-Tools Solver
- **[Beispieldaten](docs/SAMPLE_DATA.md)** - Testdaten und API-Beispiele

### 💻 Für Entwickler
- **[Architektur](ARCHITECTURE.md)** - System-Design und Komponenten
- **[Build-Anleitung](docs/BUILD_GUIDE.md)** - Executable erstellen
- **[Migration](MIGRATION.md)** - .NET zu Python Migration
- **[Changelog](CHANGELOG.md)** - Versionshistorie

### 📍 Zentrale Übersicht
- **[Dokumentationsindex](DOKUMENTATION.md)** - Zentraler Einstiegspunkt mit allen Links und Strukturen

## 📄 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert - siehe [LICENSE](LICENSE) für Details.

## 🙋 Support & Kontakt

Bei Fragen oder Problemen:
- GitHub Issues: https://github.com/TimUx/Dienstplan/issues
- Dokumentation: Siehe diese README und [docs/](docs/)

## 🗺️ Roadmap

### ✅ Version 2.0 - Abgeschlossen
- [x] **Migration zu Python** ✅ **v2.0**
- [x] **Google OR-Tools Integration** ✅ **v2.0**
- [x] **Optimale Schichtplanung** ✅ **v2.0**
- [x] **Mitarbeiterverwaltung** mit Springer-System ✅ **v2.0**
- [x] **Teamverwaltung** mit virtuellen Teams ✅ **v2.0**
- [x] **Urlaubsantrags-System** mit Workflow ✅ **v2.0**
- [x] **Diensttausch-Plattform** ✅ **v2.0**
- [x] **Statistiken & Dashboard** ✅ **v2.0**
- [x] **PDF/Excel/CSV-Export** ✅ **v2.0**
- [x] **Windows Standalone Executable** ✅ **v2.0**
- [x] **Ferienjobber-Support** ✅ **v2.0**
- [x] **BMT/BSB/TD Sonderfunktionen** ✅ **v2.0**
- [x] **Responsive Web-UI** ✅ **v2.0**
- [x] **Audit-Logging** ✅ **v2.0**

### 🔄 Version 2.1 - In Planung
- [ ] **E-Mail-Benachrichtigungen** (SMTP-Integration)
  - Urlaubsgenehmigungen
  - Diensttausch-Bestätigungen
  - Erinnerungen an bevorstehende Schichten
- [ ] **Erweiterte Berichte und Analytics**
  - Monatsberichte als PDF
  - Jahresübersichten
  - Export-Templates
- [ ] **Verbesserungen am Planungsalgorithmus**
  - Bevorzugte Rhythmen pro Mitarbeiter
  - Team-basierte Präferenzen

### 🚀 Version 3.0 - Zukünftig
- [ ] **Wunschschichten**
  - Mitarbeiter können bevorzugte Schichten angeben
  - Berücksichtigung bei automatischer Planung
  - Wunsch-Erfüllungsrate in Statistiken
- [ ] **Urlaubssperren**
  - Zeiträume definieren, in denen kein Urlaub möglich ist
  - Saisonale Einschränkungen
- [ ] **Zeiterfassung Integration**
  - Tatsächliche Arbeitszeiten erfassen
  - Überstunden-Tracking
  - Soll/Ist-Vergleich
- [ ] **Multi-Mandanten-Fähigkeit**
  - Mehrere Firmen/Standorte in einer Installation
  - Getrennte Datenbanken pro Mandant
  - Zentrale Verwaltung
- [ ] **Mobile App** (React Native)
  - Native Apps für iOS und Android
  - Push-Benachrichtigungen
  - Offline-Modus
- [ ] **Real-Time Benachrichtigungen** (WebSockets)
  - Live-Updates bei Änderungen
  - Chat-Funktion für Diensttausch
  - Benachrichtigungs-Center

---

**Version 2.0 - Python Edition** | Entwickelt von **Timo Braun** mit ❤️ für effiziente Schichtverwaltung

Powered by **Google OR-Tools**

© 2025 Fritz Winter Eisengießerei GmbH & Co. KG
