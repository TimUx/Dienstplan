# Lösung für INFEASIBLE Schichtplanungsfehler

## Zusammenfassung

Der Schichtplaner zeigte "INFEASIBLE - No solution exists!" wenn Teams leere `allowed_shift_type_ids` hatten oder falsch konfiguriert waren. Das Problem wurde durch automatische Zuweisung der F, S, N Schichten zu Teams ohne konfigurierte Schichtzuweisungen gelöst.

## Das Problem

### Symptome
- CP-SAT Solver gibt "INFEASIBLE" zurück
- Keine Schichtplanung möglich
- Diagnose zeigt: "0 Teams können F-N-S-Rotation durchführen"
- Oder: "Schicht F/S/N: 0 verfügbar / X benötigt"

### Ursache
Das System erwartet, dass Teams die Schichten F (Früh), S (Spät), N (Nacht) arbeiten können, um die F→N→S Rotation zu erfüllen. Wenn:

1. **Keine TeamShiftAssignments in der Datenbank** → Teams hatten leere `allowed_shift_type_ids`
2. **Falsche Schichtzuweisungen** → Teams haben z.B. nur ZD, BMT, BSB (nicht F, S, N)
3. **Inkonsistente Konfiguration** → Einige Teams haben Zuweisungen, andere nicht

Dann können:
- ❌ Teams KEINE F, S, N Schichten arbeiten
- ❌ Personalbedarfsanforderungen KÖNNEN NICHT erfüllt werden (F: 4 Mitarbeiter, S: 3, N: 3)
- ❌ Solver findet KEINE gültige Lösung → **INFEASIBLE**

## Die Lösung

### Automatische Zuweisung von F, S, N

Die Datei `data_loader.py` wurde geändert, um automatisch F, S, N Schichten zu Teams zuzuweisen, die keine `TeamShiftAssignments` in der Datenbank haben:

```python
# Auto-Zuweisung F, S, N für Teams ohne Konfiguration (Rückwärtskompatibilität)
if not team.allowed_shift_type_ids and not team.is_virtual:
    # Finde F, S, N Schicht-IDs aus geladenen Schichttypen
    f_id = next((st.id for st in shift_types if st.code == "F"), None)
    s_id = next((st.id for st in shift_types if st.code == "S"), None)
    n_id = next((st.id for st in shift_types if st.code == "N"), None)
    
    # Nur zuweisen wenn alle drei Schichten existieren
    if f_id and s_id and n_id:
        team.allowed_shift_type_ids = [f_id, s_id, n_id]
        print(f"  Auto-Zuweisung F, S, N Schichten für {team.name} (keine TeamShiftAssignments gefunden)")
```

### Vorteile
- ✅ **Verhindert INFEASIBLE**: Teams haben immer mindestens F, S, N
- ✅ **Rückwärtskompatibel**: Bestehende Systeme ohne TeamShiftAssignments funktionieren weiter
- ✅ **Klares Verhalten**: Log-Meldung zeigt, wann Auto-Zuweisung erfolgt
- ✅ **Sicher**: Nur für nicht-virtuelle Teams, nur wenn F,S,N existieren

### Was passiert jetzt?

#### Beim Laden der Daten
Sie sehen eine Meldung wie:
```
Loading data from database...
  Auto-Zuweisung F, S, N Schichten für Team 1 (keine TeamShiftAssignments gefunden)
  Auto-Zuweisung F, S, N Schichten für Team 2 (keine TeamShiftAssignments gefunden)
  Auto-Zuweisung F, S, N Schichten für Team 3 (keine TeamShiftAssignments gefunden)
```

Dies zeigt an, dass Teams automatisch für F, S, N Schichten konfiguriert wurden.

#### Bei der Planung
- ✅ Teams können F→N→S Rotation durchführen
- ✅ Personalbedarfsanforderungen können erfüllt werden
- ✅ Solver findet OPTIMALE Lösung
- ✅ Schichtplan wird erfolgreich erstellt

## Tests

### Vorher (INFEASIBLE)
```
Team Configuration:
  ✗ Team 1: 5 members, allowed shifts: 0 shifts, participates_in_rotation=False
  ✗ Team 2: 5 members, allowed shifts: 0 shifts, participates_in_rotation=False
  ✗ Team 3: 5 members, allowed shifts: 0 shifts, participates_in_rotation=False

Shift Staffing Analysis:
  ✗ F: 0 eligible / 4 required
  ✗ N: 0 eligible / 3 required
  ✗ S: 0 eligible / 3 required

Result: INFEASIBLE - No solution exists!
```

