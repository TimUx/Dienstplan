# Urlaubsjahresplan (Yearly Vacation Plan) - Dokumentation

## Übersicht

Der Urlaubsjahresplan bietet eine Jahresübersicht aller Urlaube für alle Mitarbeiter. Die Anzeige der Urlaubsdaten muss vom Administrator für jedes Jahr individuell freigegeben werden.

## Funktionen

### 1. Farbcodierung der Urlaube

Alle Urlaubseinträge werden im gesamten System (Dienstplan-Ansichten und Urlaubsjahresplan) farblich nach ihrem Genehmigungsstatus gekennzeichnet:

- **🔵 Blau (Genehmigt)**: Urlaubsantrag wurde vom Disponenten genehmigt
- **🟠 Orange (In Genehmigung)**: Urlaubsantrag wurde eingereicht und wartet auf Genehmigung
- **⚫ Grau (Abgelehnt)**: Urlaubsantrag wurde vom Disponenten abgelehnt

### 2. Jahresfreigabe durch Administrator

Der Administrator muss die Anzeige der Urlaubsdaten für jedes Jahr explizit freigeben:

- **Nicht freigegeben**: Urlaubsdaten sind für normale Benutzer nicht sichtbar
- **Freigegeben**: Alle Benutzer können die Urlaubsdaten für dieses Jahr im Urlaubsjahresplan einsehen

### 3. Integration mit bestehendem Urlaubsmanagement

Der Urlaubsjahresplan basiert vollständig auf dem vorhandenen Urlaubsmanagement:

- Nutzt die bestehende `VacationRequests` Tabelle (Urlaubsanträge mit Workflow)
- Integriert auch direkt eingetragene Urlaube aus der `Absences` Tabelle (Type=2)
- Respektiert alle bestehenden Genehmigungsstatus
- Keine Änderung am bestehenden Urlaubsantragsprozess erforderlich

## Datenbank-Schema

### Neue Tabelle: VacationYearApprovals

```sql
CREATE TABLE VacationYearApprovals (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    Year INTEGER NOT NULL UNIQUE,
    IsApproved INTEGER NOT NULL DEFAULT 0,
    ApprovedAt TEXT,
    ApprovedBy TEXT,
    CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ModifiedAt TEXT,
    Notes TEXT
)
```

**Felder:**
- `Year`: Das Jahr (z.B. 2025, 2026)
- `IsApproved`: 1 = Freigegeben, 0 = Nicht freigegeben
- `ApprovedAt`: Zeitstempel der Freigabe
- `ApprovedBy`: E-Mail des Administrators, der freigegeben hat
- `Notes`: Optional Notizen zur Freigabe

## API Endpoints

### 1. GET /api/vacationyearapprovals
Gibt alle Jahresfreigaben zurück (für alle Jahre).

**Authentifizierung:** Keine erforderlich (aber empfohlen)

**Response:**
```json
[
  {
    "id": 1,
    "year": 2025,
    "isApproved": true,
    "approvedAt": "2025-01-15T10:30:00",
    "approvedBy": "admin@fritzwinter.de",
    "createdAt": "2025-01-15T10:30:00",
    "modifiedAt": null,
    "notes": null
  }
]
```

### 2. GET /api/vacationyearapprovals/{year}
Prüft den Freigabestatus für ein bestimmtes Jahr.

**Parameter:**
- `year`: Jahr (z.B. 2025)

**Response (freigegeben):**
```json
{
  "id": 1,
  "year": 2025,
  "isApproved": true,
  "approvedAt": "2025-01-15T10:30:00",
  "approvedBy": "admin@fritzwinter.de",
  "createdAt": "2025-01-15T10:30:00",
  "modifiedAt": null,
  "notes": null,
  "exists": true
}
```

**Response (nicht freigegeben):**
```json
{
  "year": 2025,
  "isApproved": false,
  "exists": false
}
```

### 3. POST /api/vacationyearapprovals
Gibt ein Jahr frei oder zieht die Freigabe zurück.

**Authentifizierung:** Admin-Rolle erforderlich

**Request Body:**
```json
{
  "year": 2025,
  "isApproved": true,
  "notes": "Freigabe für Urlaubsplanung 2025"
}
```

**Response:**
```json
{
  "success": true,
  "id": 1,
  "year": 2025
}
```

### 4. GET /api/vacationyearplan/{year}
Gibt den Urlaubsjahresplan für ein bestimmtes Jahr zurück.

**Authentifizierung:** Keine erforderlich

