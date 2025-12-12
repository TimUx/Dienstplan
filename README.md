# Dienstplan - Automatisches Schichtverwaltungssystem

**Version 1.3** | Entwickelt von Timo Braun

Ein flexibles System zur Verwaltung und automatischen Planung von Schichtdiensten für Unternehmen jeder Größe. Mit erweitertem Algorithmus für faire Schichtverteilung, intelligenter Springer-Verwaltung und automatischer Zuweisung von Zusatzfunktionen.

**Flexibel skalierbar**: Das System unterstützt beliebige Anzahlen von Mitarbeitern und Teams - nicht nur auf 17 Mitarbeiter in 3 Teams beschränkt.

![Dienstplan Hauptansicht](docs/screenshots/00-main-view.png)

## 🎯 Funktionsumfang

### Mitarbeiterverwaltung
- **Pflichtfelder**: Vorname, Name, Personalnummer
- **Erweiterte Daten**: Geburtsdatum, Funktion (z.B. Brandmeldetechniker, Brandschutzbeauftragter)
- **Teamzuordnung**: Mitarbeiter können Teams zugeordnet werden
- **Springer-System**: Markierung von Backup-Mitarbeitern für automatische Vertretung bei Ausfällen
- **Ferienjobber**: Unterstützung für temporäre Mitarbeiter (meist in Sommerferien)
- **Abwesenheiten**: Verwaltung von Krank, Urlaub, Lehrgang
- **Arbeitszeitregeln**: Maximal 192 Stunden pro Monat, 48 Stunden pro Woche

### Urlaubsverwaltung 🆕
- **Urlaubsanträge**: Mitarbeiter können Urlaubswünsche einreichen
- **Status-Workflow**: In Bearbeitung → Genehmigt/Nicht genehmigt
- **Bearbeitung**: Disponent/Admin kann Anträge genehmigen oder ablehnen
- **Automatische Umwandlung**: Genehmigte Anträge werden automatisch zu Abwesenheiten
- **Statusverfolgung**: Mitarbeiter können den Status ihrer Anträge einsehen

### Diensttausch-System 🆕
- **Dienste anbieten**: Mitarbeiter können einzelne Dienste zum Tausch anbieten
- **Tauschangebote annehmen**: Andere Mitarbeiter können Dienste anfragen
- **Genehmigungspflicht**: Alle Tausche müssen vom Disponent genehmigt werden
- **Automatische Umschichtung**: Nach Genehmigung wird der Dienst automatisch umgetauscht
- **Nachverfolgung**: Vollständige Historie aller Tauschangebote

### Schichtarten
- **Früh**: 05:45–13:45 Uhr
- **Spät**: 13:45–21:45 Uhr
- **Nacht**: 21:45–05:45 Uhr
- **Zwischendienst**: 08:00–16:00 Uhr
- **Brandmeldetechniker**: 06:00-14:00 Uhr (Mo-Fr) 🆕
- **Brandschutzbeauftragter**: 07:00-16:30 Uhr (Mo-Fr, 9,5 Stunden) 🆕
- **Zusatzkürzel**: Flexibel erweiterbar für Sonderaufgaben

### Schichtbesetzung
**Montag–Freitag:**
- Früh: 4–5 Personen
- Spät: 3–4 Personen
- Nacht: 3 Personen

**Wochenende:**
- Alle Schichten: 2-3 Personen (Minimum 2, Maximum 3)

### Automatische Schichtplanung
Das System beachtet folgende Regeln:
- ✅ Nicht zweimal hintereinander dieselbe Schicht
- 🚫 Verbotene Wechsel: Spät → Früh, Nacht → Spät
- ⏰ Gesetzliche Ruhezeiten (11 Stunden Minimum)
- 📊 Maximal 6 Schichten am Stück 🆕
- 🌙 Maximal 3 Nachtschichten am Stück 🆕
- ⚖️ Gleichmäßige Verteilung über alle Mitarbeiter
- 📅 Gleichmäßige Wochenendverteilung innerhalb der Teams 🆕
- 🔄 Idealer Rhythmus: Früh → Nacht → Spät
- 📌 Feste Dienste (z.B. Feiertage) werden respektiert 🆕
- 🔧 Manuelle Änderungen jederzeit möglich
- 🆘 Automatischer Springer-Einsatz bei Ausfällen

