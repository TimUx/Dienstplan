# Beispieldaten – Mitarbeiter & Teams

Dieses Verzeichnis enthält Beispiel-CSV-Dateien, die so formatiert sind wie ein Export aus der Dienstplan-App.
Sie dienen dazu, die App schnell mit Testdaten zu befüllen.

## Dateien

| Datei | Inhalt |
|---|---|
| `teams_export_beispiel.csv` | 3 Teams (Team 1, 2, 3) |
| `mitarbeiter_export_beispiel.csv` | 15 Mitarbeiter (je 5 pro Team) |

## Importreihenfolge

> **Wichtig:** Teams müssen **zuerst** importiert werden, da die Mitarbeiter-CSV auf
> die automatisch vergebenen Team-IDs verweist.

1. **Teams importieren** – `teams_export_beispiel.csv`  
   Die App vergibt dabei die IDs 1, 2, 3 (in der Reihenfolge der Zeilen).

2. **Mitarbeiter importieren** – `mitarbeiter_export_beispiel.csv`  
   Die Spalte `TeamId` in der Mitarbeiter-Datei verweist auf diese IDs.

## Import in der App

1. Anmelden als **Admin**.
2. Navigieren zu **Verwaltung → Mitarbeiter & Teams**.
3. Tab **Teams** öffnen → **Importieren** → `teams_export_beispiel.csv` hochladen.
4. Tab **Mitarbeiter** öffnen → **Importieren** → `mitarbeiter_export_beispiel.csv` hochladen.

## Datenübersicht

### Teams
| ID | Name | Beschreibung |
|----|------|-------------|
| 1 | Team 1 | Erste Schichtgruppe |
| 2 | Team 2 | Zweite Schichtgruppe |
| 3 | Team 3 | Dritte Schichtgruppe |

### Mitarbeiter

| PersonalNr | Vorname | Name | Team | Funktion |
|---|---|---|---|---|
| PN001 | Max | Müller | Team 1 | Mitarbeiter |
| PN002 | Anna | Schmidt | Team 1 | Mitarbeiter |
| PN003 | Peter | Weber | Team 1 | Mitarbeiter |
| PN004 | Lisa | Meyer | Team 1 | Mitarbeiter |
| PN005 | Robert | Franke | Team 1 | Mitarbeiter |
| PN006 | Julia | Becker | Team 2 | Mitarbeiter |
| PN007 | Michael | Schulz | Team 2 | Mitarbeiter |
| PN008 | Sarah | Hoffmann | Team 2 | Mitarbeiter |
| PN009 | Daniel | Koch | Team 2 | Mitarbeiter |
| PN010 | Thomas | Zimmermann | Team 2 | Mitarbeiter |
| PN011 | Markus | Richter | Team 3 | Mitarbeiter |
| PN012 | Stefanie | Klein | Team 3 | Mitarbeiter |
| PN013 | Andreas | Wolf | Team 3 | Mitarbeiter |
| PN014 | Nicole | Schröder | Team 3 | Mitarbeiter |
| PN015 | Maria | Lange | Team 3 | Mitarbeiter |
