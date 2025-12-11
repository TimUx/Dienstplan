# Screenshot-Anleitung / Screenshot Guide

Diese Anleitung beschreibt, wie Sie Screenshots für die Dokumentation erstellen.

## Vorbereitung

### 1. Testdaten laden

Die Anwendung startet standardmäßig mit einer leeren Datenbank (nur Admin-Benutzer und Rollen).

Für Screenshots müssen temporäre Testdaten geladen werden:

```bash
cd src/Dienstplan.Web

# Datenbank löschen (falls vorhanden)
rm -f dienstplan.db*

# Anwendung starten, um Schema zu erstellen
dotnet run --urls "http://localhost:5000"
# Warten bis "Application started" erscheint, dann mit Ctrl+C beenden

# Testdaten importieren
sqlite3 dienstplan.db < ../../docs/screenshot-test-data.sql
```

### 2. Anwendung starten

```bash
cd src/Dienstplan.Web
dotnet run --urls "http://localhost:5000"
```

Öffnen Sie http://localhost:5000 im Browser.

### 3. Anmeldung

**Standard-Admin-Zugangsdaten:**
- E-Mail: admin@fritzwinter.de
- Passwort: Admin123!

## Screenshots erstellen

### Benötigte Screenshots

#### 1. Hauptansicht - Dienstplan
- **Datei**: `screenshot-01-schedule-week.png`
- **Ansicht**: Wochenansicht mit Beispieldaten (KW 50, 9.-15. Dez. 2025)
- **Inhalt**: Vollständiger Dienstplan mit allen Schichten und Mitarbeitern

#### 2. Hauptansicht - Dienstplan Monatsansicht
- **Datei**: `screenshot-02-schedule-month.png`
- **Ansicht**: Monatsansicht Dezember 2025
- **Inhalt**: Monatliche Übersicht der Schichtplanung

#### 3. Login-Dialog
- **Datei**: `screenshot-03-login.png`
- **Ansicht**: Anmeldedialog vor dem Einloggen
- **Inhalt**: Modal mit E-Mail/Passwort-Feldern

#### 4. Mitarbeiterverwaltung
- **Datei**: `screenshot-04-employees.png`
- **Ansicht**: Mitarbeiterübersicht nach dem Login als Admin
- **Inhalt**: Liste aller 17 Mitarbeiter mit Details

#### 5. Mitarbeiter-Formular
- **Datei**: `screenshot-05-employee-form.png`
- **Ansicht**: Dialog zum Hinzufügen/Bearbeiten eines Mitarbeiters
- **Inhalt**: Formular mit allen Feldern (Name, E-Mail, Geburtsdatum, Funktion, Team, etc.)

#### 6. Teams-Verwaltung
- **Datei**: `screenshot-06-teams.png`
- **Ansicht**: Teamübersicht
- **Inhalt**: Grid mit 3 Teams (Alpha, Beta, Gamma)

#### 7. Urlaubsverwaltung - Urlaubsanträge
- **Datei**: `screenshot-07-vacation-requests.png`
- **Ansicht**: Urlaub-Tab mit Urlaubsanträgen
- **Inhalt**: Tabelle mit Anträgen und verschiedenen Status

#### 8. Urlaubsverwaltung - Diensttausch
- **Datei**: `screenshot-08-shift-exchanges.png`
- **Ansicht**: Diensttausch-Tab
- **Inhalt**: Liste der Tauschangebote

#### 9. Statistiken
- **Datei**: `screenshot-09-statistics.png`
- **Ansicht**: Statistikübersicht
- **Inhalt**: Arbeitsstunden, Schichtverteilung, Team-Auslastung

#### 10. Admin-Panel - Übersicht
- **Datei**: `screenshot-10-admin-overview.png`
- **Ansicht**: Admin-Panel mit allen Sektionen
- **Inhalt**: Benutzerverwaltung, E-Mail-Einstellungen, Globale Einstellungen, System-Info

#### 11. Admin - E-Mail-Einstellungen
- **Datei**: `screenshot-11-admin-email-settings.png`
- **Ansicht**: E-Mail-Einstellungen Detail
- **Inhalt**: Aktive SMTP-Konfiguration

#### 12. Admin - Globale Einstellungen
- **Datei**: `screenshot-12-admin-global-settings.png`
- **Ansicht**: Globale Einstellungen
- **Inhalt**: Parameter (Max. Stunden, Max. aufeinanderfolgende Schichten, etc.)

#### 13. Hilfe/Handbuch
- **Datei**: `screenshot-13-help-manual.png`
- **Ansicht**: Hilfe-Seite
- **Inhalt**: Inhaltsverzeichnis und Einleitung des Handbuchs

## Testdaten-Übersicht

Die `screenshot-test-data.sql` enthält:

- **3 Teams**: Alpha (Frühschicht), Beta (Spätschicht), Gamma (Nachtschicht)
- **17 Mitarbeiter**: 15 reguläre Mitarbeiter + 2 Springer
  - Verschiedene Funktionen: Werkschutz, Brandmeldetechniker, Brandschutzbeauftragter
  - Vollständige Daten: E-Mail, Geburtsdatum, Personalnummer
- **Schichten**: Komplette Woche (9.-15. Dez. 2025)
  - Frühdienst: 4-5 Personen (Mo-Fr), 2 Personen (Sa-So)
  - Spätdienst: 3-4 Personen (Mo-Fr), 2 Personen (Sa-So)
  - Nachtdienst: 3 Personen (Mo-Fr), 2-3 Personen (Sa-So)
- **Abwesenheiten**: 3 Urlaubseinträge
- **Urlaubsanträge**: 3 Anträge mit verschiedenen Status
- **Diensttausch**: 2 Tauschangebote
- **E-Mail-Einstellungen**: Beispiel-SMTP-Konfiguration

## Nach den Screenshots

**WICHTIG**: Nach Erstellung der Screenshots die Testdaten NICHT committen!

```bash
# Datenbank löschen
rm -f src/Dienstplan.Web/dienstplan.db*

# Sicherstellen, dass .gitignore dienstplan.db enthält
```

Die Anwendung sollte in Produktion mit einer leeren Datenbank starten.

## Screenshots in Dokumentation einfügen

### README.md

Screenshots in den Abschnitt "Screenshots" einfügen:

```markdown
## Screenshots

### Dienstplan-Ansicht (Woche)
![Dienstplan Wochenansicht](docs/screenshots/screenshot-01-schedule-week.png)
*Wochenansicht mit vollständiger Schichtplanung*

### Mitarbeiterverwaltung
![Mitarbeiterverwaltung](docs/screenshots/screenshot-04-employees.png)
*Übersicht aller Mitarbeiter mit Detailinformationen*

... (weitere Screenshots)
```

### Handbuch (index.html)

Screenshots in relevanten Sektionen einfügen:

```html
<h3>4.1 Dienstplan anzeigen</h3>
<div class="manual-screenshot">
    <img src="../docs/screenshots/screenshot-01-schedule-week.png" alt="Dienstplan Wochenansicht">
    <p><em>Abbildung 1: Wochenansicht des Dienstplans</em></p>
</div>
```

## Hinweise

- Screenshots sollten in hoher Qualität (PNG) gespeichert werden
- Vollbild-Screenshots für vollständige Seitenansicht
- Browser-Zoom auf 100% setzen
- Für bessere Darstellung: Browser-Fenster auf 1920x1080 setzen

---

**Version**: 1.2  
**Letzte Aktualisierung**: Dezember 2025
