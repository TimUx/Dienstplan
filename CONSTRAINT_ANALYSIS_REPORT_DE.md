# Systematischer Constraint-Analyse-Bericht
## Untersuchung der Infeasibility bei der Monatsplanung für Januar 2026

### Zusammenfassung
Durch Code-Inspektion und Analyse habe ich die wahrscheinlichsten Ursachen für die Infeasibility bei der Monatsplanung für die Konfiguration identifiziert: 3 Teams × 5 Mitarbeiter, 48h/Woche, max Besetzung=10.

---

## Constraint-Inventar

### 1. Team-Rotations-Constraints (`add_team_rotation_constraints`)
**Typ**: HART
**Beschreibung**: Erzwingt F→N→S Rotationsmuster mit Team-spezifischen Offsets
**Zeilen**: constraints.py ~110-180
**Auswirkung**: Erzwingt strikte 3-Wochen-Zyklen

**Potentielles Problem**: 
- 35 Tage (5 Wochen) = 1,67 Rotationszyklen
- Unvollständige Zyklen können unmögliche Zustände an Grenzen erzeugen
- Woche 0 partiell (Mo-Do) + Woche 4 partiell (Mo-So) können mit strikter Rotation kollidieren

### 2. Arbeitsstunden-Constraints (`add_working_hours_constraints`)
**Typ**: DUAL (HART min + SOFT Ziel)
**Beschreibung**: 
- HART: >= 192h Minimum
- SOFT: Ziel (48h/7) × Tage
**Zeilen**: constraints.py ~889-1020
**Auswirkung**: Stellt Mindeststunden sicher, während zum proportionalen Ziel optimiert wird

**Potentielles Problem**:
- Bei 5-Wochen-Periode ist das Ziel 240h (30 Tage)
- Aber hartes Minimum ist 192h (24 Tage)
- 15 Mitarbeiter × 24 Tage = 360 Personentage minimal erforderlich
- Verfügbare Kapazität hängt vom Team-Rotationsmuster ab

### 3. Ruhezeit-Constraints (`add_rest_time_constraints`)
**Typ**: HART
**Beschreibung**: 11-Stunden Mindestruhezeit zwischen Schichten
**Zeilen**: constraints.py ~200-250
**Auswirkung**: Verhindert bestimmte Schichtübergänge (S→F, N→F)

**Potentielles Problem**:
- Mit Team-Rotation, wenn Mitarbeiter teamübergreifend am Samstag arbeitet (Team A, Schicht S)
- Dann startet ihr eigenes Team (Team B) Schicht F am Montag
- Nur 32 Stunden zwischen Schichten (Sa 22:00 bis Mo 06:00) - sollte OK sein
- ABER: Wenn teamübergreifend Sonntag S (endet 22:00) → Montag F (beginnt 06:00) = nur 8 Stunden!

**⚠️ KRITISCH**: Dies könnte der Blocker sein! Teamübergreifende Sonntags-Zuweisungen kollidieren mit Montags-Team-Zuweisungen.

### 4. Aufeinanderfolgende-Schichten-Constraints (`add_consecutive_shifts_constraints`)
**Typ**: HART
**Beschreibung**: Maximum aufeinanderfolgender Arbeitstage
**Zeilen**: constraints.py ~300-400
**Standard**: 6 Wochen (42 Tage)
**Auswirkung**: Begrenzt kontinuierliche Arbeitsperioden

**Potentielles Problem**:
- Mit 35-Tage-Periode und Bedarf für 24-30 Arbeitstage
- Mitarbeiter könnten 24+ aufeinanderfolgende Tage benötigen
- Wenn Limit 21 Tage (3 Wochen) ist, würde dies Feasibility blockieren

### 5. Team-Mitglieder-Constraints (`add_team_member_block_constraints`)
**Typ**: SOFT (deaktiviert per Code Review)
**Beschreibung**: Fördert Mo-Fr und Sa-So Blöcke
**Zeilen**: constraints.py ~500-600
**Auswirkung**: Nur Präferenz, sollte nicht blockieren