### Nachher (OPTIMAL)
```
Team Configuration:
  ✓ Team 1: 5 members, allowed shifts: [F, S, N], participates_in_rotation=True
  ✓ Team 2: 5 members, allowed shifts: [F, S, N], participates_in_rotation=True
  ✓ Team 3: 5 members, allowed shifts: [F, S, N], participates_in_rotation=True

Shift Staffing Analysis:
  ✓ F: 15 eligible / 4 required
  ✓ N: 15 eligible / 3 required
  ✓ S: 15 eligible / 3 required

Result: OPTIMAL solution found! (15.06 seconds)
Total assignments: 405
```

## Migration

### Keine Datenbankänderungen erforderlich
Die Lösung funktioniert automatisch ohne Änderungen an der Datenbank. 

### Optional: TeamShiftAssignments konfigurieren
Wenn Sie explizit steuern möchten, welche Teams welche Schichten arbeiten, fügen Sie Einträge in die `TeamShiftAssignments` Tabelle ein:

```sql
-- Beispiel: Team 1 kann F, S, N Schichten arbeiten
-- (Angenommen: F=1, S=2, N=3)
INSERT INTO TeamShiftAssignments (TeamId, ShiftTypeId, CreatedBy)
VALUES 
  (1, 1, 'admin'),  -- F
  (1, 2, 'admin'),  -- S
  (1, 3, 'admin');  -- N

-- Wiederholen für andere Teams
```

## Bekannte Szenarien

### Szenario 1: Leere TeamShiftAssignments Tabelle
- **Situation**: Keine Einträge in TeamShiftAssignments
- **Verhalten**: Alle Teams bekommen automatisch F, S, N
- **Ergebnis**: ✅ OPTIMAL

### Szenario 2: Explizite F, S, N Zuweisungen
- **Situation**: Teams haben TeamShiftAssignments mit F, S, N
- **Verhalten**: Konfiguration wird verwendet, keine Auto-Zuweisung
- **Ergebnis**: ✅ OPTIMAL

### Szenario 3: Falsche Schichtzuweisungen
- **Situation**: Teams haben nur ZD, BMT, BSB (NICHT F, S, N)
- **Verhalten**: Keine Auto-Zuweisung (bereits konfiguriert)
- **Ergebnis**: ❌ INFEASIBLE (wie erwartet - Fehlkonfiguration)
- **Lösung**: Korrigieren Sie die TeamShiftAssignments in der Datenbank

## Diagnose bei Problemen

Wenn Sie immer noch INFEASIBLE sehen:

### 1. Prüfen Sie die Ausgabe
Suchen Sie nach:
```
✗ Team X: participates_in_rotation=False
```

### 2. Prüfen Sie TeamShiftAssignments
```sql
SELECT t.Name, st.Code, st.Name
FROM TeamShiftAssignments tsa
JOIN Teams t ON t.Id = tsa.TeamId
JOIN ShiftTypes st ON st.Id = tsa.ShiftTypeId
ORDER BY t.Id;
```

### 3. Korrigieren Sie falsche Zuweisungen
Wenn Teams NICHT F, S, N haben:
```sql
-- Löschen Sie falsche Zuweisungen
DELETE FROM TeamShiftAssignments WHERE TeamId = X;

-- System wird automatisch F, S, N zuweisen beim nächsten Laden
```

Oder fügen Sie F, S, N explizit hinzu:
```sql
INSERT INTO TeamShiftAssignments (TeamId, ShiftTypeId, CreatedBy)
SELECT 1, Id, 'admin' FROM ShiftTypes WHERE Code IN ('F', 'S', 'N');
```

## Geänderte Dateien

- ✅ `data_loader.py` - Auto-Zuweisung F,S,N für Teams ohne Konfiguration
- ✅ `AUTO_ASSIGN_FIX.md` - Englische Dokumentation
- ✅ `LOESUNG_INFEASIBLE.md` - Diese deutsche Dokumentation
- ✅ `test_infeasible_with_allowed_shifts.py` - Test mit expliziten Zuweisungen
- ✅ `test_infeasible_wrong_shifts.py` - Test mit falschen Zuweisungen

## Sicherheit

✅ CodeQL-Scan durchgeführt: Keine Sicherheitsprobleme gefunden

## Zusammenfassung

Das INFEASIBLE Problem wurde durch automatische Zuweisung von F, S, N Schichten zu Teams ohne `TeamShiftAssignments` gelöst. Die Lösung ist:

- **Einfach**: Keine Datenbankänderungen erforderlich
- **Sicher**: Nur für nicht-virtuelle Teams, nur wenn F,S,N existieren
- **Transparent**: Log-Meldungen zeigen, wann Auto-Zuweisung erfolgt
- **Rückwärtskompatibel**: Bestehende Systeme funktionieren weiter

Der Schichtplaner sollte jetzt OPTIMALE Lösungen finden und Schichtpläne erfolgreich erstellen können.