### Dashboard & Statistiken
- 📊 Arbeitsstunden pro Mitarbeiter
- 📈 Schichtverteilung pro Team
- 📅 Fehltageübersicht
- 💼 Team-Workload Analyse
- 📆 Samstags-/Sonntagsdienste je Mitarbeiter (Nur Disponent/Admin) 🆕

### Änderungsverfolgung 🆕
- 📝 Jede Schichtänderung wird protokolliert
- 👤 Wer hat die Änderung vorgenommen?
- 🕐 Wann wurde die Änderung vorgenommen?
- 📢 Automatische Benachrichtigungen bei Änderungen (Vorbereitet)

### E-Mail-Benachrichtigungen 🆕
- **E-Mail-Adressen**: Erfassung von E-Mail-Adressen für Mitarbeiter und Teams
- **SMTP-Konfiguration**: Flexible Konfiguration der E-Mail-Server-Einstellungen
  - SMTP Server (DNS/IP), Port, Protokoll (SMTP, SMTPS)
  - Sicherheit (None, SSL, TLS, STARTTLS)
  - Authentifizierung (Benutzername/Passwort)
  - Absender- und Antwortadresse
- **Benachrichtigungen**: Automatische E-Mails bei Dienstplanänderungen, Urlaubsanträgen und Diensttauschen
- **Verwaltung**: Admin-Oberfläche für E-Mail-Einstellungen

### PDF-Export
- 📄 Professionelle PDF-Generierung von Dienstplänen
- 🎨 Farbcodierte Schichtarten für bessere Übersichtlichkeit
- 📋 Zusammenfassung mit Schichtanzahl pro Typ
- 📅 Flexible Zeitraumauswahl (Woche, Monat, Jahr)
- 📧 E-Mail-Versand vorbereitet

### Excel-Export (XLSX) 🆕
- 📊 Excel-Datei mit professioneller Formatierung
- 🎨 Farbcodierte Schichten wie in der Web-Ansicht
- 📐 Automatische Spaltenbreiten und Zeilenhöhen
- 👥 Gruppierung nach Teams
- 🔤 Legende mit allen Schichttypen
- 📅 Flexible Zeitraumauswahl
- 💾 Direkt in Excel bearbeitbar

### Erweiterte Algorithmus-Funktionen 🆕
- **Qualifikationsverwaltung**: Tracking von Brandmeldetechnikern (BMT) und Brandschutzbeauftragten (BSB)
- **Automatische Zusatzfunktionen**: Intelligente Zuweisung von BMT/BSB mit fairer Rotation
- **Enhanced Springer-Management**: 
  - Garantiert mindestens 1 verfügbarer Springer
  - Workload-basierte Auswahl
  - Teamübergreifender Einsatz
  - Automatische Vertretung bei Ausfällen
- **Fairness-Tracking**:
  - Gerechte Verteilung von Wochenendschichten
  - Ausgewogene Rotation aller Schichttypen
  - Tracking von Monatsstunden (192h Limit)
  - Tracking von Wochenstunden (48h Limit)
