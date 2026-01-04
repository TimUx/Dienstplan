# 📚 Dienstplan - Zentrale Dokumentationsübersicht

**Version 2.0 - Python Edition** | Entwickelt von Timo Braun

Willkommen zur zentralen Dokumentation des Dienstplan-Systems. Diese Seite bietet einen strukturierten Überblick über alle verfügbaren Dokumentationen.

---

## 🎯 Schnelleinstieg

Neu im System? Starten Sie hier:

1. **[Schnellstart-Anleitung](docs/QUICKSTART.md)** - In 5 Minuten produktiv
2. **[Benutzerhandbuch](BENUTZERHANDBUCH.md)** - Umfassende Anleitung für alle Funktionen
3. **[README](README.md)** - Projekt-Übersicht und Feature-Liste

---

## 📖 Dokumentationskategorien

### Für Endbenutzer

| Dokument | Beschreibung | Zielgruppe |
|----------|--------------|------------|
| **[Benutzerhandbuch](BENUTZERHANDBUCH.md)** | Vollständige Anleitung mit Screenshots und Beispielen | Alle Benutzer |
| **[Schnellstart](docs/QUICKSTART.md)** | Installation und erste Schritte | Neue Benutzer |
| **[Windows Standalone](docs/WINDOWS_EXECUTABLE.md)** | Anleitung für die Windows-Exe | Windows-Nutzer |

### Für Administratoren

| Dokument | Beschreibung | Zielgruppe |
|----------|--------------|------------|
| **[Nutzungsanleitung](docs/USAGE_GUIDE.md)** | CLI-Befehle und API-Nutzung | Admins |
| **[Schichtplanungsalgorithmus](docs/SHIFT_PLANNING_ALGORITHM.md)** | Details zum OR-Tools Solver | Admins |
| **[Beispieldaten](docs/SAMPLE_DATA.md)** | Testdaten und API-Beispiele | Admins, Entwickler |
| **[Mehrfachauswahl-Anleitung](MEHRFACHAUSWAHL_ANLEITUNG.md)** | Multi-Select Schichtbearbeitung | Admins |

### Für Entwickler

| Dokument | Beschreibung | Zielgruppe |
|----------|--------------|------------|
| **[Architektur](ARCHITECTURE.md)** | System-Design und Komponenten | Entwickler |
| **[Build-Anleitung](docs/BUILD_GUIDE.md)** | Executable erstellen | Entwickler |
| **[Migration](MIGRATION.md)** | .NET zu Python Migration | Entwickler |
| **[Changelog](CHANGELOG.md)** | Versionshistorie | Alle |

---

## 🚀 Nach Anwendungsfall

### Sie möchten...

#### ...das System zum ersten Mal installieren?
→ **[Schnellstart-Anleitung](docs/QUICKSTART.md)**

