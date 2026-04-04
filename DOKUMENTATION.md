# 📚 Dienstplan - Zentrale Dokumentationsübersicht

**Version 2.1 - Python Edition** | Entwickelt von Timo Braun

Willkommen zur zentralen Dokumentation des Dienstplan-Systems.

---

## 🎯 Schnelleinstieg

Neu im System? Starten Sie hier:

1. **[Installationsanleitung](docs/INSTALLATION.md)** – Native Python, 1-Klick-EXE oder Docker
2. **[Benutzerhandbuch](BENUTZERHANDBUCH.md)** – Umfassende Anleitung für alle Funktionen
3. **[README](README.md)** – Projekt-Übersicht und Feature-Liste

---

## 📖 Dokumentationskategorien

### Für Endbenutzer

| Dokument | Beschreibung | Zielgruppe |
|----------|--------------|------------|
| **[Installationsanleitung](docs/INSTALLATION.md)** | Native Python, 1-Klick-EXE, Docker Compose | Alle Benutzer |
| **[Benutzerhandbuch](BENUTZERHANDBUCH.md)** | Vollständige Anleitung mit Screenshots | Alle Benutzer |
| **[Schnellstart](docs/QUICKSTART.md)** | Installation und erste Schritte (EN) | Neue Benutzer |
| **[Windows Standalone](docs/WINDOWS_EXECUTABLE.md)** | Anleitung für die Windows-Exe | Windows-Nutzer |

### Für Administratoren

| Dokument | Beschreibung | Zielgruppe |
|----------|--------------|------------|
| **[Schichtplanungs-Regeln (DE)](docs/SCHICHTPLANUNG_REGELN.md)** | ⭐ Alle Regeln, Abhängigkeiten & Prioritäten | Admins |
| **[Shift Planning Rules (EN)](docs/SHIFT_PLANNING_RULES_EN.md)** | ⭐ All rules, dependencies & priorities | Admins |
| **[Nutzungsanleitung](docs/USAGE_GUIDE.md)** | CLI-Befehle und API-Nutzung | Admins |
| **[Schichtplanungsalgorithmus](docs/SHIFT_PLANNING_ALGORITHM.md)** | Details zum OR-Tools Solver | Admins |
| **[Beispieldaten](docs/SAMPLE_DATA.md)** | Testdaten und API-Beispiele | Admins, Entwickler |

### Für Entwickler

| Dokument | Beschreibung | Zielgruppe |
|----------|--------------|------------|
| **[Architektur](ARCHITECTURE.md)** | System-Design und Komponenten | Entwickler |
| **[Build-Anleitung](docs/BUILD_GUIDE.md)** | Executable erstellen | Entwickler |
| **[Migration](MIGRATION.md)** | .NET zu Python Migration + DB-Migrationen | Entwickler |
| **[Changelog](CHANGELOG.md)** | Versionshistorie | Alle |

---

## 🚀 Nach Anwendungsfall

### Sie möchten...

#### ...das System zum ersten Mal installieren?
→ **[Installationsanleitung](docs/INSTALLATION.md)**

#### ...das System als Mitarbeiter nutzen?
→ **[Benutzerhandbuch](BENUTZERHANDBUCH.md)**

#### ...Schichten planen als Administrator?
→ **[Benutzerhandbuch – Schichtplanung](BENUTZERHANDBUCH.md#9-schichtplanung)**

#### ...alle Planungsregeln verstehen?
→ **[Schichtplanungs-Regeln (DE)](docs/SCHICHTPLANUNG_REGELN.md)** · **[EN](docs/SHIFT_PLANNING_RULES_EN.md)**

#### ...die API nutzen?
→ **[README – API-Dokumentation](README.md#-api-dokumentation)**

#### ...eine Executable erstellen?
→ **[Build-Anleitung](docs/BUILD_GUIDE.md)**

#### ...das System erweitern oder anpassen?
→ **[Architektur](ARCHITECTURE.md)** + **[Entwicklung](README.md#-entwicklung)**

---

## 🔧 Konfiguration und Einstellungen

### Datenbank
- Standard: `dienstplan.db` im aktuellen Verzeichnis
- Ändern mit: `--db /pfad/zur/datenbank.db`

### Webserver
- Standard: `http://localhost:5000`
- Anpassen: `python main.py serve --host 0.0.0.0 --port 8080`

### Solver-Parameter
- Zeitlimit: Standardmäßig 300 Sekunden
- Worker: 8 parallele Threads
- Details: [SHIFT_PLANNING_ALGORITHM.md](docs/SHIFT_PLANNING_ALGORITHM.md)

---

## 🆘 Hilfe und Support

### Häufige Probleme

| Problem | Lösung |
|---------|--------|
| Datenbank-Fehler beim Start | `python main.py init-db --with-sample-data` |
| Port bereits belegt | `python main.py serve --port 8080` |
| Login funktioniert nicht | E-Mail: `admin@fritzwinter.de` / PW: `Admin123!` |
| Keine optimale Lösung | `python main.py plan --time-limit 600` |

Weitere Hilfe: [BENUTZERHANDBUCH – Fehlerbehebung](BENUTZERHANDBUCH.md#fehlerbehebung)

---

## 🗺️ Dokumentationsstruktur

```
Dienstplan/
├── README.md                         # Projekt-Übersicht, Features, API
├── DOKUMENTATION.md                  # Diese Datei – Zentrale Übersicht
├── BENUTZERHANDBUCH.md              # Vollständiges Benutzerhandbuch (DE)
├── ARCHITECTURE.md                   # System-Architektur
├── CHANGELOG.md                      # Versionshistorie
├── MIGRATION.md                      # Migration .NET→Python + DB-Migrationen
├── LICENSE                           # MIT-Lizenz
├── Dockerfile                        # Docker-Image-Definition
├── docker-compose.yml               # Docker Compose Konfiguration
│
└── docs/
    ├── INSTALLATION.md              # ⭐ Installationsanleitung (alle Methoden)
    ├── QUICKSTART.md                # Schnellstart (EN)
    ├── USAGE_GUIDE.md               # CLI und API Nutzung
    ├── BUILD_GUIDE.md               # Executable erstellen
    ├── WINDOWS_EXECUTABLE.md        # Windows-Standalone-Anleitung
    ├── SHIFT_PLANNING_ALGORITHM.md  # Algorithmus-Details
    ├── SCHICHTPLANUNG_REGELN.md     # Planungsregeln (DE)
    ├── SHIFT_PLANNING_RULES_EN.md   # Planungsregeln (EN)
    ├── SAMPLE_DATA.md               # Testdaten und Beispiele
    ├── SYSTEM_UEBERSICHT.md         # Systemübersicht
    ├── SYSTEM_DIAGRAMME.md          # Visuelle Diagramme
    ├── SHIFT_GROUPING_CONSTRAINT.md # Shift-Sequenz-Constraint
    └── screenshots/                  # Alle Screenshots
```

---

## 📄 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert – siehe [LICENSE](LICENSE) für Details.

---

## 🔗 Links

- **GitHub Repository**: https://github.com/TimUx/Dienstplan
- **Issues & Support**: https://github.com/TimUx/Dienstplan/issues
- **Releases**: https://github.com/TimUx/Dienstplan/releases

---

**Version 2.1 - Python Edition** | Entwickelt von **Timo Braun** mit ❤️ | Powered by **Google OR-Tools**

© 2025 Fritz Winter Eisengießerei GmbH & Co. KG