- **Monatsübergreifende Planung**: Validierung über Monatsgrenzen hinweg
- **Comprehensive Validation**: Prüfung aller gesetzlichen und organisatorischen Regeln

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
├── src/
│   ├── Dienstplan.Domain/          # Domain-Modelle und Business-Regeln
│   │   ├── Entities/               # Employee, Team, Shift, etc.
│   │   ├── Rules/                  # Schichtplanungsregeln
│   │   └── Interfaces/             # Repository-Interfaces
│   │
│   ├── Dienstplan.Application/     # Anwendungslogik
│   │   ├── Services/               # ShiftPlanningService, StatisticsService
│   │   └── DTOs/                   # Data Transfer Objects
│   │
│   ├── Dienstplan.Infrastructure/  # Datenzugriff
│   │   ├── Data/                   # DbContext
│   │   └── Repositories/           # Repository-Implementierungen
│   │
│   └── Dienstplan.Web/             # Web API & UI
│       ├── Controllers/            # REST API Endpoints
│       └── wwwroot/                # HTML, CSS, JavaScript
│
├── tests/                          # Unit- und Integrationstests
└── .github/workflows/              # CI/CD Pipeline
```

### Layer-Architektur
- **Domain**: Kerngeschäftslogik, unabhängig von externen Frameworks
- **Application**: Use Cases und Orchestrierung
- **Infrastructure**: Datenzugriff, externe Services
- **Web**: Präsentationsschicht, API, UI

### Technologie-Stack
- **Backend**: ASP.NET Core 10.0 (C#)
- **Database**: SQLite (einfach austauschbar)
- **ORM**: Entity Framework Core
- **Frontend**: Vanilla JavaScript, CSS3, HTML5
- **API**: REST mit OpenAPI/Swagger

## 🚀 Installation & Ausführung

### Voraussetzungen
- .NET 10.0 SDK oder höher
- Optional: Visual Studio 2022 oder VS Code

### Schnellstart

#### 1. Repository klonen
```bash
git clone https://github.com/TimUx/Dienstplan.git
cd Dienstplan
```

#### 2. Projekt bauen
```bash
dotnet build
```

#### 3. (Optional) Beispieldatenbank generieren
Für Entwicklung und Tests können Sie eine vorbefüllte Datenbank mit 17 Mitarbeitern und 3 Teams erstellen:

**Linux/macOS:**
```bash
# Einfach das bereitgestellte Skript ausführen
./generate-sample-db.sh
```

**Windows:**
```powershell
# PowerShell-Skript ausführen
.\generate-sample-db.ps1
```

**Manuell (alle Plattformen):**
```bash
# Beispieldatenbank generieren
dotnet run --project src/SampleDataGenerator

# Als aktive Datenbank verwenden
cp dienstplan-sample.db dienstplan.db  # Linux/macOS
# oder
Copy-Item dienstplan-sample.db dienstplan.db  # Windows
```

Siehe [docs/SAMPLE_DATA.md](docs/SAMPLE_DATA.md) für Details zu Beispieldaten und API-Aufrufen.

#### 4. Anwendung starten
```bash
dotnet run --project src/Dienstplan.Web
```

#### 5. Browser öffnen
Navigieren Sie zu: `http://localhost:5000` oder `https://localhost:5001`

### Binaries verwenden
1. Laden Sie die neueste Release-Version herunter
2. Entpacken Sie das Archiv
3. Führen Sie die ausführbare Datei aus:
   - **Windows**: `Dienstplan.Web.exe`
   - **Linux**: `./Dienstplan.Web`

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

#### Neuen Benutzer registrieren (nur Admin)
```http
POST /api/auth/register
Content-Type: application/json
Authorization: Required (Admin role)

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "fullName": "Max Mustermann",
  "role": "Mitarbeiter"
}
```

#### Passwort ändern
```http
POST /api/auth/change-password
Content-Type: application/json
Authorization: Required

{
  "currentPassword": "OldPass123!",
  "newPassword": "NewPass123!"
}
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
GET /api/shifts/schedule?startDate=2024-01-01&view=week
Authorization: Optional (öffentlich lesbar)
```
Parameter:
- `startDate`: Startdatum (ISO Format)
- `view`: week, month, oder year
- `endDate`: Optional, überschreibt view

#### Schichten automatisch planen
```http
POST /api/shifts/plan?startDate=2024-01-01&endDate=2024-01-31&force=false
Authorization: Required (Admin oder Disponent)
```

#### PDF-Export des Dienstplans
```http
GET /api/shifts/export/pdf?startDate=2024-01-01&endDate=2024-01-31
Authorization: Optional (öffentlich verfügbar)
```
Parameter:
- `startDate`: Startdatum (ISO Format)
- `endDate`: Enddatum (ISO Format)

Antwort: PDF-Datei zum Download

#### Excel-Export des Dienstplans 🆕
```http
GET /api/shifts/export/excel?startDate=2024-01-01&endDate=2024-01-31
Authorization: Optional (öffentlich verfügbar)
```
Parameter:
- `startDate`: Startdatum (ISO Format)
- `endDate`: Enddatum (ISO Format)

Antwort: Excel-Datei (.xlsx) mit formatiertem Dienstplan

Features:
- Farbcodierte Schichten (Früh=Gold, Spät=Tomato, Nacht=RoyalBlue, etc.)
- Wochenend-Highlighting (Samstag/Sonntag in Hellblau)
- Gruppierung nach Teams
- Springer-Kennzeichnung (Spr)
- Urlaub-Markierung (Ur in Rosa)
- Legende am Ende des Dokuments
- Automatische Spaltenbreiten und Zeilenhöhen

