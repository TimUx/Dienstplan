# Dienstplan - Automatisches Schichtverwaltungssystem

Ein vollständiges System zur Verwaltung und automatischen Planung von Schichtdiensten für 15 Mitarbeiter in 3 Teams.

## 🎯 Funktionsumfang

### Mitarbeiterverwaltung
- **Pflichtfelder**: Vorname, Name, Personalnummer
- **Teamzuordnung**: Mitarbeiter können Teams zugeordnet werden
- **Springer-System**: Markierung von Backup-Mitarbeitern für automatische Vertretung bei Ausfällen
- **Abwesenheiten**: Verwaltung von Krank, Urlaub, Lehrgang

### Schichtarten
- **Früh**: 05:45–13:45 Uhr
- **Spät**: 13:45–21:45 Uhr
- **Nacht**: 21:45–05:45 Uhr
- **Zwischendienst**: 08:00–16:00 Uhr
- **Zusatzkürzel**: Flexibel erweiterbar (z.B. SRHT)

### Schichtbesetzung
**Montag–Freitag:**
- Früh: 4–5 Personen
- Spät: 3–4 Personen
- Nacht: 3 Personen

**Wochenende:**
- Alle Schichten: max. 3 Personen

### Automatische Schichtplanung
Das System beachtet folgende Regeln:
- ✅ Nicht zweimal hintereinander dieselbe Schicht
- 🚫 Verbotene Wechsel: Spät → Früh, Nacht → Spät
- ⏰ Gesetzliche Ruhezeiten (11 Stunden Minimum)
- ⚖️ Gleichmäßige Verteilung über alle Mitarbeiter
- 🔄 Idealer Rhythmus: Früh → Nacht → Spät
- 🔧 Manuelle Änderungen jederzeit möglich
- 🆘 Automatischer Springer-Einsatz bei Ausfällen

### Dashboard & Statistiken
- 📊 Arbeitsstunden pro Mitarbeiter
- 📈 Schichtverteilung pro Team
- 📅 Fehltageübersicht
- 💼 Team-Workload Analyse

### PDF-Export
- 📄 Professionelle PDF-Generierung von Dienstplänen
- 🎨 Farbcodierte Schichtarten für bessere Übersichtlichkeit
- 📋 Zusammenfassung mit Schichtanzahl pro Typ
- 📅 Flexible Zeitraumauswahl (Woche, Monat, Jahr)

### Web-Schnittstelle
- 📱 Responsive Design (Desktop & Smartphone)
- 📆 Ansichten: Woche, Monat, Jahr
- 🔐 Authentifizierung und Autorisierung
- 👀 Lesezugriff für alle Mitarbeiter
- ⚡ Performante REST API

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

#### 3. Anwendung starten
```bash
dotnet run --project src/Dienstplan.Web
```

#### 4. Browser öffnen
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
- IsManual, IsSpringerAssignment

**Absence (Abwesenheit)**
- Id, EmployeeId (FK)
- Type (Enum: Krank, Urlaub, Lehrgang)
- StartDate, EndDate

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
- [x] **Authentifizierung & Autorisierung** ✅ **Neu in v1.1**
- [x] **PDF-Export von Dienstplänen** ✅ **Neu in v1.1**
- [ ] E-Mail-Benachrichtigungen
- [ ] Mobile App (React Native)

### Version 2.x
- [ ] Erweiterte Regeln (Urlaubssperren, Wunschschichten)
- [ ] Schichtmarktplatz (Schichttausch)
- [ ] Zeiterfassung Integration
- [ ] Multi-Mandanten-Fähigkeit
- [ ] Erweiterte Berichte und Analytics

---

**Entwickelt mit ❤️ für effiziente Schichtverwaltung**
