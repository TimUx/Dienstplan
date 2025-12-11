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

#### 1. Hauptansicht - Dienstplan (Public)
- **Datei**: `01-schedule-week-public.png`
- **Ansicht**: Wochenansicht mit Beispieldaten (KW 50, 9.-15. Dez. 2025) - Öffentliche Ansicht
- **Inhalt**: Vollständiger Dienstplan mit allen Schichten und Mitarbeitern, ohne Administratorrechte

#### 2. Login-Dialog
- **Datei**: `02-login-modal.png`
- **Ansicht**: Anmeldedialog vor dem Einloggen
- **Inhalt**: Modal mit E-Mail/Passwort-Feldern und Standard-Anmeldedaten

#### 3. Hauptansicht - Dienstplan (Admin)
- **Datei**: `03-schedule-week-admin.png`
- **Ansicht**: Wochenansicht nach Administrator-Anmeldung
- **Inhalt**: Wochenansicht mit vollem Funktionsumfang und "Schichten planen" Button

#### 4. Hauptansicht - Dienstplan Monatsansicht (Admin)
- **Datei**: `04-schedule-month-admin.png`
- **Ansicht**: Monatsansicht Dezember 2025
- **Inhalt**: Monatliche Übersicht der Schichtplanung

#### 5. Hauptansicht - Dienstplan Jahresansicht (Admin)
- **Datei**: `05-schedule-year-admin.png`
- **Ansicht**: Jahresansicht 2025
- **Inhalt**: Jahresübersicht mit KW-Darstellung

#### 6. Mitarbeiterverwaltung
- **Datei**: `06-employees-list.png`
- **Ansicht**: Mitarbeiterübersicht nach dem Login als Admin
- **Inhalt**: Liste aller 17 Mitarbeiter mit Teams, Personalnummern und Springer-Kennzeichnung

#### 7. Urlaubsverwaltung - Urlaubsanträge
- **Datei**: `07-vacation-requests.png`
- **Ansicht**: Urlaub-Tab mit Urlaubsanträgen
- **Inhalt**: Tabelle mit Anträgen und verschiedenen Status (In Bearbeitung, Genehmigt, Nicht genehmigt)

#### 8. Urlaubsverwaltung - Diensttausch
- **Datei**: `08-shift-exchange.png`
- **Ansicht**: Diensttausch-Tab
- **Inhalt**: Mitarbeiter können Dienste zum Tausch anbieten - Genehmigung durch Disponent erforderlich

#### 9. Statistiken
- **Datei**: `09-statistics.png`
- **Ansicht**: Statistikübersicht
- **Inhalt**: Umfassende Statistiken über Arbeitsstunden, Schichtverteilung, Fehltage und Team-Auslastung

#### 10. Hilfe/Handbuch
- **Datei**: `10-help-manual.png`
- **Ansicht**: Hilfe-Seite
- **Inhalt**: Integriertes Benutzerhandbuch mit ausführlichen Anleitungen zu allen Funktionen

#### 11. Admin-Panel
- **Datei**: `11-admin-panel.png`
- **Ansicht**: Admin-Panel mit allen Sektionen
- **Inhalt**: Benutzerverwaltung, E-Mail-Einstellungen, Globale Einstellungen und System-Info

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
- **WICHTIG: Screenshots MÜSSEN in Full-HD (1920x1080) erstellt werden**
- Vollbild-Screenshots für vollständige Seitenansicht
- Browser-Zoom auf 100% setzen
- Browser-Fenster auf exakt 1920x1080 Pixel setzen

---

**Version**: 1.2  
**Letzte Aktualisierung**: Dezember 2025