#### Springer zuweisen
```http
POST /api/shifts/springer/123?date=2024-01-15
Authorization: Required
```

### Statistik-Endpoints

#### Dashboard-Statistiken
```http
GET /api/statistics/dashboard?startDate=2024-01-01&endDate=2024-01-31
Authorization: Optional (öffentlich lesbar)
```

#### Wochenend-Schicht-Statistiken (Nur Disponent/Admin) 🆕
```http
GET /api/statistics/weekend-shifts?startDate=2024-01-01&endDate=2024-12-31
Authorization: Required (Admin oder Disponent)
```

Antwort:
```json
[
  {
    "employeeId": 1,
    "employeeName": "Max Mustermann",
    "saturdayShifts": 12,
    "sundayShifts": 10,
    "totalWeekendShifts": 22
  }
]
```

### Urlaubsantrags-Endpoints 🆕

#### Alle Urlaubsanträge abrufen (Admin/Disponent)
```http
GET /api/vacationrequests
Authorization: Required (Admin oder Disponent)
```

#### Urlaubsanträge eines Mitarbeiters
```http
GET /api/vacationrequests/employee/1
Authorization: Required
```

#### Offene Urlaubsanträge (Admin/Disponent)
```http
GET /api/vacationrequests/pending
Authorization: Required (Admin oder Disponent)
```

#### Urlaubsantrag erstellen
```http
POST /api/vacationrequests
Content-Type: application/json
Authorization: Required

{
  "employeeId": 1,
  "startDate": "2024-07-01",
  "endDate": "2024-07-14",
  "notes": "Sommerurlaub"
}
```

#### Urlaubsantrag-Status ändern (Admin/Disponent)
```http
PUT /api/vacationrequests/123/status
Content-Type: application/json
Authorization: Required (Admin oder Disponent)

{
  "status": "Genehmigt",
  "disponentResponse": "Viel Spaß im Urlaub!"
}
```

### Diensttausch-Endpoints 🆕

#### Verfügbare Tauschangebote
```http
GET /api/shiftexchanges/available
Authorization: Required
```

#### Tauschangebote eines Mitarbeiters
```http
GET /api/shiftexchanges/employee/1
Authorization: Required
```

#### Offene Tauschangebote (Admin/Disponent)
```http
GET /api/shiftexchanges/pending
Authorization: Required (Admin oder Disponent)
```

#### Dienst zum Tausch anbieten
```http
POST /api/shiftexchanges
Content-Type: application/json
Authorization: Required

{
  "shiftAssignmentId": 123,
  "offeringReason": "Familiäre Verpflichtung"
}
```

#### Dienst anfragen
```http
POST /api/shiftexchanges/123/request
Content-Type: application/json
Authorization: Required

{
  "requestingEmployeeId": 2
}
```

#### Diensttausch genehmigen/ablehnen (Admin/Disponent)
```http
PUT /api/shiftexchanges/123/process
Content-Type: application/json
Authorization: Required (Admin oder Disponent)

{
  "status": "Genehmigt",
  "disponentNotes": "Genehmigt, da keine Probleme mit der Besetzung"
}
```

### Abwesenheiten-Endpoints

#### Abwesenheiten abrufen
```http
GET /api/absences
Authorization: Optional (öffentlich lesbar)
```

#### Abwesenheit erfassen
```http
POST /api/absences
Content-Type: application/json
Authorization: Required (Admin oder Disponent)

{
  "employeeId": 1,
  "type": "Urlaub",
  "startDate": "2024-01-15",
  "endDate": "2024-01-20",
  "notes": "Jahresurlaub"
}
```

## 🔧 Konfiguration

### Datenbankverbindung
In `appsettings.json`:
```json
{
  "ConnectionStrings": {
    "DefaultConnection": "Data Source=dienstplan.db"
  }
}
```

### CORS-Einstellungen
Die API erlaubt standardmäßig alle Origins für Entwicklungszwecke. Für Produktion anpassen in `Program.cs`.

## 🧪 Tests

### Tests ausführen
```bash
dotnet test
```

### Test-Abdeckung
Die Lösung beinhaltet Testkategorien für:
- Unit-Tests der Business-Regeln
- Integration-Tests der API
- Repository-Tests

## 🔐 Sicherheit & Authentifizierung

