# Fix: Abwesenheiten entfernen geplante Schichten korrekt

## Problem

Wenn ein Mitarbeiter bereits Schichten verplant hatte und nachträglich als abwesend gemeldet wurde (AU, Urlaub oder Lehrgang), wurden die geplanten Schichten **nicht** aus der Datenbank entfernt. Dies führte zu falschen Statistiken:

**Beispiel:**
- Mitarbeiter "A" hat 208h für einen Monat geplant (26 Schichten × 8h)
- Mitarbeiter "A" wird für 7 Tage AU (krank) gemeldet, in denen 5 Schichten (40h) geplant waren
- Die Statistik zeigte weiterhin 208h statt korrekter 168h (208h - 40h)

## Ursache

Die Funktion `process_absence_with_springer_assignment()` in `springer_replacement.py` hat zwar Springer gesucht, aber die ursprünglichen Schichten des abwesenden Mitarbeiters nicht gelöscht.

## Lösung

### 1. Schichten werden automatisch entfernt

Die Funktion `process_absence_with_springer_assignment()` wurde erweitert:
- Findet alle betroffenen Schichten
- **Löscht diese Schichten aus der Datenbank**
- Sucht dann Springer-Ersatz für die gelöschten Schichten
- Alle Änderungen werden in einer Transaktion committed (Atomarität)

### 2. Statistik-Berechnung für alle Abwesenheitstypen

Die Statistik-Berechnung in `web_api.py` wurde aktualisiert:

| Abwesenheitstyp | Schichten entfernen | Stunden zählen |
|----------------|---------------------|----------------|
| **AU** (Krank/AU) | ✅ Ja | ❌ Nein |
| **U** (Urlaub) | ✅ Ja | ❌ Nein |
| **L** (Lehrgang) | ✅ Ja | ✅ Ja (8h/Tag) |

**Besonderheit Lehrgang (L):**
- Schichten werden entfernt wie bei AU und Urlaub
- **ABER:** Lehrgangstage werden trotzdem mit 8h pro Tag in der Statistik gezählt
- Dies ist wichtig für die korrekte Erfassung der Arbeitszeit

## Implementierungsdetails

### Datenbankänderungen

**Beim Erstellen einer Abwesenheit:**
```sql
-- 1. Betroffene Schichten finden
SELECT sa.Id, sa.Date, st.Code, st.Name
FROM ShiftAssignments sa
JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
WHERE sa.EmployeeId = ? 
  AND sa.Date BETWEEN ? AND ?

-- 2. Schichten löschen
DELETE FROM ShiftAssignments
WHERE Id IN (...)
```

### Statistik-Berechnung

**Schichtstunden:**
```sql
SELECT COUNT(sa.Id) as ShiftCount,
       COALESCE(SUM(st.DurationHours), 0) as ShiftHours
FROM ShiftAssignments sa
JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
WHERE sa.EmployeeId = ?
  AND sa.Date >= ? AND sa.Date <= ?
```

**Lehrgangstunden (separat):**
```sql
SELECT SUM(
    CASE
        WHEN a.StartDate >= ? AND a.EndDate <= ? THEN
            julianday(a.EndDate) - julianday(a.StartDate) + 1
        -- ... weitere Fälle für überlappende Zeiträume
    END
) * 8.0 as LehrgangHours
FROM Absences a
WHERE a.EmployeeId = ?
  AND a.Type = 'L'
  AND (Überlappung mit Zeitraum)
```

**Gesamtstunden:**
```
TotalHours = ShiftHours + LehrgangHours
```

## Tests

Zwei umfassende Tests wurden erstellt:

### Test 1: `test_absence_removes_shifts.py`
- Erstellt 26 Schichten für einen Mitarbeiter (208h)
- Meldet Mitarbeiter für 7 Tage AU
- Verifiziert: Schichten wurden entfernt (19 Schichten übrig)
- Verifiziert: Statistik zeigt korrekte Stunden (152h)

### Test 2: `test_lehrgang_statistics.py`
Testet alle 3 Abwesenheitstypen mit je 20 Schichten (160h):

**Employee 1 - AU (Krank):**
- Vor Abwesenheit: 20 Schichten, 160h
- 5 Tage AU (Jan 6-10)
- Nach Abwesenheit: 15 Schichten, 120h ✅

**Employee 2 - U (Urlaub):**
- Vor Abwesenheit: 20 Schichten, 160h
- 5 Tage Urlaub (Jan 6-10)
- Nach Abwesenheit: 15 Schichten, 120h ✅

**Employee 3 - L (Lehrgang):**
- Vor Abwesenheit: 20 Schichten, 160h
- 5 Tage Lehrgang (Jan 6-10)
- Nach Abwesenheit: 15 Schichten, aber 160h (120h Schichten + 40h Lehrgang) ✅

## Transaktionssicherheit

Die Implementierung stellt sicher, dass entweder **alle** Änderungen erfolgreich sind oder **keine**:

1. Schichten werden gelöscht
2. Springer werden zugewiesen
3. Erst dann wird committed

Falls ein Fehler auftritt, werden alle Änderungen zurückgerollt.

## Auswirkungen

### Für Benutzer
- ✅ Statistiken zeigen jetzt korrekte Arbeitsstunden
- ✅ Abwesende Mitarbeiter haben keine "Geister-Schichten" mehr
- ✅ Lehrgangstage werden korrekt als 8h gezählt (auch ohne Schicht)

### Für Administratoren
- ✅ Bessere Datenintegrität
- ✅ Korrekte Berichte und Auswertungen
- ✅ Automatische Springer-Zuweisung funktioniert weiterhin

### Für Entwickler
- ✅ Klare Trennung zwischen Schichten und Abwesenheiten
- ✅ Verbesserte Dokumentation und Kommentare
- ✅ Umfassende Tests für alle Abwesenheitstypen
- ✅ Keine Sicherheitslücken (CodeQL: 0 Warnungen)

## Migration

**Keine Migration erforderlich!**

Die Änderungen sind vollständig abwärtskompatibel:
- Bestehende Abwesenheiten funktionieren weiterhin
- Alte Schichten bleiben bestehen (werden nur bei **neuen** Abwesenheiten entfernt)
- Statistiken berechnen sich automatisch korrekt

Bei Bedarf kann ein Admin-Script erstellt werden, um alte "Geister-Schichten" nachträglich zu bereinigen.

## Zusammenfassung

✅ **Problem gelöst:** Schichten werden jetzt korrekt entfernt bei Abwesenheit  
✅ **Statistik korrekt:** AU/U zählen nicht, Lehrgang zählt 8h/Tag  
✅ **Transaktionssicherheit:** Atomare Operationen mit Rollback  
✅ **Tests:** Alle Tests bestanden  
✅ **Sicherheit:** Keine Schwachstellen gefunden  
✅ **Dokumentation:** Vollständig dokumentiert und kommentiert