**Parameter:**
- `year`: Jahr (z.B. 2025)

**Response (Jahr freigegeben):**
```json
{
  "year": 2025,
  "isApproved": true,
  "vacationRequests": [
    {
      "id": 1,
      "employeeId": 5,
      "employeeName": "Max Mustermann",
      "teamId": 1,
      "teamName": "Team A",
      "startDate": "2025-07-01",
      "endDate": "2025-07-14",
      "status": "Genehmigt",
      "notes": "Sommerurlaub",
      "source": "VacationRequest"
    }
  ],
  "absences": [
    {
      "id": 2,
      "employeeId": 8,
      "employeeName": "Maria Müller",
      "teamId": 2,
      "teamName": "Team B",
      "startDate": "2025-12-23",
      "endDate": "2025-12-31",
      "status": "Genehmigt",
      "notes": "Weihnachtsurlaub",
      "source": "Absence"
    }
  ]
}
```

**Response (Jahr nicht freigegeben):**
```json
{
  "year": 2025,
  "isApproved": false,
  "vacations": [],
  "message": "Urlaubsdaten für dieses Jahr wurden noch nicht freigegeben."
}
```

## Benutzeroberfläche

### Für alle Benutzer: Urlaubsjahresplan

**Navigation:** Hauptmenü → Urlaubsjahresplan

**Funktionen:**
1. Jahr auswählen (Dropdown mit aktuellen und zukünftigen Jahren)
2. "Laden" Button zum Anzeigen der Daten
3. Farbcodierte Legende:
   - 🔵 Blau = Genehmigter Urlaub
   - 🟠 Orange = Urlaub in Genehmigung
   - ⚫ Grau = Abgelehnter Urlaub
4. Tabellarische Übersicht mit:
   - Mitarbeitername
   - Team
   - Von-Datum
   - Bis-Datum
   - Anzahl Tage
   - Status (farbcodiert)
   - Notizen

**Hinweis bei nicht freigegebenem Jahr:**
> ⚠️ Jahr nicht freigegeben
> 
> Die Urlaubsdaten für dieses Jahr wurden noch nicht vom Administrator freigegeben.

### Für Administratoren: Jahresfreigabe

**Navigation:** Admin → Urlaubsjahresplan Freigabe

**Funktionen:**
1. Übersicht aller Jahre (aktuell ±5 Jahre)
2. Status-Anzeige:
   - ✓ Freigegeben (grün)
   - ✗ Nicht freigegeben (rot)
3. Aktionen:
   - "Freigeben" Button für nicht freigegebene Jahre
   - "Freigabe zurückziehen" Button für freigegebene Jahre
4. Anzeige von Freigabe-Details:
   - Freigegeben von (Benutzer)
   - Freigegeben am (Datum)

## Anwendungsbeispiele

### Beispiel 1: Jahr für Urlaubsplanung freigeben

1. Administrator meldet sich an
2. Navigiert zu: Admin → Urlaubsjahresplan Freigabe
3. Findet das gewünschte Jahr (z.B. 2026)
4. Klickt auf "Freigeben"
5. Bestätigt die Aktion
6. Jahr ist nun für alle Benutzer im Urlaubsjahresplan sichtbar

### Beispiel 2: Urlaubsjahresplan ansehen

1. Benutzer (beliebige Rolle) meldet sich an
2. Navigiert zu: Urlaubsjahresplan
3. Wählt das gewünschte Jahr aus
4. Klickt auf "Laden"
5. Sieht alle Urlaube für dieses Jahr (falls freigegeben)
6. Farbcodierung zeigt Genehmigungsstatus

### Beispiel 3: Farbcodierung im Dienstplan

Die Farbcodierung ist auch in allen Dienstplan-Ansichten (Woche, Monat, Jahr) sichtbar:

- **Wochenansicht**: "U" Badge in entsprechender Farbe
- **Monatsansicht**: "U" Badge in entsprechender Farbe
- **Jahresansicht**: "U" Badge in entsprechender Farbe

## CSS-Klassen

```css
/* Approved vacation - Blue */
.shift-U { 
    background: #2196F3; 
    color: #fff; 
}

/* Pending vacation - Orange */
.shift-U-pending { 
    background: #FF9800; 
    color: #fff; 
}

/* Rejected vacation - Gray */
.shift-U-rejected { 
    background: #9E9E9E; 
    color: #fff; 
}
```

## JavaScript-Funktionen

### Hauptfunktionen

