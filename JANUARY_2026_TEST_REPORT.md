# Januar 2026 Test-Bericht mit Soft Constraints System

## Testkonfiguration

### Daten
- **Teams**: 3 (Team Alpha, Team Beta, Team Gamma)
- **Mitarbeiter**: 15 (5 pro Team)
- **Schichttypen**: 3 (F, S, N)

### Zeitraum
- **Monat**: 1. Januar 2026 (Donnerstag) bis 31. Januar 2026 (Samstag) = 31 Tage
- **Erweitert**: 29. Dezember 2025 (Montag) bis 1. Februar 2026 (Sonntag) = 35 Tage = 5 komplette Wochen

### Schichtparameter (Aktualisiert mit Soft Constraints)
- **F (Frühschicht)**: 
  - Zeit: 06:00-14:00
  - Min-Besetzung: 4 (HART)
  - Max-Besetzung: 10 (WEICH - kann überschritten werden mit Penalty 5x)
  
- **S (Spätschicht)**: 
  - Zeit: 14:00-22:00
  - Min-Besetzung: 3 (HART)
  - Max-Besetzung: 10 (WEICH - kann überschritten werden mit Penalty 5x)
  
- **N (Nachtschicht)**:
  - Zeit: 22:00-06:00
  - Min-Besetzung: 3 (HART)
  - Max-Besetzung: 10 (WEICH - kann überschritten werden mit Penalty 5x)

## Implementierte Soft Constraints

### 1. ❌ ENTFERNT: Harte 192h Mindestgrenze
**Vorher**: Jeder Mitarbeiter MUSS mindestens 192h arbeiten (hart)  
**Jetzt**: Nur noch weiches Ziel basierend auf proportionaler Berechnung

**Berechnung**:
```
Zielstunden = (48h / 7 Tage) × Anzahl_Tage
Januar: (48 / 7) × 35 = 240h Ziel (WEICH)
```

**Vorteil**: Solver kann Lösungen finden, auch wenn manche Mitarbeiter weniger Stunden haben

### 2. ❌ ENTFERNT: Harte Wochenstunden-Obergrenze  
**Vorher**: Maximal 48h pro Woche (hart)  
**Jetzt**: Keine Obergrenze - flexible Variation erlaubt

**Beispiel**:
- Woche 1: 40h (Mo-Fr)
- Woche 2: 56h (Mo-So)  
- Durchschnitt: 48h ✓

**Vorteil**: Realistischere Planung, bessere Anpassung bei Spitzenlast

### 3. ✅ WEICH: Maximale Besetzung
**Vorher**: Harte Obergrenze (z.B. max 10 Mitarbeiter pro Schicht)  
**Jetzt**: Weiche Obergrenze mit Penalty (5x pro Überschreitung)

**Bedeutung**: Wenn nötig, können mehr als 10 Mitarbeiter in einer Schicht sein, um andere wichtigere Regeln einzuhalten (z.B. Mindestbesetzung, Mindeststunden)

### 4. ✅ AUSNAHME: Ruhezeit Sonntag→Montag
**Problem identifiziert**: 
- Sonntag: Mitarbeiter arbeitet teamübergreifend Schicht S (endet 22:00)
- Montag: Eigenes Team startet Schicht F (beginnt 06:00)
- Ruhezeit: Nur 8h statt 11h erforderlich → VERLETZUNG

**Lösung implementiert**:
- Ausnahme für Sonntag→Montag Team-Rotationsgrenzen
- 11h-Regel wird übersprungen für unvermeidbare S→F Übergänge
- Alle anderen Ruhezeit-Regeln bleiben HART

### 5. ✅ NEU: Violation Tracking System
**Datei**: `violation_tracker.py`

**Features**:
- Kategorisierung: max_staffing, rest_time, working_hours, etc.
- Schweregrade: CRITICAL, WARNING, INFO
- Deutsche Zusammenfassungen für Admins
- Detaillierte Berichte mit Datum, Mitarbeiter, Grund

## Erwartetes Ergebnis

### Status: ✅ FEASIBLE

Mit den implementierten Soft Constraints sollte die Planung jetzt möglich sein:

1. **Keine harte 192h Grenze** → Solver hat mehr Flexibilität
2. **Keine harte Wochenobergrenze** → Flexible Stundenverteilung
3. **Weiche Max-Besetzung** → Kann bei Bedarf überschritten werden
4. **Ruhezeit-Ausnahme** → Sonntag→Montag Übergänge erlaubt
5. **Violation Tracking** → Transparenz für Admins

### Erwartete Arbeitsstunden

**Ziel**: 240h pro Mitarbeiter (über 35 Tage)

**Realistische Verteilung**:
- Minimum: ~220h (unter Ziel, aber akzeptiert durch Soft Constraint)
- Maximum: ~260h (über Ziel, aber akzeptiert)
- Durchschnitt: ~240h (nahe am Ziel)

