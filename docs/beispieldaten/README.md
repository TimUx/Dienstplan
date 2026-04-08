# Beispieldaten – Mitarbeiter & Teams

Dieses Verzeichnis enthält Beispiel-CSV-Dateien, die so formatiert sind wie ein Export aus der Dienstplan-App.
Sie dienen dazu, die App schnell mit Testdaten zu befüllen.

## Dateien

| Datei | Inhalt |
|---|---|
| `teams_export_beispiel.csv` | 3 Teams (Wache 1, 2, 3) |
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
| 1 | Wache 1 | Feuerwehr Wache 1 – Früh- und Spätdienst |
| 2 | Wache 2 | Feuerwehr Wache 2 – Früh- und Spätdienst |
| 3 | Wache 3 | Feuerwehr Wache 3 – Früh- und Spätdienst |

### Mitarbeiter

| PersonalNr | Vorname | Name | Team | Funktion | Teamleiter | BMT | BSB | TD |
|---|---|---|---|---|---|---|---|---|
| PN001 | Max | Müller | Wache 1 | Brandmeister | ✓ | | | |
| PN002 | Anna | Schmidt | Wache 1 | Oberbrandmeister | | | | |
| PN003 | Peter | Weber | Wache 1 | Hauptbrandmeister | | ✓ | | ✓ |
| PN004 | Lisa | Meyer | Wache 1 | Brandmeister | | | | |
| PN005 | Robert | Franke | Wache 1 | Oberbrandmeister | | | ✓ | ✓ |
| PN006 | Julia | Becker | Wache 2 | Hauptbrandmeister | ✓ | | | |
| PN007 | Michael | Schulz | Wache 2 | Brandmeister | | | | |
| PN008 | Sarah | Hoffmann | Wache 2 | Oberbrandmeister | | ✓ | | ✓ |
| PN009 | Daniel | Koch | Wache 2 | Brandmeister | | | | |
| PN010 | Thomas | Zimmermann | Wache 2 | Hauptbrandmeister | | | | |
| PN011 | Markus | Richter | Wache 3 | Hauptbrandmeister | ✓ | | | |
| PN012 | Stefanie | Klein | Wache 3 | Brandmeister | | | | |
| PN013 | Andreas | Wolf | Wache 3 | Oberbrandmeister | | ✓ | | ✓ |
| PN014 | Nicole | Schröder | Wache 3 | Brandmeister | | | | |
| PN015 | Maria | Lange | Wache 3 | Oberbrandmeister | | | ✓ | ✓ |
