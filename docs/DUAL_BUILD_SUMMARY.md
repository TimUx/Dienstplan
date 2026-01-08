# Dual-Build Implementation Summary

## Overview

Das Build-System wurde erweitert, um **zwei verschiedene Versionen** der Dienstplan-Anwendung zu erstellen:

1. **Empty Version (Produktionsversion)** - Leere Datenbank für den produktiven Einsatz
2. **SampleData Version (Demo-Version)** - Mit Beispieldaten für Tests und Demonstrationen

## Was hat sich geändert?

### GitHub Actions Workflow

Der automatische Build-Prozess erstellt jetzt **4 separate Executables**:

- ✅ `Dienstplan-Windows-Empty-v2.1.x.zip` - Windows Produktionsversion
- ✅ `Dienstplan-Windows-SampleData-v2.1.x.zip` - Windows Demo-Version
- ✅ `Dienstplan-Linux-Empty-v2.1.x.tar.gz` - Linux Produktionsversion
- ✅ `Dienstplan-Linux-SampleData-v2.1.x.tar.gz` - Linux Demo-Version

### Neue Build-Skripte

Zum lokalen Erstellen beider Versionen auf einmal:

**Windows:**
```cmd
build_windows_both.bat
```
Erstellt:
- `Dienstplan-Windows-Empty.zip`
- `Dienstplan-Windows-SampleData.zip`

**Linux:**
```bash
./build_executable_both.sh
```
Erstellt:
- `Dienstplan-Linux-Empty.tar.gz`
- `Dienstplan-Linux-SampleData.tar.gz`

### Bestehende Skripte

Die ursprünglichen Build-Skripte funktionieren weiterhin für einzelne Builds:

```cmd
REM Windows - leere Datenbank
build_windows.bat

REM Windows - mit Beispieldaten
build_windows.bat --sample-data
```

```bash
# Linux - leere Datenbank
./build_executable.sh

# Linux - mit Beispieldaten
./build_executable.sh --sample-data
```

## Versionsvergleich

### Empty Version (Produktionsversion)

**Enthält:**
- ✅ Datenbank-Schema (alle Tabellen und Indizes)
- ✅ Standard-Rollen (Admin, Mitarbeiter)
- ✅ Admin-Benutzer (admin@fritzwinter.de)
- ✅ Standard-Schichttypen (F, S, N)
- ❌ Keine Teams
- ❌ Keine Mitarbeiter (außer Admin)
- ❌ Keine virtuellen Teams

**Verwendungszweck:**
Für den produktiven Einsatz mit eigenen Daten. Die Datenbank ist bereit für die erste Inbetriebnahme mit Ihren Teams und Mitarbeitern.

### SampleData Version (Demo-Version)

**Enthält alles aus der Empty Version, plus:**
- ✅ 3 Teams (Alpha, Beta, Gamma)
- ✅ 17 Mitarbeiter mit verschiedenen Qualifikationen
- ✅ Beispiel-Abwesenheiten
- ✅ 3 Springer
- ✅ 2 Mitarbeiter mit Spezialfunktionen (BMT/BSB)
- ❌ **Kein virtuelles Ferienjobber-Team** (entfernt)

**Verwendungszweck:**
Für Tests, Schulungen und Demonstrationen. Sie können die Funktionen sofort testen, ohne erst Daten eingeben zu müssen.

## Wichtige Änderungen

### Virtuelle Teams entfernt

Das virtuelle Ferienjobber-Team wird **nicht mehr erstellt**:
- Alle Teams in den Beispieldaten sind reale Teams (`IsVirtual=0`)
- Die Sample-Datenbank enthält nur die 3 Teams: Alpha, Beta, Gamma
- Ferienjobber können bei Bedarf einem eigenen Team zugewiesen werden

### Mitarbeiter-Verteilung

**Empty Version:**
- 1 Mitarbeiter (Admin)

**SampleData Version:**
- 18 Mitarbeiter gesamt:
  - 1 Admin (ohne Team)
  - 5 Mitarbeiter in Team Alpha (davon 1 Springer)
  - 5 Mitarbeiter in Team Beta (davon 1 Springer)
  - 5 Mitarbeiter in Team Gamma (davon 1 Springer)
  - 2 Mitarbeiter ohne Team (mit Spezialfunktionen BMT/BSB)

## Welche Version soll ich wählen?

### Für Produktion → Empty Version

Wählen Sie die **Empty Version**, wenn:
- Sie das System zum ersten Mal produktiv einsetzen
- Sie Ihre eigenen Teams und Mitarbeiter anlegen möchten
- Sie eine "saubere" Datenbank ohne Beispieldaten benötigen

### Für Tests/Demo → SampleData Version

Wählen Sie die **SampleData Version**, wenn:
- Sie das System erst einmal testen möchten
- Sie eine Demonstration für Kollegen vorbereiten
- Sie die Funktionen erkunden möchten, ohne Daten eingeben zu müssen
- Sie Schulungen durchführen

## Download

Laden Sie die gewünschte Version von den [GitHub Releases](https://github.com/TimUx/Dienstplan/releases) herunter.

## Standard-Anmeldung (beide Versionen)

```
E-Mail: admin@fritzwinter.de
Passwort: Admin123!
```

⚠️ **WICHTIG**: Ändern Sie das Passwort nach der ersten Anmeldung!

## Technische Details

### Datenbank-Initialisierung

```bash
# Empty (Produktion)
python db_init.py data/dienstplan.db

# SampleData (Demo)
python db_init.py data/dienstplan.db --with-sample-data
```

### Release-Struktur

Beide Versionen enthalten:
- `Dienstplan.exe` (Windows) oder `Dienstplan` (Linux)
- `data/dienstplan.db` (vorkonfigurierte Datenbank)
- `README.md`
- `LICENSE`
- `VERSION.txt` (beschreibt die Version)

### Persistenz

Die Datenbank ist in beiden Versionen persistent:
- Speicherort: `data/dienstplan.db`
- Alle Änderungen werden gespeichert
- Zum Zurücksetzen: `data/` Ordner löschen und Anwendung neu starten

## Weitere Informationen

- **Vollständige Dokumentation**: Siehe [README.md](../README.md)
- **Build-Anleitung**: Siehe [BUILD_GUIDE.md](BUILD_GUIDE.md)
- **Schnellstart**: Siehe [QUICKSTART.md](QUICKSTART.md)