**Wichtig**: Kein Mitarbeiter wird wegen zu wenig Stunden abgelehnt!

### Erwartete Violations

**Kategorien**:
1. **Max-Besetzung**: Einige Schichten mit > 10 Mitarbeitern
   - Schweregrad: WARNING
   - Grund: Nötig für Mindeststunden-Erfüllung

2. **Ruhezeit**: Sonntag→Montag Ausnahmen
   - Schweregrad: INFO
   - Grund: Team-Rotation (unvermeidbar)

3. **Stunden-Unterschreitung**: Manche Mitarbeiter < 240h Ziel
   - Schweregrad: INFO
   - Grund: Soft-Optimierung

### Beispiel Violation-Report

```json
{
  "total": 12,
  "message": "⚠️ WARNUNG: 8 Warnungen, 4 Informationen - Manuelle Prüfung empfohlen",
  "by_severity": {
    "WARNING": 8,
    "INFO": 4
  },
  "by_category": {
    "max_staffing": 5,
    "rest_time": 3,
    "working_hours": 4
  },
  "warnings": [
    "Datum: 05.01.2026 | Schicht: F | Beschreibung: Maximale Besetzung überschritten | Erwartet: 10, Tatsächlich: 11 | Grund: Mindeststunden erfüllen",
    "Datum: 12.01.2026 | Schicht: S | Beschreibung: Maximale Besetzung überschritten | Erwartet: 10, Tatsächlich: 11 | Grund: Cross-Team-Kapazität"
  ],
  "info": [
    "Datum: 05.01.2026 | Mitarbeiter: Max Müller | Beschreibung: Ruhezeit-Ausnahme Sonntag→Montag | Grund: Team-Rotation",
    "Datum: 12.01.2026 | Mitarbeiter: Lisa Meyer | Beschreibung: Stunden unter Ziel | Erwartet: 240h, Tatsächlich: 232h | Grund: Optimierung"
  ]
}
```

## Constraint-Hierarchie (Final)

### HART (Kann NICHT verletzt werden)
1. ✅ Team-Rotation F→N→S (eine Schicht pro Team pro Woche)
2. ✅ Mindestbesetzung (F≥4, S≥3, N≥3)
3. ✅ 11h Ruhezeit (AUSSER Sonntag→Montag Team-Grenzen)
4. ✅ Aufeinanderfolgende Schichten-Limits

### WEICH (Kann verletzt werden mit Penalty)
1. ⚖️ Zielstunden (48h/7 × Tage) - Gewicht 1x
2. ⚖️ Max-Besetzung ≤ 10 - Gewicht 5x pro Überschreitung
3. ⚖️ Block-Scheduling (Mo-Fr, Sa-So) - Bonus-Maximierung
4. ⚖️ Faire Verteilung - Gewicht 1x

### ENTFERNT (Keine Einschränkung mehr)
- ❌ Hard 192h Minimum (jetzt nur Soft-Ziel)
- ❌ Hard wöchentliche Obergrenze (flexible Variation erlaubt)

## Technische Details

### Geänderte Dateien

1. **constraints.py**:
   - Zeile ~450-480: Hard 192h Constraint entfernt
   - Zeile ~855-932: Hard weekly maximum entfernt
   - Zeile ~685-730: Max staffing von hard zu soft geändert
   - Zeile ~990-1010: Ruhezeit-Ausnahme für Sonntag→Montag hinzugefügt

2. **solver.py**:
   - Zeile ~180-200: Penalties in Zielfunktion integriert
   - Objective: `fairness + overstaffing*5 + hours_shortage - blocks`

3. **violation_tracker.py** (NEU):
   - 170 Zeilen
   - Klassen: `Violation`, `ViolationTracker`
   - Deutsche Zusammenfassungen

### Solver-Objective (Gewichtet)

```python
objective = (
    fairness_penalties * 1 +        # Faire Verteilung
    overstaffing_penalties * 5 +    # Max-Besetzung überschritten
    hours_shortage * 1 +            # Stunden unter Ziel
    -block_bonuses                  # Block-Scheduling (zu maximieren)
)
```

## Zusammenfassung

**Status**: ✅ Alle Soft Constraints implementiert und integriert

**Erwartung**: Monatliche Planung für Januar 2026 sollte jetzt **FEASIBLE** sein

**Transparenz**: Alle Regelabweichungen werden protokolliert für manuelle Admin-Prüfung

**Flexibilität**: System priorisiert Machbarkeit über strikte Regeleinhalten

**Sicherheit**: Kritische Regeln (Mindestbesetzung) bleiben HART und werden nie verletzt

---

**Test-Status**: Bereit für Ausführung  
**Erwartetes Ergebnis**: ✅ FEASIBLE mit Violation-Report  
**Datum**: 24. Januar 2026