#### ...das System als Mitarbeiter nutzen?
→ **[Benutzerhandbuch - Für Mitarbeiter](BENUTZERHANDBUCH.md#für-mitarbeiter)**

#### ...Schichten planen als Administrator?
→ **[Benutzerhandbuch - Schichtplanung](BENUTZERHANDBUCH.md#9-schichtplanung)**

#### ...das System administrieren?
→ **[Benutzerhandbuch - Administration](BENUTZERHANDBUCH.md#administration)**

#### ...die API nutzen?
→ **[README - API-Dokumentation](README.md#-api-dokumentation)**

#### ...eine Windows-Exe erstellen?
→ **[Build-Anleitung](docs/BUILD_GUIDE.md)**

#### ...das System erweitern oder anpassen?
→ **[Architektur](ARCHITECTURE.md)** + **[Entwicklung](README.md#-entwicklung)**

---

## 📸 Screenshots und Beispiele

Alle Screenshots befinden sich im Verzeichnis `docs/screenshots/`:

**Existierende Screenshots:**
- **Anmeldung**: `00-login-modal.png`
- **Hauptansicht**: `00-main-view.png`
- **Dienstplan-Ansichten**: `03-schedule-week-admin.png`, `04-schedule-month-admin.png`, `05-schedule-year-admin.png`
- **Mitarbeiterverwaltung**: `06-employees-list.png`
- **Urlaubsverwaltung**: `07-vacation-requests.png`
- **Diensttausch**: `08-shift-exchange.png`
- **Statistiken**: `09-statistics.png`
- **Hilfe-System**: `10-help-manual.png`
- **Administration**: `11-admin-panel.png`
- **Schichtverwaltung**: `12-shift-management.png` - Dynamische Schichttypen-Verwaltung ✅
- **Schichttyp bearbeiten**: `13-shift-type-edit.png` - Bearbeitungsformular ✅
- **Team-Zuordnung**: `14-shift-team-assignment.png` - Teams zu Schichten zuweisen ✅
- **Mehrfachauswahl**: `15-multi-select-active.png` - Multi-Select für Schichten ✅
- **Bearbeitungsdialog**: `16-multi-select-edit-dialog.png` - Massenbearbeitung ✅
- **Jahresurlaubsplan**: `17-vacation-year-plan.png` - Jahresübersicht Urlaube ✅
- **Teamverwaltung**: `18-team-management.png` - Team-Übersicht ✅

---

## 🔧 Konfiguration und Einstellungen

### Datenbank
- Standard: `dienstplan.db` im aktuellen Verzeichnis
- Ändern mit: `--db /pfad/zur/datenbank.db`
- Siehe: [QUICKSTART - Datenbank](docs/QUICKSTART.md#database-location)

### Webserver
- Standard: `http://localhost:5000`
- Anpassen: `python main.py serve --host 0.0.0.0 --port 8080`
- Siehe: [USAGE_GUIDE - Server](docs/USAGE_GUIDE.md#1-web-server-starten)

### Solver-Parameter
- Zeitlimit: Standardmäßig 300 Sekunden
- Worker: 8 parallele Threads
- Details: [SHIFT_PLANNING_ALGORITHM.md](docs/SHIFT_PLANNING_ALGORITHM.md)

---

## 🆘 Hilfe und Support

### Häufige Probleme

**Datenbank-Fehler beim Start?**
→ Initialisieren Sie die Datenbank: `python main.py init-db --with-sample-data`

**Port bereits belegt?**
→ Anderen Port verwenden: `python main.py serve --port 8080`

**Login funktioniert nicht?**
→ Standard-Anmeldedaten: `admin@fritzwinter.de` / `Admin123!`

**Keine optimale Lösung gefunden?**
→ Zeitlimit erhöhen: `python main.py plan --time-limit 600`

Weitere Hilfe: [BENUTZERHANDBUCH - Fehlerbehebung](BENUTZERHANDBUCH.md#fehlerbehebung)

---

## 🗺️ Dokumentationsstruktur (Verzeichnisbaum)

```
Dienstplan/
├── README.md                          # Projekt-Übersicht, Features, Installation
├── DOKUMENTATION.md                   # Diese Datei - Zentrale Übersicht
├── BENUTZERHANDBUCH.md               # Vollständiges Benutzerhandbuch
├── ARCHITECTURE.md                    # System-Architektur
├── CHANGELOG.md                       # Versionshistorie
├── MIGRATION.md                       # Migration von .NET zu Python
├── LICENSE                            # MIT-Lizenz
│
├── docs/                              # Detaillierte Dokumentation
│   ├── QUICKSTART.md                 # Schnellstart in 5 Minuten
│   ├── USAGE_GUIDE.md                # CLI und API Nutzung
│   ├── BUILD_GUIDE.md                # Executable erstellen
│   ├── WINDOWS_EXECUTABLE.md         # Windows-Standalone-Anleitung
│   ├── SHIFT_PLANNING_ALGORITHM.md   # Algorithmus-Details
│   ├── SAMPLE_DATA.md                # Testdaten und Beispiele
│   └── screenshots/                   # Alle Screenshots
│       ├── 00-login-modal.png
│       ├── 03-schedule-week-admin.png
│       └── ...
│
├── wwwroot/                           # Web-UI (HTML/CSS/JS)
├── data/                              # Datenbank-Verzeichnis
└── [Python-Dateien]                   # Backend-Code
```

---

## 📝 Dokumentation beitragen

Haben Sie Verbesserungsvorschläge für die Dokumentation?

1. Erstellen Sie ein Issue auf GitHub
2. Schlagen Sie Änderungen per Pull Request vor
3. Kontaktieren Sie das Entwicklerteam

**Dokumentations-Richtlinien:**
- Klare, verständliche Sprache
- Praxisnahe Beispiele
- Screenshots für UI-Funktionen
- Code-Beispiele mit Erklärungen
- Markdown-Formatierung

---

## 📄 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert - siehe [LICENSE](LICENSE) für Details.

---

## 🔗 Weiterführende Links

- **GitHub Repository**: https://github.com/TimUx/Dienstplan
- **Issues & Support**: https://github.com/TimUx/Dienstplan/issues
- **Releases**: https://github.com/TimUx/Dienstplan/releases

---

**Version 2.0 - Python Edition**

Entwickelt von **Timo Braun** mit ❤️ für effiziente Schichtverwaltung

Powered by **Google OR-Tools**

© 2025 Fritz Winter Eisengießerei GmbH & Co. KG