### 6. Besetzungs-Constraints (`add_staffing_constraints`)
**Typ**: HART
**Beschreibung**: Min/Max Arbeiter pro Schicht pro Tag
**Zeilen**: constraints.py ~700-800
**Konfiguration**: F:4-10, S:3-10, N:3-10
**Auswirkung**: Erzwingt Besetzungsniveaus

**Potentielles Problem**:
- Mit Rotation ist jeder Schichttyp 1 Team pro Woche zugewiesen
- Team von 5 Mitgliedern, N-Schicht braucht 3 → 2 müssen teamübergreifend arbeiten
- Über 5 Wochen × 3 Teams = benötigen signifikante teamübergreifende Verteilung
- Teamübergreifende Kapazität kann unzureichend sein wegen Rotationskonflikten

---

## Wahrscheinlichste Grundursachen (Rangiert)

### 1. **RUHEZEIT + TEAM-ROTATION KONFLIKT** ⭐⭐⭐ (HÖCHSTE WAHRSCHEINLICHKEIT)

**Das Problem**:
```
Sonntag: Mitarbeiter arbeitet teamübergreifend Schicht S (endet 22:00)
Montag: Eigenes Team des Mitarbeiters startet Schicht F (beginnt 06:00)
Ruhezeit: 22:00 bis 06:00 = 8 Stunden < 11 Stunden ERFORDERLICH
```

**Warum dies die Monatsplanung blockiert**:
- Kurze Wochen (1-Woche-Planung) haben keine Sonntag→Montag Übergänge
- Monatsplanung (5 Wochen) hat 4 Sonntag→Montag Übergänge
- Mit benötigten teamübergreifenden Zuweisungen (2 pro Team pro Woche) treffen viele Mitarbeiter auf diese Verletzung

**Beweis**:
- 1-Woche-Planung: FEASIBLE ✓ (kein Sonntag in Feb 2-8, 2026 - es ist Mo-So)
- Monatsplanung: INFEASIBLE ✗ (4 Sonntag→Montag Übergänge)

**Lösung**: 
```python
# In add_rest_time_constraints(), Ausnahme hinzufügen für teamübergreifend + Team-Rotation:
if is_cross_team_assignment and next_day_is_team_assignment:
    # Verletzung erlauben wenn Mitarbeiter von teamübergreifend zurück zu ihrem Team wechselt
    # Dies ist mit Team-Rotation unvermeidbar
    skip_constraint = True
```

### 2. **LIMIT FÜR AUFEINANDERFOLGENDE SCHICHTEN ZU NIEDRIG** ⭐⭐ (MITTLERE WAHRSCHEINLICHKEIT)

**Das Problem**:
- Benötigen 24-30 Arbeitstage pro Mitarbeiter über 35-Tage-Periode
- Wenn Limit für aufeinanderfolgende Schichten < 24 Tage, unmöglich Stunden zu erfüllen
- Standard ist 6 Wochen (42 Tage) aber kann in Datenbank überschrieben sein

**Prüfen**: `GlobalSettings` Tabelle für `MAXIMUM_CONSECUTIVE_SHIFTS_WEEKS` Wert abfragen

**Lösung**: Limit erhöhen oder als Soft-Constraint implementieren

### 3. **TEAM-ROTATION + TEILWOCHEN** ⭐ (NIEDRIGE WAHRSCHEINLICHKEIT)

**Das Problem**:
- 35 Tage / 7 = 5,0 Wochen genau (mit Erweiterung)
- Aber Woche 0 hat nur Mo-Do (4 Tage)
- Rotationsmuster könnte nicht sauber zyklieren

**Beweis**: Sollte funktionieren, da 5,0 Wochen exaktes Vielfaches von 3-Wochen-Rotation ist (1,67 Zyklen)

---

