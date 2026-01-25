# Export/Import Funktionalität für Mitarbeiter und Teams

## Status

Die Export/Import-Funktionalität existiert **nur im Backend (API)**, ist aber **NICHT im Web-UI verlinkt**.

## API-Endpunkte (Verfügbar)

Die folgenden Endpunkte sind im Backend implementiert (`web_api.py`, Zeilen 5544-5915):

### Mitarbeiter Export
- **Endpunkt**: `GET /api/employees/export/csv`
- **Berechtigung**: Admin
- **Beschreibung**: Exportiert alle Mitarbeiter in CSV-Format
- **Ausgabe**: CSV-Datei mit allen Mitarbeiterdaten

### Mitarbeiter Import
- **Endpunkt**: `POST /api/employees/import/csv`
- **Berechtigung**: Admin
- **Parameter**: 
  - `file`: CSV-Datei
  - `conflict_resolution`: "overwrite" oder "skip"
- **Beschreibung**: Importiert Mitarbeiter aus CSV-Datei

### Team Export
- **Endpunkt**: `GET /api/teams/export/csv`
- **Berechtigung**: Admin
- **Beschreibung**: Exportiert alle Teams in CSV-Format
- **Ausgabe**: CSV-Datei mit allen Team-Daten

### Team Import
- **Endpunkt**: `POST /api/teams/import/csv`
- **Berechtigung**: Admin
- **Parameter**:
  - `file`: CSV-Datei
  - `conflict_resolution`: "overwrite" oder "skip"
- **Beschreibung**: Importiert Teams aus CSV-Datei

## Wo die Funktionen im UI fehlen

Die Export/Import-Buttons fehlen in der **Verwaltung**-Ansicht:

### Empfohlene Position

**Ansicht**: Verwaltung → Mitarbeiter Tab
- Button: "📤 Mitarbeiter exportieren (CSV)" → ruft `/api/employees/export/csv` auf
- Button: "📥 Mitarbeiter importieren (CSV)" → öffnet Datei-Uploader für `/api/employees/import/csv`

**Ansicht**: Verwaltung → Teams Tab
- Button: "📤 Teams exportieren (CSV)" → ruft `/api/teams/export/csv` auf
- Button: "📥 Teams importieren (CSV)" → öffnet Datei-Uploader für `/api/teams/import/csv`

## Manuelle Nutzung (Aktueller Workaround)

Bis die UI-Integration erfolgt, können die Endpunkte manuell aufgerufen werden:

### Export (cURL):
```bash
# Mitarbeiter Export
curl -X GET "http://localhost:5000/api/employees/export/csv" \
  --cookie "session=YOUR_SESSION_COOKIE" \
  -o employees_export.csv

# Teams Export
curl -X GET "http://localhost:5000/api/teams/export/csv" \
  --cookie "session=YOUR_SESSION_COOKIE" \
  -o teams_export.csv
```

### Import (cURL):
```bash
# Mitarbeiter Import
curl -X POST "http://localhost:5000/api/employees/import/csv?conflict_resolution=skip" \
  --cookie "session=YOUR_SESSION_COOKIE" \
  -F "file=@employees.csv"

# Teams Import  
curl -X POST "http://localhost:5000/api/teams/import/csv?conflict_resolution=skip" \
  --cookie "session=YOUR_SESSION_COOKIE" \
  -F "file=@teams.csv"
```

## CSV-Format

### Mitarbeiter CSV
```
Vorname,Name,Personalnummer,Email,Geburtsdatum,Funktion,TeamId,IsSpringer,IsFerienjobber,IsBrandmeldetechniker,IsBrandschutzbeauftragter,IsTdQualified,IsTeamLeader,IsActive
Max,Müller,PN001,max.mueller@example.com,1990-01-15,Schichtleiter,1,0,0,0,0,1,1,1
```

### Teams CSV
```
Name,Description,Email,IsVirtual
Team Alpha,Erste Schichtgruppe,team.alpha@example.com,0
```

## Nächste Schritte für UI-Integration

1. In `/wwwroot/index.html` Buttons hinzufügen:
   - Im Mitarbeiter-Tab: Export/Import Buttons
   - Im Teams-Tab: Export/Import Buttons

2. In `/wwwroot/js/app.js` JavaScript-Funktionen erstellen:
   - `exportEmployeesCsv()` - ruft API auf und lädt Datei herunter
   - `importEmployeesCsv()` - öffnet Datei-Dialog und sendet an API
   - `exportTeamsCsv()` - ruft API auf und lädt Datei herunter
   - `importTeamsCsv()` - öffnet Datei-Dialog und sendet an API

3. Beispiel-Implementation für Export-Button:
```javascript
async function exportEmployeesCsv() {
    try {
        const response = await fetch(`${API_BASE}/employees/export/csv`, {
            credentials: 'include'
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `employees_${new Date().toISOString().split('T')[0]}.csv`;
            a.click();
            window.URL.revokeObjectURL(url);
        }
    } catch (error) {
        console.error('Export error:', error);
        alert('Fehler beim Export');
    }
}
```

## Zusammenfassung

✅ **Backend API**: Vollständig implementiert und funktionsfähig  
❌ **Web UI**: Keine Buttons/Links zu den Export/Import-Funktionen  
📋 **Dokumentation**: Diese Datei beschreibt die verfügbaren Endpunkte und wo sie im UI eingefügt werden sollten