- `initVacationYearPlan()`: Initialisiert die Jahresauswahl
- `loadVacationYearPlan()`: Lädt den Urlaubsjahresplan für das ausgewählte Jahr
- `displayVacationYearPlan(data, year)`: Zeigt die Urlaubsdaten in Tabellenform an
- `loadVacationYearApprovals()`: Lädt alle Jahresfreigaben (Admin)
- `displayVacationYearApprovals(approvals)`: Zeigt die Freigaben-Tabelle an (Admin)
- `toggleYearApproval(year, approve)`: Gibt ein Jahr frei oder zieht die Freigabe zurück (Admin)
- `createAbsenceBadge(absence)`: Erstellt ein farbcodiertes Abwesenheits-Badge

## Migration

Die Migration wird automatisch beim ersten Start ausgeführt durch:
```bash
python migrate_add_vacation_year_approvals.py
```

Diese erstellt die `VacationYearApprovals` Tabelle und den Index.

## Sicherheit

- **Jahresfreigabe**: Nur Administratoren können Jahre freigeben/sperren
- **Urlaubsjahresplan ansehen**: Alle authentifizierten Benutzer können freigegebene Jahre ansehen
- **Audit Log**: Alle Freigabe-Aktionen werden im Audit Log protokolliert

## Datenschutz

- Urlaubsdaten werden nur für freigegebene Jahre angezeigt
- Nicht freigegebene Jahre sind komplett unsichtbar für normale Benutzer
- Administratoren können die Freigabe jederzeit zurückziehen

## Best Practices

1. **Freigabe am Jahresanfang**: Geben Sie das neue Jahr zu Beginn des Jahres frei, wenn die Urlaubsplanung abgeschlossen ist
2. **Historische Daten**: Vergangene Jahre können freigegeben bleiben für Archivzwecke
3. **Zukünftige Planung**: Geben Sie zukünftige Jahre erst frei, wenn die grobe Urlaubsplanung steht
4. **Kommunikation**: Informieren Sie Mitarbeiter, wenn ein Jahr freigegeben wurde

## Fehlerbehebung

### Problem: "Jahr nicht freigegeben" obwohl ich Administrator bin

**Lösung:** Auch Administratoren müssen Jahre explizit freigeben. Gehen Sie zu Admin → Urlaubsjahresplan Freigabe und geben Sie das Jahr frei.

### Problem: Urlaubsantrag wird nicht im Jahresplan angezeigt

**Mögliche Ursachen:**
1. Jahr ist nicht freigegeben → Administrator muss Jahr freigeben
2. Urlaubsantrag liegt außerhalb des ausgewählten Jahres → Korrektes Jahr auswählen
3. Cache-Problem → Seite neu laden (F5)

### Problem: Farben werden nicht korrekt angezeigt

**Lösung:** 
1. Browser-Cache leeren (Strg+F5)
2. Prüfen, ob CSS-Datei korrekt geladen wurde
3. Browser-Entwicklertools (F12) → Console auf Fehler prüfen

## Technische Details

### Datenfluss

1. **Urlaubsantrag erstellen** → `VacationRequests` Tabelle
2. **Antrag genehmigen** → Status = 'Genehmigt' in `VacationRequests`
3. **Jahr freigeben** → Eintrag in `VacationYearApprovals` erstellen
4. **Jahresplan laden** → 
   - Prüft `VacationYearApprovals`
   - Wenn freigegeben: Lädt Daten aus `VacationRequests` und `Absences`
   - Kombiniert und gruppiert nach Mitarbeiter
   - Zeigt farbcodiert an

### Performanz

- Index auf `VacationYearApprovals.Year` für schnelle Abfragen
- Daten werden nur bei Bedarf geladen (on-demand)
- Gruppierung erfolgt clientseitig in JavaScript

## Erweiterungsmöglichkeiten

Zukünftige mögliche Erweiterungen:

1. **Excel-Export**: Urlaubsjahresplan als Excel-Datei exportieren
2. **Team-Filter**: Nur Urlaube eines bestimmten Teams anzeigen
3. **Kalenderansicht**: Grafische Kalendardarstellung statt Tabelle
4. **Statistiken**: Urlaubstage-Statistik pro Mitarbeiter/Team
5. **Benachrichtigungen**: E-Mail-Benachrichtigung bei Jahresfreigabe

## Support

Bei Fragen oder Problemen wenden Sie sich an:
- IT-Support: support@fritzwinter.de
- Entwickler: Timo Braun

---

**Version:** 1.0  
**Datum:** Januar 2026  
**Autor:** Timo Braun
