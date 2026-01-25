# Zusammenfassung der Behebung

## Problem
Beim Erstellen eines Schichtplans trat folgender Fehler auf: **"no such column"**

## Ursache
In der Datei `web_api.py` (Zeile 2683-2693) versuchte eine SQL-Abfrage, Spalten aus der Tabelle `TeamShiftAssignments` zu selektieren, die dort nicht existieren:
- Die Abfrage versuchte `TeamId, Date, ShiftTypeCode` aus `TeamShiftAssignments` zu holen
- `TeamShiftAssignments` ist aber eine Konfigurations-Tabelle (welche Teams welche Schichten arbeiten können)
- Sie enthält keine `Date` oder `ShiftTypeCode` Spalten

## Lösung
Die SQL-Abfrage wurde korrigiert, um die richtigen Tabellen zu verwenden:
```sql
SELECT e.TeamId, sa.Date, st.Code
FROM ShiftAssignments sa
INNER JOIN Employees e ON sa.EmployeeId = e.Id
INNER JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
WHERE sa.Date >= ? AND sa.Date <= ?
AND (sa.Date < ? OR sa.Date > ?)
AND e.TeamId IS NOT NULL
```

Dies holt die tatsächlichen Schichtzuweisungen (ShiftAssignments) und verknüpft sie mit:
- `Employees` um die TeamId zu erhalten
- `ShiftTypes` um den Schicht-Code zu erhalten

## Tests
✅ **SQL-Abfrage getestet**: Funktioniert ohne Fehler  
✅ **Code Review durchgeführt**: Keine weiteren Probleme gefunden  
✅ **Sicherheitsscan (CodeQL)**: Keine Sicherheitsprobleme gefunden  
✅ **Realistische Parameter wiederhergestellt**: F=4/10, N=2/10, S=3/10

## Export/Import Funktionalität

### Status
Die Export/Import-Funktionalität für Mitarbeiter und Teams existiert **NUR im Backend (API)**, ist aber **NICHT im Web-UI verlinkt**.

### Verfügbare API-Endpunkte
- `GET /api/employees/export/csv` - Mitarbeiter exportieren
- `POST /api/employees/import/csv` - Mitarbeiter importieren
- `GET /api/teams/export/csv` - Teams exportieren
- `POST /api/teams/import/csv` - Teams importieren

### Wo die Buttons sein sollten
Die Export/Import-Buttons sollten in der **Verwaltung**-Ansicht hinzugefügt werden:
- **Mitarbeiter Tab**: Buttons für Mitarbeiter-Export/Import
- **Teams Tab**: Buttons für Team-Export/Import

### Dokumentation
Siehe `EXPORT_IMPORT_DOKUMENTATION.md` für:
- Vollständige API-Dokumentation
- Manuelle Nutzung via cURL (Workaround)
- CSV-Format-Beispiele
- Empfehlungen zur UI-Integration

## Dateien geändert
1. `web_api.py` - SQL-Abfrage korrigiert (Zeile 2681-2693)
2. `EXPORT_IMPORT_DOKUMENTATION.md` - Neue Dokumentation erstellt

## Nächste Schritte (Optional)
Wenn Sie die Export/Import-Funktionen im Web-UI hinzufügen möchten:
1. Buttons in `wwwroot/index.html` hinzufügen (im Verwaltung-Bereich)
2. JavaScript-Funktionen in `wwwroot/js/app.js` erstellen
3. Siehe `EXPORT_IMPORT_DOKUMENTATION.md` für Beispiel-Code