### Implementiert
Version 1.1 implementiert vollständige Authentifizierung und Autorisierung mit ASP.NET Core Identity.

#### Rollenbasierte Autorisierung
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

#### Standard-Anmeldedaten
Bei der ersten Ausführung wird automatisch ein Administrator-Account erstellt:
- **E-Mail**: admin@fritzwinter.de
- **Passwort**: Admin123!

**WICHTIG**: Ändern Sie das Standard-Passwort nach der ersten Anmeldung!

#### Funktionen
- ✅ Cookie-basierte Authentifizierung
- ✅ Passwort-Hashing (ASP.NET Core Identity)
- ✅ Account-Sperrung nach fehlgeschlagenen Anmeldeversuchen (5 Versuche)
- ✅ Sichere Session-Verwaltung
- ✅ Passwort-Anforderungen: Mind. 8 Zeichen, Groß- und Kleinbuchstaben, Ziffer

### Sicherheitshinweise für Produktion
1. **Passwörter ändern**: Ändern Sie alle Standard-Passwörter
2. **HTTPS verwenden**: Aktivieren Sie HTTPS in der Produktion
3. **CORS konfigurieren**: Beschränken Sie erlaubte Origins in `Program.cs`
4. **Datenbank schützen**: SQLite-Datei vor unbefugtem Zugriff schützen
5. **Regular Updates**: Halten Sie alle NuGet-Pakete aktuell

## 📊 Datenmodell

### Hauptentitäten

**Employee (Mitarbeiter)**
- Id, Vorname, Name, Personalnummer
- IsSpringer (Boolean)
- TeamId (FK)

**Team**
- Id, Name, Description
- Employees (Collection)

**ShiftType (Schichtart)**
- Id, Code, Name
- StartTime, EndTime
- ColorCode

**ShiftAssignment (Schichtzuweisung)**
- Id, EmployeeId (FK), ShiftTypeId (FK)
- Date
- IsManual, IsSpringerAssignment, IsFixed 🆕
- CreatedBy, ModifiedBy, CreatedAt, ModifiedAt 🆕

**Absence (Abwesenheit)**
- Id, EmployeeId (FK)
- Type (Enum: Krank, Urlaub, Lehrgang)
- StartDate, EndDate

**VacationRequest (Urlaubsantrag)** 🆕
- Id, EmployeeId (FK)
- StartDate, EndDate
- Status (Enum: InBearbeitung, Genehmigt, NichtGenehmigt)
- Notes, DisponentResponse
- CreatedAt, UpdatedAt, ProcessedBy

**ShiftExchange (Diensttausch)** 🆕
- Id, OfferingEmployeeId (FK), RequestingEmployeeId (FK)
- ShiftAssignmentId (FK)
- Status (Enum: Angeboten, Angefragt, Genehmigt, Abgelehnt, Zurückgezogen, Abgeschlossen)
- OfferingReason, DisponentNotes
- CreatedAt, UpdatedAt, ProcessedBy

## 🔄 CI/CD Pipeline

Die GitHub Actions Workflow führt automatisch aus:

1. ✅ **Build**: Kompilierung aller Projekte
2. 🧪 **Tests**: Ausführung aller Unit- und Integration-Tests
3. 📦 **Publish**: Erstellung von Self-Contained Binaries
   - Windows (x64)
   - Linux (x64)
4. 📝 **Versioning**: Automatische Versionsnummern (1.0.Build-Nummer)
5. 🚀 **Release**: Veröffentlichung mit:
   - ZIP/TAR.GZ Archiven
   - Automatischem Changelog
   - Download-Anleitung

### Trigger
- **Push auf main**: Vollständiger Build + Release
- **Pull Request**: Nur Build + Tests

## 🛠️ Entwicklung

### Neue Schichtart hinzufügen
1. In `DienstplanDbContext.SeedShiftTypes()` neue Schicht definieren
2. Farbcode in CSS hinzufügen (`styles.css`)
3. Optional: Konstante in `ShiftTypeCodes` ergänzen

### Regel erweitern
Bearbeiten Sie `src/Dienstplan.Domain/Rules/ShiftRules.cs`:
- `ForbiddenTransitions`: Verbotene Wechsel
- `IdealRotation`: Gewünschte Reihenfolge
- Staffing-Anforderungen

### Beispieldaten für Entwicklung
Für schnelles Testen und Entwicklung steht ein Beispieldaten-Generator zur Verfügung:

