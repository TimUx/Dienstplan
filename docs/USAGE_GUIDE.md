# Dienstplan - Benutzerhandbuch

## Übersicht

Dieses Handbuch beschreibt die Nutzung des Dienstplan-Systems für die automatische Schichtplanung mit Python und Google OR-Tools.

## Installation

### Voraussetzungen
- Python 3.9 oder höher
- pip (Python Package Manager)

### Schnellinstallation
```bash
# Repository klonen
git clone https://github.com/TimUx/Dienstplan.git
cd Dienstplan

# Virtuelle Umgebung erstellen (empfohlen)
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# oder
venv\Scripts\activate     # Windows

# Abhängigkeiten installieren
pip install -r requirements.txt
```

## Verwendung

### 1. Web-Server starten

Der einfachste Weg, das System zu nutzen, ist über die Web-Oberfläche:

```bash
python main.py serve
```

Standardmäßig läuft der Server auf `http://localhost:5000`

**Optionale Parameter:**
```bash
# Auf anderem Port
python main.py serve --port 8080

# Auf anderer Adresse (z.B. für Zugriff im Netzwerk)
python main.py serve --host 0.0.0.0 --port 8080

# Mit spezifischer Datenbank
python main.py serve --db /pfad/zur/datenbank.db
```

### 2. Erstanmeldung

Beim ersten Start wird automatisch ein Administrator-Konto erstellt:

- **E-Mail**: admin@fritzwinter.de
- **Passwort**: Admin123!

**WICHTIG**: Ändern Sie das Passwort nach der ersten Anmeldung!

### 3. Mitarbeiter und Teams verwalten

#### Mitarbeiter hinzufügen
1. Navigieren Sie zu **Mitarbeiter** im Menü
2. Klicken Sie auf **Neuer Mitarbeiter**
3. Füllen Sie die Pflichtfelder aus:
   - Vorname
   - Name
   - Personalnummer
4. Optional:
   - Team zuordnen
   - Als Springer markieren
   - Qualifikationen festlegen (BMT/BSB)

#### Teams erstellen
1. Navigieren Sie zu **Teams** im Menü
2. Klicken Sie auf **Neues Team**
3. Geben Sie Namen und Beschreibung ein

### 4. Schichtplanung durchführen

#### Automatische Planung über Web UI
1. Wechseln Sie zur **Dienstplan**-Ansicht
2. Wählen Sie den gewünschten Zeitraum
3. Klicken Sie auf **Automatisch planen**
4. Warten Sie auf die Berechnung
5. Überprüfen Sie das Ergebnis

#### Automatische Planung über CLI
Für größere Planungszeiträume oder Batch-Verarbeitung:

```bash
# Mit vorhandener Datenbank
python main.py plan \
  --start-date 2025-01-01 \
  --end-date 2025-01-31 \
  --db dienstplan.db

# Mit Test-Daten (für Entwicklung)
python main.py plan \
  --start-date 2025-01-01 \
  --end-date 2025-01-31 \
  --sample-data

# Mit erhöhtem Zeitlimit (für komplexe Planungen)
python main.py plan \
  --start-date 2025-01-01 \
  --end-date 2025-01-31 \
  --time-limit 600
```

### 5. Abwesenheiten verwalten

#### Abwesenheit erfassen
1. Navigieren Sie zu **Abwesenheiten**
2. Klicken Sie auf **Neue Abwesenheit**
3. Wählen Sie:
   - Mitarbeiter
   - Art (Urlaub, Krank, Lehrgang)
   - Start- und Enddatum
4. Optional: Notizen hinzufügen

#### Urlaubsanträge bearbeiten (Admin/Disponent)
1. Navigieren Sie zu **Urlaubsanträge**
2. Sehen Sie alle offenen Anträge
3. Genehmigen oder ablehnen Sie Anträge
4. Genehmigte Anträge werden automatisch zu Abwesenheiten

### 6. Diensttausch-System

#### Als Mitarbeiter: Dienst zum Tausch anbieten
1. Navigieren Sie zu **Diensttausch**
2. Wählen Sie einen Ihrer Dienste
3. Geben Sie einen Grund an
4. Warten Sie auf Interessenten

#### Als anderer Mitarbeiter: Dienst anfragen
1. Sehen Sie verfügbare Tauschangebote
2. Wählen Sie einen Dienst aus
3. Stellen Sie eine Anfrage

#### Als Disponent/Admin: Tausch genehmigen
1. Navigieren Sie zu **Diensttausch**
2. Sehen Sie offene Anfragen
3. Genehmigen oder ablehnen Sie den Tausch
4. Nach Genehmigung werden die Dienste automatisch getauscht

## Planungsalgorithmus

### Automatische Schichtplanung mit OR-Tools

Das System verwendet den **Google OR-Tools CP-SAT Constraint Solver** für optimale Schichtplanung.

### Implementierte Regeln

#### Harte Constraints (müssen eingehalten werden)

**Grundregeln:**
- ✅ Maximal 1 Schicht pro Mitarbeiter und Tag
- ✅ Keine Arbeit während Abwesenheit

**Mindestbesetzung:**
- ✅ Früh: 4-5 Personen (Mo-Fr), 2-3 (Sa-So)
- ✅ Spät: 3-4 Personen (Mo-Fr), 2-3 (Sa-So)
- ✅ Nacht: 3 Personen (Mo-Fr), 2-3 (Sa-So)

