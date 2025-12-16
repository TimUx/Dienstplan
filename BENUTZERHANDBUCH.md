# 📘 Dienstplan - Benutzerhandbuch

**Version 2.0 - Python Edition** | Fritz Winter Eisengießerei GmbH & Co. KG

Vollständiges Handbuch für die Nutzung des automatischen Schichtverwaltungssystems.

---

## 📑 Inhaltsverzeichnis

1. [Einführung](#1-einführung)
2. [Erste Schritte](#2-erste-schritte)
3. [Benutzerrollen](#3-benutzerrollen)
4. [Anmeldung und Navigation](#4-anmeldung-und-navigation)
5. [Dienstplan-Ansichten](#5-dienstplan-ansichten)
6. [Mitarbeiterverwaltung](#6-mitarbeiterverwaltung)
7. [Teamverwaltung](#7-teamverwaltung)
8. [Schichtplanung](#8-schichtplanung)
9. [Abwesenheitsverwaltung](#9-abwesenheitsverwaltung)
10. [Urlaubsanträge](#10-urlaubsanträge)
11. [Diensttausch-System](#11-diensttausch-system)
12. [Statistiken und Auswertungen](#12-statistiken-und-auswertungen)
13. [Administration](#13-administration)
14. [Export-Funktionen](#14-export-funktionen)
15. [Fehlerbehebung](#15-fehlerbehebung)
16. [FAQ](#16-faq)

---

## 1. Einführung

### Was ist Dienstplan?

Dienstplan ist ein intelligentes System zur **automatischen Planung und Verwaltung von Schichtdiensten**. Es verwendet modernste Optimierungsalgorithmen (Google OR-Tools), um faire und rechtskonforme Schichtpläne zu erstellen.

### Hauptfunktionen

- ✅ **Automatische Schichtplanung** mit KI-gestütztem Solver
- ✅ **Mitarbeiter- und Teamverwaltung**
- ✅ **Abwesenheitsmanagement** (Urlaub, Krankheit, Lehrgänge)
- ✅ **Urlaubsantragsystem** mit Genehmigungsworkflow
- ✅ **Diensttausch-Plattform** zwischen Mitarbeitern
- ✅ **Umfangreiche Statistiken** und Auswertungen
- ✅ **Export-Funktionen** (PDF, Excel, CSV)
- ✅ **Responsive Web-Oberfläche** (Desktop & Smartphone)

### Systemvoraussetzungen

**Für Endbenutzer (Web-Zugriff):**
- Moderner Webbrowser (Chrome, Firefox, Edge, Safari)
- Internetverbindung zum Server
- Empfohlene Auflösung: mindestens 1024x768

**Für Server-Betrieb:**
- Python 3.9 oder höher ODER Windows Standalone Executable
- 2 GB RAM (Minimum), 4 GB empfohlen
- 500 MB freier Speicherplatz

---

## 2. Erste Schritte

### Installation

#### Option A: Windows Standalone (Empfohlen für Desktop-Nutzer)

1. Laden Sie die neueste Version von [GitHub Releases](https://github.com/TimUx/Dienstplan/releases) herunter
2. Entpacken Sie die ZIP-Datei
3. Doppelklicken Sie auf `Dienstplan.exe`
4. Der Browser öffnet sich automatisch

**Standard-Login:**
- E-Mail: `admin@fritzwinter.de`
- Passwort: `Admin123!`

#### Option B: Python-Installation

```bash
# Repository klonen
git clone https://github.com/TimUx/Dienstplan.git
cd Dienstplan

# Abhängigkeiten installieren
pip install -r requirements.txt

# Datenbank initialisieren
python main.py init-db --with-sample-data

# Server starten
python main.py serve
```

Öffnen Sie dann `http://localhost:5000` im Browser.

### Erster Login

1. Öffnen Sie die Dienstplan-Anwendung im Browser
2. Klicken Sie auf den **Anmelden**-Button (rechts oben)
3. Geben Sie die Standard-Anmeldedaten ein:
   - E-Mail: `admin@fritzwinter.de`
   - Passwort: `Admin123!`
4. Klicken Sie auf **Anmelden**

![Anmeldedialog](docs/screenshots/00-login-modal.png)

⚠️ **WICHTIG**: Ändern Sie nach der ersten Anmeldung das Passwort unter **Administration → Benutzerverwaltung**!

---

## 3. Benutzerrollen

Das System kennt drei Benutzerrollen mit unterschiedlichen Berechtigungen:

### 🔴 Administrator
**Vollzugriff auf alle Funktionen**

- ✅ Mitarbeiter erstellen, bearbeiten, löschen
- ✅ Teams verwalten
- ✅ Schichtplanung durchführen
- ✅ Abwesenheiten verwalten
- ✅ Urlaubsanträge genehmigen/ablehnen
- ✅ Diensttausch genehmigen/ablehnen
- ✅ Neue Benutzer registrieren
- ✅ Systemeinstellungen ändern
- ✅ Alle Statistiken einsehen
- ✅ Audit-Logs einsehen

### 🟡 Disponent
**Schichtplanung und Personalverwaltung**

- ✅ Mitarbeiter erstellen und bearbeiten
- ✅ Schichtplanung durchführen
- ✅ Abwesenheiten verwalten
- ✅ Urlaubsanträge genehmigen/ablehnen
- ✅ Diensttausch genehmigen/ablehnen
- ✅ Statistiken einsehen
- ❌ Keine Systemeinstellungen
- ❌ Keine Benutzerregistrierung

### 🟢 Mitarbeiter
**Lesezugriff und eigene Anträge**

- ✅ Dienstplan ansehen
- ✅ Statistiken einsehen (begrenzt)
- ✅ Mitarbeiterliste ansehen
- ✅ Eigene Urlaubsanträge stellen
- ✅ Eigene Dienste zum Tausch anbieten
- ✅ Diensttausch-Angebote annehmen
- ❌ Keine Bearbeitungsrechte
- ❌ Keine Verwaltungsfunktionen

---

## 4. Anmeldung und Navigation

### Hauptmenü (Navigationsleiste)

Nach der Anmeldung sehen Sie die Hauptnavigation:

- **🏠 Start** - Startseite mit Übersicht
- **📅 Dienstplan** - Schichtplan-Ansicht
- **👥 Mitarbeiter** - Mitarbeiterverwaltung
- **🏢 Teams** - Teamverwaltung
- **❌ Abwesenheiten** - Urlaub, Krank, Lehrgänge
- **🌴 Urlaubsanträge** - Urlaubsantragssystem
- **🔄 Diensttausch** - Diensttausch-Plattform
- **📊 Statistiken** - Auswertungen und Reports
- **⚙️ Administration** - Systemverwaltung (nur Admin)
- **❓ Hilfe** - Integriertes Handbuch

### Benutzermenu (Rechts oben)

Klicken Sie auf Ihren Namen (rechts oben) für:
- **Profil anzeigen**
- **Passwort ändern**
- **Abmelden**

![Hauptansicht](docs/screenshots/00-main-view.png)

---

## 5. Dienstplan-Ansichten

Der Dienstplan kann in drei verschiedenen Ansichten dargestellt werden:

### Wochenansicht

**Ideal für**: Detaillierte Tagesplanung

![Wochenansicht](docs/screenshots/03-schedule-week-admin.png)

**Funktionen:**
- Anzeige einer einzelnen Woche (Mo-So)
- Alle Schichten pro Tag und Mitarbeiter
- Farbcodierung nach Schichttyp
- Navigation: Vorherige/Nächste Woche

**Schichtcodes:**
- **F** = Frühdienst (05:45-13:45)
- **S** = Spätdienst (13:45-21:45)
- **N** = Nachtdienst (21:45-05:45)
- **Z** = Zwischendienst (08:00-16:00)
- **BMT** = Brandmeldetechniker (06:00-14:00, Mo-Fr)
- **BSB** = Brandschutzbeauftragter (07:00-16:30, Mo-Fr)
- **TD** = Tagdienst (speziell für qualifizierte Mitarbeiter)
- **K** = Krank
- **U** = Urlaub
- **L** = Lehrgang

### Monatsansicht

**Ideal für**: Mittelfristige Planung und Überblick

![Monatsansicht](docs/screenshots/04-schedule-month-admin.png)

**Funktionen:**
- Kalenderdarstellung eines ganzen Monats
- Kompakte Anzeige aller Schichten
- Schneller Überblick über Wochenenden
- Navigation: Vorheriger/Nächster Monat

### Jahresansicht

**Ideal für**: Langzeitplanung und Jahresübersicht

![Jahresansicht](docs/screenshots/05-schedule-year-admin.png)

**Funktionen:**
- Gesamtübersicht über ein ganzes Jahr
- Alle 12 Monate auf einen Blick
- Ideal für Jahresplanung
- Navigation: Vorheriges/Nächstes Jahr

### Ansicht wechseln

Klicken Sie auf die Buttons oben:
- **📅 Woche** - Wochenansicht
- **📅 Monat** - Monatsansicht
- **📅 Jahr** - Jahresansicht

---

## 6. Mitarbeiterverwaltung

### Mitarbeiterliste anzeigen

**Navigation:** Menü → **Mitarbeiter**

![Mitarbeiterliste](docs/screenshots/06-employees-list.png)

**Angezeigte Informationen:**
- Personalnummer
- Vorname und Name
- Team
- Funktion/Qualifikation
- Springer-Status
- Ferienjobber-Status
- Sonderfunktionen (BMT/BSB/TD)

### Neuen Mitarbeiter anlegen

**Berechtigung:** Admin oder Disponent

1. Klicken Sie auf **➕ Mitarbeiter hinzufügen**
2. Füllen Sie das Formular aus:

**Pflichtfelder:**
- **Vorname** *
- **Name** *
- **Personalnummer** * (eindeutig)

**Optionale Felder:**
- **E-Mail** - Für zukünftige Benachrichtigungen
- **Geburtsdatum** - Format: TT.MM.JJJJ
- **Funktion** - Freitext (z.B. "Schichtleiter")
- **Team** - Dropdown-Auswahl
- **Springer** - Checkbox (Backup-Mitarbeiter)
- **Ferienjobber** - Checkbox (temporärer Mitarbeiter)
- **Brandmeldetechniker (BMT)** - Checkbox
- **Brandschutzbeauftragter (BSB)** - Checkbox

3. Klicken Sie auf **Speichern**

**Hinweis:** Mitarbeiter mit BMT oder BSB-Qualifikation erhalten automatisch auch die TD-Qualifikation.

### Mitarbeiter bearbeiten

1. Klicken Sie auf das **✏️ Bearbeiten**-Symbol neben dem Mitarbeiter
2. Ändern Sie die gewünschten Felder
3. Klicken Sie auf **Speichern**

**Änderbare Felder:**
- Alle Personalinformationen
- Team-Zuordnung
- Qualifikationen (BMT/BSB/TD)
- Springer-Status
- Ferienjobber-Status

### Mitarbeiter löschen

**Berechtigung:** Nur Administrator

1. Klicken Sie auf das **🗑️ Löschen**-Symbol
2. Bestätigen Sie die Sicherheitsabfrage

⚠️ **ACHTUNG**: Das Löschen kann nicht rückgängig gemacht werden! Alle zugeordneten Schichten und Abwesenheiten werden ebenfalls gelöscht.

### Springer-System

**Was sind Springer?**
Springer sind Backup-Mitarbeiter, die flexibel einsetzbar sind und bei Personalausfällen einspringen können.

**Eigenschaften:**
- Können teamübergreifend eingesetzt werden
- Werden vom Planungsalgorithmus bevorzugt für Vertretungen verwendet
- Mindestens 1 Springer muss immer verfügbar bleiben (nicht eingeplant)

**Springer markieren:**
1. Mitarbeiter bearbeiten
2. Checkbox **Springer** aktivieren
3. Speichern

### Ferienjobber

**Was sind Ferienjobber?**
Ferienjobber sind temporäre Mitarbeiter, die typischerweise in den Sommerferien eingestellt werden.

**Besonderheiten:**
- Eigenes virtuelles Team "Ferienjobber"
- Können normal eingeplant werden
- Werden separat in Statistiken ausgewiesen

**Ferienjobber markieren:**
1. Mitarbeiter bearbeiten
2. Checkbox **Ferienjobber** aktivieren
3. Optional: Team zuordnen (falls gewünscht)
4. Speichern

### Qualifikationen (BMT/BSB/TD)

**BMT - Brandmeldetechniker:**
- Qualifikation für Brandmeldetechniker-Schichten
- Schichtzeit: Mo-Fr, 06:00-14:00 Uhr
- Genau 1 BMT pro Werktag erforderlich

**BSB - Brandschutzbeauftragter:**
- Qualifikation für Brandschutzbeauftragter-Schichten
- Schichtzeit: Mo-Fr, 07:00-16:30 Uhr (9,5 Stunden)
- Genau 1 BSB pro Werktag erforderlich

**TD - Tagdienst:**
- Spezieller Tagdienst für qualifizierte Mitarbeiter
- Wird automatisch gesetzt, wenn BMT oder BSB aktiv ist
- Kann auch manuell vergeben werden

---

## 7. Teamverwaltung

### Teams anzeigen

**Navigation:** Menü → **Teams**

**Angezeigte Informationen:**
- Teamname
- Beschreibung
- Anzahl Mitarbeiter
- Aktionen (Bearbeiten, Löschen)

### Neues Team erstellen

**Berechtigung:** Admin oder Disponent

1. Klicken Sie auf **➕ Team hinzufügen**
2. Füllen Sie das Formular aus:
   - **Name** * - z.B. "Team Alpha"
   - **Beschreibung** - Optional, z.B. "Frühschicht-Team"
3. Klicken Sie auf **Erstellen**

**Standard-Teams:**
- Team Alpha
- Team Beta
- Team Gamma
- Virtuelle Teams (automatisch):
  - Brandmeldetechniker (BMT)
  - Brandschutzbeauftragte (BSB)
  - Ferienjobber

### Team bearbeiten

1. Klicken Sie auf **✏️ Bearbeiten**
2. Ändern Sie Name oder Beschreibung
3. Klicken Sie auf **Speichern**

### Team löschen

**Berechtigung:** Nur Administrator

1. Klicken Sie auf **🗑️ Löschen**
2. Bestätigen Sie die Sicherheitsabfrage

⚠️ **WICHTIG**: Mitarbeiter im Team werden nicht gelöscht, sondern nur ihre Team-Zuordnung wird entfernt.

### Virtuelle Teams

Das System erstellt automatisch virtuelle Teams für Sonderfunktionen:

**Team "Brandmeldetechniker (BMT)":**
- Enthält alle Mitarbeiter mit BMT-Qualifikation
- ID: 99 (fest)
- Nicht löschbar

**Team "Brandschutzbeauftragte (BSB)":**
- Enthält alle Mitarbeiter mit BSB-Qualifikation
- ID: 97 (fest)
- Nicht löschbar

**Team "Ferienjobber":**
- Enthält alle als Ferienjobber markierten Mitarbeiter
- ID: 98 (fest)
- Nicht löschbar

---

## 8. Schichtplanung

### Automatische Planung starten

**Berechtigung:** Admin oder Disponent

**Navigation:** Menü → **Dienstplan** → Button **Schichten planen**

![Planungsdialog](docs/screenshots/03-schedule-week-admin.png)

1. Klicken Sie auf **Schichten planen**
2. Wählen Sie den Zeitraum:
   - **Startdatum** - Beginn der Planung
   - **Enddatum** - Ende der Planung
3. Optional: **Vorhandene Schichten überschreiben**
   - ⚠️ Checkbox aktivieren = Alle bestehenden Schichten im Zeitraum werden gelöscht
   - Checkbox deaktiviert = Nur leere Tage werden geplant
4. Klicken Sie auf **Planen**
5. Warten Sie auf die Berechnung (kann 1-5 Minuten dauern)

**Der Algorithmus berücksichtigt:**
- ✅ Alle Abwesenheiten (Urlaub, Krank, Lehrgang)
- ✅ Arbeitszeitgesetze (max. 48h/Woche, 192h/Monat)
- ✅ Ruhezeiten (mind. 11 Stunden zwischen Schichten)
- ✅ Mindestbesetzung pro Schicht
- ✅ Faire Verteilung über alle Mitarbeiter
- ✅ Springer-Verfügbarkeit
- ✅ Qualifikationsanforderungen (BMT/BSB/TD)
- ✅ Verbotene Schichtwechsel (z.B. Spät → Früh)

**Ergebnis:**
- Grüne Meldung = Erfolgreich geplant
- Rote Meldung = Keine Lösung gefunden (siehe [Fehlerbehebung](#15-fehlerbehebung))

### Manuelle Schichtbearbeitung

**Berechtigung:** Admin oder Disponent

Sie können Schichten manuell hinzufügen, ändern oder löschen:

#### Schicht hinzufügen

1. Klicken Sie auf eine leere Zelle im Kalender
2. Wählen Sie:
   - **Mitarbeiter**
   - **Schichttyp** (F/S/N/Z/BMT/BSB/TD)
   - **Datum**
3. Klicken Sie auf **Speichern**

#### Schicht ändern

1. Klicken Sie auf eine bestehende Schicht
2. Wählen Sie neuen Schichttyp
3. Klicken Sie auf **Speichern**

#### Schicht löschen

1. Klicken Sie auf eine bestehende Schicht
2. Klicken Sie auf **Löschen**
3. Bestätigen Sie die Aktion

#### Schicht fixieren

Fixierte Schichten werden bei erneuter automatischer Planung nicht überschrieben:

1. Klicken Sie auf eine Schicht
2. Klicken Sie auf **🔒 Fixieren**
3. Fixierte Schichten werden mit Schloss-Symbol angezeigt

Um Fixierung aufzuheben:
1. Klicken Sie auf fixierte Schicht
2. Klicken Sie auf **🔓 Fixierung aufheben**

### Schichtbesetzungsregeln

**Wochentage (Mo-Fr):**
- **Frühdienst (F)**: 4-5 Personen
- **Spätdienst (S)**: 3-4 Personen
- **Nachtdienst (N)**: 3 Personen
- **BMT**: Genau 1 Person (qualifiziert)
- **BSB**: Genau 1 Person (qualifiziert)

**Wochenende (Sa-So):**
- **Frühdienst (F)**: 2-3 Personen
- **Spätdienst (S)**: 2-3 Personen
- **Nachtdienst (N)**: 2-3 Personen
- **BMT**: Nicht erforderlich
- **BSB**: Nicht erforderlich

### Planungsstrategien

**Best Practices für optimale Ergebnisse:**

1. **Rechtzeitig planen**: Mindestens 2 Wochen im Voraus
2. **Abwesenheiten erfassen**: Alle bekannten Urlaube/Ausfälle eintragen
3. **Genug Springer**: Mindestens 3-4 Springer markieren
4. **Zeitraum begrenzen**: Max. 2 Monate auf einmal planen
5. **Fixierungen sparsam nutzen**: Nur wichtige Schichten fixieren
6. **Nach Planung prüfen**: Ergebnis auf Fairness kontrollieren

---

## 9. Abwesenheitsverwaltung

### Abwesenheiten anzeigen

**Navigation:** Menü → **Abwesenheiten**

**Angezeigte Informationen:**
- Mitarbeiter
- Art der Abwesenheit (Urlaub/Krank/Lehrgang)
- Start- und Enddatum
- Dauer in Tagen
- Notizen

### Neue Abwesenheit erfassen

**Berechtigung:** Admin oder Disponent

1. Klicken Sie auf **➕ Abwesenheit hinzufügen**
2. Füllen Sie das Formular aus:
   - **Mitarbeiter** * - Dropdown-Auswahl
   - **Art** * - Urlaub, Krank oder Lehrgang
   - **Startdatum** * - Format: TT.MM.JJJJ
   - **Enddatum** * - Format: TT.MM.JJJJ
   - **Notizen** - Optional
3. Klicken Sie auf **Speichern**

**Abwesenheitsarten:**
- **U - Urlaub** (grün) - Geplante Urlaubstage
- **K - Krank** (rot) - Krankheitstage
- **L - Lehrgang** (blau) - Schulungen, Fortbildungen

### Abwesenheit bearbeiten

1. Klicken Sie auf **✏️ Bearbeiten**
2. Ändern Sie die gewünschten Felder
3. Klicken Sie auf **Speichern**

### Abwesenheit löschen

1. Klicken Sie auf **🗑️ Löschen**
2. Bestätigen Sie die Aktion

### Abwesenheitsdarstellung im Dienstplan

Abwesenheiten werden im Dienstplan farblich markiert:
- **U** (Urlaub) = Grüner Hintergrund
- **K** (Krank) = Roter Hintergrund
- **L** (Lehrgang) = Blauer Hintergrund

**Wichtig:** An Abwesenheitstagen können keine regulären Schichten vergeben werden.

---

## 10. Urlaubsanträge

Das System verfügt über ein vollständiges Urlaubsantragssystem mit Genehmigungsworkflow.

![Urlaubsanträge](docs/screenshots/07-vacation-requests.png)

### Urlaubsantrag stellen (als Mitarbeiter)

**Navigation:** Menü → **Urlaubsanträge** → **➕ Antrag stellen**

1. Klicken Sie auf **Neuer Urlaubsantrag**
2. Füllen Sie das Formular aus:
   - **Startdatum** * - Erster Urlaubstag
   - **Enddatum** * - Letzter Urlaubstag
   - **Grund** - Optional, z.B. "Sommerurlaub"
3. Klicken Sie auf **Antrag stellen**

**Status nach Einreichung:** "In Bearbeitung" (gelb)

### Urlaubsanträge bearbeiten (als Disponent/Admin)

**Berechtigung:** Admin oder Disponent

**Navigation:** Menü → **Urlaubsanträge**

Sie sehen alle offenen und vergangenen Anträge:

#### Antrag genehmigen

1. Wählen Sie einen Antrag mit Status "In Bearbeitung"
2. Klicken Sie auf **✅ Genehmigen**
3. Bestätigen Sie die Aktion

**Was passiert:**
- Status wird auf "Genehmigt" (grün) gesetzt
- Automatisch wird eine Abwesenheit vom Typ "Urlaub" erstellt
- Mitarbeiter kann die Genehmigung sehen

#### Antrag ablehnen

1. Wählen Sie einen Antrag mit Status "In Bearbeitung"
2. Klicken Sie auf **❌ Ablehnen**
3. Optional: Geben Sie einen Ablehnungsgrund ein
4. Bestätigen Sie die Aktion

**Was passiert:**
- Status wird auf "Abgelehnt" (rot) gesetzt
- Keine Abwesenheit wird erstellt
- Mitarbeiter kann die Ablehnung sehen

### Status-Übersicht

- **🟡 In Bearbeitung** - Warten auf Genehmigung
- **🟢 Genehmigt** - Urlaubsantrag genehmigt, Abwesenheit erstellt
- **🔴 Abgelehnt** - Urlaubsantrag abgelehnt

### Eigene Anträge einsehen (als Mitarbeiter)

1. Navigieren Sie zu **Urlaubsanträge**
2. Sie sehen alle Ihre eigenen Anträge mit aktuellem Status
3. Filter nach Status möglich

---

## 11. Diensttausch-System

Das Diensttausch-System ermöglicht es Mitarbeitern, Dienste untereinander zu tauschen.

![Diensttausch](docs/screenshots/08-shift-exchange.png)

### Dienst zum Tausch anbieten

**Als Mitarbeiter:**

1. Navigieren Sie zu **Diensttausch**
2. Klicken Sie auf **Dienst anbieten**
3. Wählen Sie:
   - **Datum** - Welchen Dienst möchten Sie anbieten?
   - **Grund** - Optional, z.B. "Private Verpflichtung"
4. Klicken Sie auf **Anbieten**

**Was passiert:**
- Ihr Dienst wird in der Tauschbörse angezeigt
- Andere Mitarbeiter können diesen Dienst anfragen

### Dienst anfragen

**Als interessierter Mitarbeiter:**

1. Navigieren Sie zu **Diensttausch** → **Verfügbare Angebote**
2. Sehen Sie alle angebotenen Dienste
3. Klicken Sie bei gewünschtem Dienst auf **Anfragen**
4. Bestätigen Sie Ihre Anfrage

**Was passiert:**
- Eine Tausch-Anfrage wird erstellt
- Der Disponent/Admin wird benachrichtigt
- Status: "Warten auf Genehmigung"

### Diensttausch genehmigen/ablehnen

**Als Disponent/Admin:**

**Navigation:** Menü → **Diensttausch** → **Offene Anfragen**

#### Tausch genehmigen

1. Wählen Sie eine offene Anfrage
2. Prüfen Sie die Details:
   - Wer tauscht mit wem?
   - Welches Datum?
   - Sind beide Mitarbeiter qualifiziert?
3. Klicken Sie auf **✅ Genehmigen**

**Was passiert:**
- Die Schichtzuweisung wird automatisch getauscht
- Beide Mitarbeiter werden benachrichtigt
- Status: "Genehmigt"

#### Tausch ablehnen

1. Wählen Sie eine offene Anfrage
2. Klicken Sie auf **❌ Ablehnen**
3. Optional: Geben Sie einen Grund ein

**Was passiert:**
- Keine Änderung an Schichten
- Beide Mitarbeiter werden benachrichtigt
- Status: "Abgelehnt"

### Tausch-Regeln

**Automatische Prüfungen:**
- ✅ Beide Mitarbeiter müssen für die Schichtart qualifiziert sein
- ✅ Keine Konflikte mit Abwesenheiten
- ✅ Arbeitszeitgesetze werden eingehalten
- ✅ Ruhezeiten werden beachtet

**Gründe für Ablehnung:**
- Fehlende Qualifikation
- Überschreitung von Arbeitszeitgrenzen
- Konflikte mit anderen Schichten
- Mangelnde Besetzung

---

## 12. Statistiken und Auswertungen

Das System bietet umfangreiche Statistiken und Auswertungen.

![Statistiken](docs/screenshots/09-statistics.png)

### Dashboard-Statistiken

**Navigation:** Menü → **Statistiken**

**Verfügbare Auswertungen:**

#### 1. Arbeitsstunden pro Mitarbeiter

- Gesamtstunden im gewählten Zeitraum
- Durchschnitt pro Woche
- Durchschnitt pro Monat
- Farbliche Kennzeichnung:
  - 🟢 Grün: Im Normalbereich
  - 🟡 Gelb: Nahe am Limit
  - 🔴 Rot: Überschreitung

#### 2. Schichtverteilung

**Pro Mitarbeiter:**
- Anzahl Frühdienste (F)
- Anzahl Spätdienste (S)
- Anzahl Nachtdienste (N)
- Anzahl Zwischendienste (Z)
- Sonderfunktionen (BMT/BSB/TD)

**Pro Team:**
- Gesamtverteilung aller Schichtarten
- Vergleich zwischen Teams
- Auslastung pro Team

#### 3. Fehltage-Übersicht

- Urlaubstage pro Mitarbeiter
- Krankheitstage pro Mitarbeiter
- Lehrgangstage pro Mitarbeiter
- Gesamtausfallzeiten

#### 4. Wochenend-Dienste (Nur Disponent/Admin)

**Spezielle Auswertung:**
- Anzahl Samstags-Dienste pro Mitarbeiter
- Anzahl Sonntags-Dienste pro Mitarbeiter
- Anzahl Wochenend-Dienste gesamt
- Faire Verteilung überprüfen

**Zugriff:**
```
GET /api/statistics/weekend-shifts?startDate=2025-01-01&endDate=2025-12-31
```

#### 5. Team-Auslastung

- Durchschnittliche Arbeitsstunden pro Team
- Vergleich zwischen Teams
- Auslastungsgrad in %

### Statistik-Zeiträume

Wählen Sie den Auswertungszeitraum:
- **Letzte 7 Tage**
- **Letzter Monat**
- **Letzte 3 Monate**
- **Letztes Jahr**
- **Benutzerdefiniert** - Freie Datumsauswahl

### Export von Statistiken

Alle Statistiken können exportiert werden:
1. Klicken Sie auf **Export**
2. Wählen Sie Format:
   - **CSV** - Für Excel/Numbers
   - **PDF** - Für Berichte
   - **Excel** - Natives Excel-Format

---

## 13. Administration

Der Administrationsbereich ist nur für Benutzer mit Admin-Rolle zugänglich.

![Admin-Panel](docs/screenshots/11-admin-panel.png)

### Benutzerverwaltung

#### Neue Benutzer registrieren

1. Navigieren Sie zu **Administration** → **Benutzer**
2. Klicken Sie auf **➕ Benutzer hinzufügen**
3. Füllen Sie das Formular aus:
   - **E-Mail** * - Eindeutige E-Mail-Adresse
   - **Passwort** * - Mindestens 8 Zeichen
   - **Vorname**
   - **Nachname**
   - **Rolle** * - Admin, Disponent oder Mitarbeiter
4. Klicken Sie auf **Registrieren**

#### Benutzer bearbeiten

1. Wählen Sie einen Benutzer aus der Liste
2. Klicken Sie auf **✏️ Bearbeiten**
3. Ändern Sie:
   - E-Mail
   - Name
   - Rolle
   - Passwort (falls gewünscht)
4. Klicken Sie auf **Speichern**

#### Passwort zurücksetzen

1. Wählen Sie einen Benutzer
2. Klicken Sie auf **🔑 Passwort zurücksetzen**
3. Geben Sie neues Passwort ein
4. Bestätigen Sie

### System-Einstellungen

#### E-Mail-Konfiguration

**Für zukünftige Benachrichtigungen:**
- SMTP-Server
- Port
- Benutzername
- Passwort
- Absender-Adresse

#### Schichtparameter

**Anpassbare Parameter:**
- Mindestbesetzung pro Schicht
- Maximalbesetzung pro Schicht
- Standardschichtzeiten
- Ruhezeiten

#### Solver-Einstellungen

**OR-Tools-Parameter:**
- Zeitlimit (in Sekunden, Standard: 300)
- Anzahl Worker (Standard: 8)
- Such-Strategie

### Audit-Logs

**Protokollierung aller Änderungen:**
- Wer hat was geändert?
- Wann wurde die Änderung vorgenommen?
- Welche Daten wurden geändert?

**Zugriff:**
1. Navigieren Sie zu **Administration** → **Audit-Logs**
2. Filtern Sie nach:
   - Datum
   - Benutzer
   - Aktion (Create, Update, Delete)
   - Entität (Employee, Shift, etc.)

### Datenbank-Wartung

#### Backup erstellen

**Manuell:**
1. Kopieren Sie die Datei `dienstplan.db`
2. Speichern Sie an sicherem Ort

**Automatisiert:**
```bash
# Tägliches Backup (Linux Cron)
0 2 * * * cp /pfad/zu/dienstplan.db /backup/dienstplan_$(date +\%Y\%m\%d).db
```

#### Datenbank wiederherstellen

1. Stoppen Sie den Server
2. Ersetzen Sie `dienstplan.db` durch Backup
3. Starten Sie den Server neu

#### Alte Daten löschen

**Empfehlung:** Daten älter als 2 Jahre löschen

```sql
-- Alte Schichten löschen (SQL direkt auf DB)
DELETE FROM ShiftAssignments WHERE Date < date('now', '-2 years');

-- Alte Abwesenheiten löschen
DELETE FROM Absences WHERE StartDate < date('now', '-2 years');
```

---

## 14. Export-Funktionen

Das System bietet umfangreiche Export-Funktionen für Dienstpläne.

### CSV-Export

**Verwendung:** Import in Excel, Numbers, Google Sheets

**Zugriff:**
1. Öffnen Sie den Dienstplan
2. Wählen Sie den Zeitraum
3. Klicken Sie auf **Export → CSV**

**Dateiformat:**
```csv
Datum,Mitarbeiter,Personalnummer,Team,Schichttyp,Start,Ende,Dauer
2025-01-01,Max Mustermann,12345,Team Alpha,F,05:45,13:45,8.0
...
```

### PDF-Export

**Verwendung:** Ausdrucke, Berichte, Aushänge

**Zugriff:**
1. Öffnen Sie den Dienstplan
2. Wählen Sie den Zeitraum
3. Klicken Sie auf **Export → PDF**

**Inhalt:**
- Übersichtlicher Kalender
- Alle Schichten farbcodiert
- Teamzuordnung
- Abwesenheiten markiert
- Kopfzeile mit Datum und Zeitraum

**Druckoptionen:**
- Hochformat / Querformat
- Wochenansicht oder Monatsansicht
- Optional: Statistik-Zusammenfassung

### Excel-Export

**Verwendung:** Detaillierte Auswertungen, Weiterverarbeitung

**Zugriff:**
1. Öffnen Sie den Dienstplan
2. Wählen Sie den Zeitraum
3. Klicken Sie auf **Export → Excel**

**Dateiformat:** `.xlsx` (Microsoft Excel 2007+)

**Enthält:**
- Mehrere Arbeitsblätter:
  - **Schichtplan** - Hauptplan mit allen Schichten
  - **Mitarbeiter** - Mitarbeiterstatistiken
  - **Teams** - Team-Auswertungen
  - **Zusammenfassung** - Übersicht und Kennzahlen
- Formatierung und Farben
- Formeln für automatische Berechnungen
- Pivot-Tabellen (optional)

### Export-API

**Programmatischer Zugriff:**

```bash
# CSV
GET /api/shifts/export/csv?startDate=2025-01-01&endDate=2025-01-31

# PDF
GET /api/shifts/export/pdf?startDate=2025-01-01&endDate=2025-01-31&view=month

# Excel
GET /api/shifts/export/excel?startDate=2025-01-01&endDate=2025-01-31
```

---

## 15. Fehlerbehebung

### Häufige Probleme und Lösungen

#### Problem: Keine Lösung gefunden bei automatischer Planung

**Symptome:**
- Fehlermeldung: "Keine optimale Lösung gefunden"
- Rote Warnung nach Planung

**Mögliche Ursachen:**
1. Zu viele Abwesenheiten im Zeitraum
2. Zu wenige verfügbare Mitarbeiter
3. Zu restriktive Constraints
4. Zeitlimit zu kurz

**Lösungen:**

**Option 1: Zeitlimit erhöhen**
```bash
python main.py plan --start-date 2025-01-01 --end-date 2025-01-31 --time-limit 600
```

**Option 2: Zeitraum verkürzen**
- Planen Sie nur 2-3 Wochen statt einen ganzen Monat
- Teilen Sie große Zeiträume auf

**Option 3: Mehr Springer hinzufügen**
- Markieren Sie weitere Mitarbeiter als Springer
- Mindestens 3-4 Springer empfohlen

**Option 4: Abwesenheiten überprüfen**
- Prüfen Sie, ob zu viele Mitarbeiter gleichzeitig abwesend sind
- Verteilen Sie Urlaube gleichmäßiger

**Option 5: Constraints anpassen** (Entwickler)
- Lockern Sie Besetzungsstärken temporär
- Passen Sie in `constraints.py` Mindest-/Maximalwerte an

#### Problem: Login funktioniert nicht

**Symptome:**
- Fehlermeldung: "Ungültige Anmeldedaten"
- Kann sich nicht anmelden

**Lösungen:**

1. **Standard-Anmeldedaten prüfen:**
   - E-Mail: `admin@fritzwinter.de`
   - Passwort: `Admin123!`
   - Beachten Sie Groß-/Kleinschreibung!

2. **Datenbank initialisiert?**
   ```bash
   python main.py init-db --with-sample-data
   ```

3. **Browser-Cache leeren:**
   - Strg+Shift+Del (Windows/Linux)
   - Cmd+Shift+Del (Mac)
   - Cache und Cookies löschen

4. **Passwort zurücksetzen (Admin):**
   - Zugriff auf Datenbank erforderlich
   - SQL-Befehl ausführen (siehe Entwicklerdoku)

#### Problem: Server startet nicht

**Symptome:**
- Fehlermeldung beim Start
- Port bereits belegt
- Module nicht gefunden

**Lösungen:**

**Port belegt:**
```bash
# Anderen Port verwenden
python main.py serve --port 8080
```

**Dependencies fehlen:**
```bash
# Neu installieren
pip install -r requirements.txt --force-reinstall
```

**Python-Version prüfen:**
```bash
python --version  # Sollte 3.9 oder höher sein
```

#### Problem: Web-UI zeigt keine Daten

**Symptome:**
- Leere Tabellen
- Keine Mitarbeiter/Teams sichtbar
- Fehlermeldungen in Browser-Konsole

**Lösungen:**

1. **Browser-Konsole öffnen:**
   - F12 drücken
   - Auf Fehler prüfen (rote Meldungen)

2. **CORS-Problem:**
   - Überprüfen Sie `web_api.py` → CORS-Konfiguration
   - Erlaubte Origins prüfen

3. **Falsche Datenbank:**
   ```bash
   # Prüfen Sie, welche DB verwendet wird
   python main.py serve --db dienstplan.db
   ```

4. **Datenbank leer:**
   ```bash
   # Beispieldaten laden
   python main.py init-db --with-sample-data
   ```

#### Problem: Schichten werden nicht gespeichert

**Symptome:**
- Manuelle Schichten verschwinden
- Änderungen werden nicht übernommen

**Lösungen:**

1. **Berechtigung prüfen:**
   - Als Admin oder Disponent angemeldet?
   - Rolle in Admin-Panel prüfen

2. **Browser-Konsole prüfen:**
   - F12 → Netzwerk-Tab
   - Fehlermeldungen bei POST-Requests?

3. **Datenbank-Rechte:**
   - Hat der Server Schreibrechte auf `dienstplan.db`?
   - Linux: `chmod 644 dienstplan.db`

#### Problem: Export funktioniert nicht

**Symptome:**
- PDF/Excel-Export schlägt fehl
- Download startet nicht

**Lösungen:**

1. **Dependencies prüfen:**
   ```bash
   pip install reportlab openpyxl
   ```

2. **Zeitraum zu groß:**
   - Exportieren Sie kürzere Zeiträume
   - Max. 3 Monate empfohlen

3. **Browser-Popup-Blocker:**
   - Erlauben Sie Downloads für die Seite
   - Popup-Blocker deaktivieren

---

## 16. FAQ

### Allgemeine Fragen

**F: Wie viele Mitarbeiter kann das System verwalten?**
A: Das System ist theoretisch unbegrenzt skalierbar. In der Praxis wurden Tests mit bis zu 100 Mitarbeitern erfolgreich durchgeführt. Die Planungszeit steigt mit der Anzahl der Mitarbeiter.

**F: Kann ich mehrere Firmen/Standorte verwalten?**
A: Aktuell ist das System für einen Standort konzipiert. Multi-Mandanten-Fähigkeit ist für Version 3.x geplant. Als Workaround können Sie separate Datenbanken verwenden.

**F: Welche Browser werden unterstützt?**
A: Alle modernen Browser:
- Chrome/Chromium (empfohlen)
- Firefox
- Microsoft Edge
- Safari (Mac/iOS)
- Mobile Browser (responsive Design)

**F: Ist das System DSGVO-konform?**
A: Ja, das System speichert Daten lokal in Ihrer eigenen Datenbank. Sie haben volle Kontrolle über alle personenbezogenen Daten. Beachten Sie die üblichen DSGVO-Anforderungen für Ihren Betrieb.

**F: Kann ich das System offline nutzen?**
A: Das System benötigt keine Internetverbindung für den Betrieb. Sie benötigen nur Netzwerkzugriff auf den Server (kann auch localhost sein).

### Planung & Algorithmus

**F: Wie lange dauert eine Planung?**
A: Typischerweise 30 Sekunden bis 5 Minuten, abhängig von:
- Anzahl Mitarbeiter (mehr = länger)
- Planungszeitraum (länger = mehr Zeit)
- Anzahl Constraints (komplexer = länger)
- Server-Hardware (besserer CPU = schneller)

**F: Garantiert der Algorithmus eine optimale Lösung?**
A: Der OR-Tools CP-SAT Solver findet provably optimale oder near-optimale Lösungen. Bei komplexen Problemen wird innerhalb des Zeitlimits die beste gefundene Lösung zurückgegeben.

**F: Kann ich eigene Regeln hinzufügen?**
A: Ja, als Entwickler können Sie in `constraints.py` neue Constraints definieren. Grundkenntnisse in Python und Constraint Programming erforderlich.

**F: Berücksichtigt der Algorithmus persönliche Wünsche?**
A: Wunschschichten sind für Version 3.x geplant. Aktuell können Sie manuelle Schichten setzen und fixieren.

### Schichten & Personal

**F: Kann ein Mitarbeiter in mehreren Teams sein?**
A: Nein, jeder Mitarbeiter kann nur einem regulären Team zugeordnet werden. Virtuelle Teams (BMT/BSB/Ferienjobber) sind zusätzlich.

**F: Was passiert, wenn ein Springer krank wird?**
A: Der Algorithmus plant automatisch einen anderen verfügbaren Mitarbeiter ein. Für Notfälle können Sie manuell umplanen.

**F: Können Teilzeit-Mitarbeiter verwaltet werden?**
A: Ja, über Abwesenheiten. Markieren Sie die Nicht-Arbeitstage als "Abwesend". Eine dedizierte Teilzeit-Funktion ist in Planung.

**F: Wie werden Feiertage behandelt?**
A: Feiertage werden wie Wochenenden behandelt (reduzierte Besetzung). Eine Feiertags-Funktion mit regionalen Kalendern ist geplant.

### Technisches

**F: Welche Datenbank wird verwendet?**
A: SQLite (Standard). Das System kann aber leicht auf PostgreSQL oder MySQL migriert werden.

**F: Kann ich das System in Docker betreiben?**
A: Ja, ein Dockerfile-Beispiel finden Sie in der README. Alternativ können Sie eigene Container-Images erstellen.

**F: Gibt es eine mobile App?**
A: Aktuell nicht, aber die Web-Oberfläche ist responsive und funktioniert auf Smartphones. Eine native App ist für Version 3.x geplant.

**F: Wie mache ich ein Backup?**
A: Kopieren Sie einfach die Datei `dienstplan.db` und den Ordner `data/`. Für automatische Backups siehe [Administration](#13-administration).

**F: Kann ich meine Daten exportieren?**
A: Ja, über Export-Funktionen (CSV/Excel/PDF) oder direkter Zugriff auf die SQLite-Datenbank.

### Sicherheit

**F: Wie sicher ist das System?**
A: Das System nutzt:
- Passwort-Hashing (SHA-256)
- Rollenbasierte Zugriffskontrolle
- SQL-Injection-Schutz
- Cookie-basierte Session-Verwaltung

Für Produktivbetrieb empfehlen wir zusätzlich HTTPS via Reverse Proxy.

**F: Wie ändere ich das Admin-Passwort?**
A: Nach Login als Admin → Administration → Benutzerverwaltung → Admin-Benutzer bearbeiten → Passwort ändern.

**F: Was passiert bei SQL-Injection-Versuchen?**
A: Alle Datenbankzugriffe verwenden parametrisierte Queries, die vor SQL-Injection schützen.

### Probleme & Support

**F: Wo finde ich weitere Hilfe?**
A: 
1. Diese Dokumentation durchsuchen
2. GitHub Issues: https://github.com/TimUx/Dienstplan/issues
3. README und technische Doku lesen

**F: Wie melde ich einen Bug?**
A: Erstellen Sie ein GitHub Issue mit:
- Beschreibung des Problems
- Schritte zur Reproduktion
- Erwartetes vs. tatsächliches Verhalten
- Screenshots (falls relevant)
- Log-Ausgaben

**F: Kann ich Features vorschlagen?**
A: Ja! Erstellen Sie ein Feature Request auf GitHub Issues. Beschreiben Sie den Use Case und den erwarteten Nutzen.

---

## 🎓 Schulungsressourcen

### Für neue Benutzer

1. **Schnellstart-Video** (geplant)
2. **Interaktive Tour** durch die Web-UI (geplant)
3. **Schritt-für-Schritt-Tutorials** in dieser Dokumentation

### Für Administratoren

1. **[Administration](#13-administration)** - Dieser Abschnitt
2. **[Build-Anleitung](docs/BUILD_GUIDE.md)** - Für Deployment
3. **[Architektur](ARCHITECTURE.md)** - System-Design

### Für Entwickler

1. **[Architektur](ARCHITECTURE.md)** - System-Übersicht
2. **[Migration](MIGRATION.md)** - .NET → Python
3. **[README](README.md#-entwicklung)** - Entwickler-Dokumentation

---

## 📞 Support und Kontakt

**Bei Fragen oder Problemen:**

1. **Dokumentation**: Lesen Sie diese Dokumentation und [README.md](README.md)
2. **GitHub Issues**: https://github.com/TimUx/Dienstplan/issues
3. **E-Mail**: Kontaktieren Sie Ihre IT-Abteilung oder System-Administrator

**Für Entwickler:**
- **Repository**: https://github.com/TimUx/Dienstplan
- **Releases**: https://github.com/TimUx/Dienstplan/releases

---

## 📄 Anhang

### Glossar

**BMT** - Brandmeldetechniker, Sonderfunktion für Brandmeldeanlagen

**BSB** - Brandschutzbeauftragter, Sonderfunktion für Brandschutz

**CP-SAT** - Constraint Programming Satisfiability Solver (Google OR-Tools)

**Disponent** - Benutzerrolle mit Planungsrechten

**F, S, N** - Früh-, Spät-, Nachtdienst

**Ferienjobber** - Temporärer Mitarbeiter (meist Sommer)

**OR-Tools** - Google's Operations Research Tools für Optimierung

**Springer** - Flexibler Backup-Mitarbeiter

**TD** - Tagdienst, Sonderfunktion für qualifizierte Mitarbeiter

**Z** - Zwischendienst (08:00-16:00)

### Tastenkürzel

**Allgemein:**
- `Strg+S` - Formular speichern (wo verfügbar)
- `Esc` - Dialog schließen
- `Strg+F` - Suche in Tabellen

**Navigation:**
- `←` / `→` - Vorherige/Nächste Woche (im Kalender)
- `↑` / `↓` - Scrollen in Listen

---

**Version 2.0 - Python Edition**

Entwickelt von **Timo Braun** mit ❤️ für effiziente Schichtverwaltung

Powered by **Google OR-Tools**

© 2025 Fritz Winter Eisengießerei GmbH & Co. KG

---

*Letzte Aktualisierung: Dezember 2025*