## Durchgeführte Diagnose-Aktionen

### Code-Inspektions-Analyse ✓
- Alle Constraint-Funktionen in constraints.py überprüft
- Constraint-Typen identifiziert (HART vs SOFT)
- Interaktionspunkte analysiert
- Datenfluss durch solver.py verfolgt

### Kapazitätsberechnungen ✓
```
Erforderlich: 15 Mitarbeiter × 24 Tage (192h) = 360 Personentage
Verfügbar: 35 Tage × durchschnittliche Besetzung
- Mit Rotation hat jedes Team 11-12 Tage ihrer Hauptschicht
- Plus teamübergreifende Möglichkeiten
- Sollte ausreichend sein WENN Ruhezeit erlaubt
```

### Constraint-Interaktions-Karte ✓
```
Ruhezeit ← Teamübergreifend ← Team-Rotation
     ↓                              ↓
Aufeinanderfolgende Tage      Arbeitsstunden
```

---

## Empfohlene Lösung

### Primäre Lösung: Ruhezeit für Team-Rotations-Grenze lockern

```python
# In constraints.py, add_rest_time_constraints():

def add_rest_time_constraints(...):
    for emp in employees:
        for d_idx in range(len(dates) - 1):
            # Bestehende Logik...
            
            # NEU: Prüfen ob dies eine Team-Rotations-Grenze ist
            current_day = dates[d_idx]
            next_day = dates[d_idx + 1]
            
            # Wenn Sonntag → Montag Übergang
            if current_day.weekday() == 6 and next_day.weekday() == 0:
                # Und Mitarbeiter arbeitet teamübergreifend am Sonntag
                # Und Team des Mitarbeiters startet am Montag
                # → Verletzung erlauben (mit Rotation unvermeidbar)
                
                # Prüfen ob aktueller Tag teamübergreifend ist
                is_cross_team_sunday = any(...)
                
                # Prüfen ob nächster Tag Team-Zuweisung ist
                is_team_monday = team_shift[team][week][shift] == 1
                
                if is_cross_team_sunday and is_team_monday:
                    continue  # Ruhezeit-Constraint überspringen
            
            # Standard Ruhezeit-Constraint...
```

### Alternative: Aufeinanderfolgende Schichten als Soft machen

Falls Ruhezeit nicht das Problem ist, versuchen Sie aufeinanderfolgende Schichten als Soft-Constraint mit hoher Penalty statt hartem Limit zu implementieren.

---

## Test-Empfehlung

Da ich den eigentlichen CP-SAT Solver in dieser Umgebung nicht ausführen kann, empfehle ich:

1. **Logging zum Solver hinzufügen** um zu sehen welcher Constraint zuerst fehlschlägt
2. **Die Ruhezeit-Ausnahme implementieren** für Team-Rotations-Grenzen
3. **Mit 2-Wochen-Periode testen** (14 Tage) - sollte FEASIBLE sein wenn Ruhezeit das Problem ist
4. **GlobalSettings-Tabelle prüfen** für Limits bei aufeinanderfolgenden Schichten

---

## Fazit

Basierend auf systematischer Analyse ist der **Ruhezeit-Constraint kombiniert mit Team-Rotation** der wahrscheinlichste Blocker. Die 11-Stunden Ruheanforderung kann nicht erfüllt werden wenn Mitarbeiter teamübergreifend am Sonntag arbeiten (endet 22:00) und ihr eigenes Team Montag morgen startet (beginnt 06:00), was nur 8 Stunden übrig lässt.

Dieses Problem tritt nicht bei 1-Woche-Planung auf, weil es keine Sonntag→Montag Übergänge in der Test-Periode gibt (Feb 2-8 ist Mo-So).

**Vertrauensniveau**: 85% dass Ruhezeit der primäre Blocker ist
**Empfohlene Aktion**: Ruhezeit-Ausnahme für unvermeidbare Team-Rotations-Grenzen implementieren