**Ruhezeiten:**
- ✅ Minimum 11 Stunden zwischen Schichten
- ✅ Verbotene Übergänge: Spät→Früh, Nacht→Früh

**Arbeitszeitbeschränkungen:**
- ✅ Max. 6 aufeinanderfolgende Dienste
- ✅ Max. 5 aufeinanderfolgende Nachtdienste
- ✅ Max. 48 Stunden pro Woche
- ✅ Max. 192 Stunden pro Monat

**Zusatzfunktionen:**
- ✅ 1 BMT (Brandmeldetechniker) pro Werktag (Mo-Fr)
- ✅ 1 BSB (Brandschutzbeauftragter) pro Werktag (Mo-Fr)
- ✅ Nur qualifizierte Mitarbeiter

**Springer-Logik:**
- ✅ Mindestens 1 Springer muss verfügbar bleiben
- ✅ Teamübergreifender Einsatz möglich

#### Weiche Constraints (werden optimiert)

**Fairness:**
- ⚖️ Gleichmäßige Schichtverteilung über alle Mitarbeiter
- ⚖️ Bevorzugter Rhythmus: Früh → Nacht → Spät

### Solver-Konfiguration

Die Solver-Parameter können in `solver.py` angepasst werden:

```python
# Zeitlimit (in Sekunden)
solver.parameters.max_time_in_seconds = 300  # 5 Minuten

# Anzahl paralleler Worker
solver.parameters.num_search_workers = 8

# Such-Fortschritt loggen
solver.parameters.log_search_progress = True
```

## REST API

### Authentifizierung

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

### Mitarbeiter

#### Alle Mitarbeiter abrufen
```http
GET /api/employees
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

### Schichtplanung

#### Dienstplan anzeigen
```http
GET /api/shifts/schedule?startDate=2025-01-01&view=week
```

Parameter:
- `startDate`: Startdatum (ISO Format: YYYY-MM-DD)
- `view`: week, month, oder year
- `endDate`: Optional, überschreibt view

#### Automatisch planen
```http
POST /api/shifts/plan?startDate=2025-01-01&endDate=2025-01-31&force=false
Authorization: Required (Admin oder Disponent)
```

Parameter:
- `startDate`: Startdatum
- `endDate`: Enddatum
- `force`: Vorhandene Schichten überschreiben (optional, default: false)

### Statistiken

#### Dashboard
```http
GET /api/statistics/dashboard?startDate=2025-01-01&endDate=2025-01-31
```

#### Wochenend-Statistiken
```http
GET /api/statistics/weekend-shifts?startDate=2025-01-01&endDate=2025-12-31
Authorization: Required (Admin oder Disponent)
```

## Tipps & Best Practices

### Schichtplanung

1. **Planen Sie rechtzeitig**: Erstellen Sie Pläne mindestens 2 Wochen im Voraus
2. **Überprüfen Sie Abwesenheiten**: Stellen Sie sicher, dass alle bekannten Abwesenheiten erfasst sind
3. **Nutzen Sie Springer**: Markieren Sie geeignete Mitarbeiter als Springer für Flexibilität
4. **Zeitlimits anpassen**: Bei komplexen Planungen erhöhen Sie das Solver-Zeitlimit

### Performance

1. **Planungszeiträume**: Planen Sie nicht mehr als 2 Monate auf einmal
2. **Sample-Data für Tests**: Verwenden Sie `--sample-data` für Entwicklung und Tests
3. **Datenbank-Wartung**: Löschen Sie alte Daten regelmäßig (z.B. älter als 2 Jahre)

### Sicherheit

1. **Passwörter ändern**: Ändern Sie Standard-Passwörter sofort
2. **HTTPS verwenden**: Setzen Sie einen Reverse Proxy (nginx/Apache) vor Flask
3. **Backups**: Sichern Sie die Datenbank regelmäßig
4. **Updates**: Halten Sie Python und alle Packages aktuell

## Fehlerbehebung

### Problem: Keine Lösung gefunden

**Ursachen:**
- Zu viele Abwesenheiten für den Zeitraum
- Zu wenige Mitarbeiter
- Zu restriktive Constraints

**Lösungen:**
- Zeitlimit erhöhen: `--time-limit 600`
- Zeitraum verkürzen (z.B. 2 Wochen statt Monat)
- Mehr Springer hinzufügen
- Abwesenheiten überprüfen

### Problem: Server startet nicht

**Ursachen:**
- Port bereits belegt
- Datenbank nicht gefunden
- Dependencies nicht installiert

**Lösungen:**
```bash
# Anderen Port verwenden
python main.py serve --port 8080

# Dependencies neu installieren
pip install -r requirements.txt --force-reinstall

# Datenbank-Pfad prüfen
python main.py serve --db ./dienstplan.db
```

### Problem: Web UI zeigt keine Daten

**Ursachen:**
- Datenbank leer
- Falsche Datenbank verwendet
- CORS-Problem

**Lösungen:**
- Datenbank mit Sample-Daten erstellen
- Datenbank-Pfad überprüfen
- Browser-Konsole auf Fehler prüfen

## Support

Bei weiteren Fragen:
- **GitHub Issues**: https://github.com/TimUx/Dienstplan/issues
- **Dokumentation**: README.md, ARCHITECTURE.md
- **Migration-Info**: MIGRATION.md

---

**Version 2.0 - Python Edition**

© 2025 Fritz Winter Eisengießerei GmbH & Co. KG