```bash
# Linux/macOS
./generate-sample-db.sh

# Windows
.\generate-sample-db.ps1
```

**Generierte Daten:**
- 3 Teams (Alpha, Beta, Gamma)
- 17 Mitarbeiter (15 mit Team, 2 Sonderaufgaben)
- 4 Springer
- Administrator-Benutzer

Ausführliche Dokumentation: [docs/SAMPLE_DATA.md](docs/SAMPLE_DATA.md)

**Manuelle API-Aufrufe:**
Die Dokumentation enthält auch komplette Beispiele für Windows (PowerShell/curl) und Linux (bash/curl) zur Datenerzeugung über die REST API.

## 🤝 Beitragen

### Entwicklungsrichtlinien
- Clean Code Prinzipien beachten
- Unit-Tests für neue Features
- Dokumentation aktualisieren
- PR gegen `main` Branch

### Branch-Strategie
- `main`: Produktionsreifer Code
- Feature-Branches: `feature/beschreibung`
- Bugfix-Branches: `bugfix/beschreibung`

## 📄 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert - siehe [LICENSE](LICENSE) für Details.

## 🙋 Support & Kontakt

Bei Fragen oder Problemen:
- GitHub Issues: https://github.com/TimUx/Dienstplan/issues
- Dokumentation: Siehe diese README

## 🗺️ Roadmap

### Version 1.x
- [x] Grundlegende Mitarbeiterverwaltung
- [x] Automatische Schichtplanung
- [x] Web-Interface mit Dashboard
- [x] CI/CD Pipeline
- [x] **Authentifizierung & Autorisierung** ✅ **v1.1**
- [x] **PDF-Export von Dienstplänen** ✅ **v1.1**
- [x] **Urlaubsverwaltung mit Antrags-Workflow** ✅ **v1.2**
- [x] **Diensttausch-System** ✅ **v1.2**
- [x] **Erweiterte Mitarbeiterdaten** (Geburtsdatum, Funktion, Ferienjobber) ✅ **v1.2**
- [x] **Erweiterte Schichtplanungsregeln** (Max. 6 Schichten, Max. 3 Nachtschichten) ✅ **v1.2**
- [x] **Feste Dienste** (z.B. für Feiertage) ✅ **v1.2**
- [x] **Änderungsverfolgung** (Audit Trail) ✅ **v1.2**
- [x] **Wochenend-Statistiken** ✅ **v1.2**
- [x] **Spezielle Schichttypen** (Brandmeldetechniker, Brandschutzbeauftragter) ✅ **v1.2**
- [x] **E-Mail-Infrastruktur** (Mitarbeiter-E-Mails, SMTP-Konfiguration) ✅ **v1.2**
- [x] **Benachrichtigungs-Service** (Interface vorbereitet) ✅ **v1.2**
- [x] **Excel-Export (XLSX)** mit Formatierung wie Web-Ansicht ✅ **Neu in v1.3**
- [x] **Enhanced Springer-Management** (Verfügbarkeit garantiert, Workload-basiert) ✅ **Neu in v1.3**
- [x] **Fairness-Tracking** (Gerechte Verteilung, Stunden-Tracking) ✅ **Neu in v1.3**
- [x] **Automatische Zusatzfunktionen** (BMT/BSB mit Rotation) ✅ **Neu in v1.3**
- [x] **Qualifikationsverwaltung** (BMT/BSB) ✅ **Neu in v1.3**
- [x] **Monatsübergreifende Validierung** ✅ **Neu in v1.3**
- [x] **Flexible Skalierung** (beliebige Anzahl Mitarbeiter und Teams) ✅ **Neu in v1.3**
- [ ] E-Mail-Benachrichtigungen (SMTP-Integration mit MailKit)
- [ ] Mobile App (React Native)

### Version 2.x
- [ ] Wunschschichten
- [ ] Urlaubssperren
- [ ] Zeiterfassung Integration
- [ ] Multi-Mandanten-Fähigkeit
- [ ] Erweiterte Berichte und Analytics
- [ ] Real-Time Benachrichtigungen (WebSockets)

---

**Version 1.3** | Entwickelt von **Timo Braun** mit ❤️ für effiziente Schichtverwaltung

© 2025 Fritz Winter Eisengießerei GmbH & Co. KG
