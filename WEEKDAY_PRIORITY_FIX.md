# Fix: Wochenend-Überbesetzung vs. Wochentags-Lücken

## Problem

Im Januar 2026 wurde beobachtet, dass die automatische Schichtplanung die Wochenenden (Samstag/Sonntag) vollständig mit Personal besetzt hat (5 Mitarbeiter je Schicht = 15 Mitarbeiter insgesamt), während in der Woche (Montag-Freitag) noch Lücken vorhanden waren.

Dies widerspricht den konfigurierten Schichteinstellungen:

**Wochentags (Montag-Freitag):**
- Frühdienst: max 8 Mitarbeiter
- Spätdienst: max 6 Mitarbeiter
- Nachtdienst: max 4 Mitarbeiter

**Wochenende (Samstag-Sonntag):**
- Frühdienst: max 3 Mitarbeiter
- Spätdienst: max 3 Mitarbeiter
- Nachtdienst: max 3 Mitarbeiter

**Erwartung:** Primär sollen die Lücken in der Woche gefüllt werden, sodass am Wochenende weniger Mitarbeiter eingeplant werden müssen.

## Ursache

Der Constraint-Solver verwendet Gewichtungen in der Zielfunktion, um verschiedene Soft-Constraints gegeneinander abzuwägen. Die bisherige Gewichtung behandelte Überbesetzung an Wochentagen und Wochenenden gleich, was dazu führte, dass der Solver Wochenenden bevorzugte, ohne die unterschiedlichen Kapazitätslimits zu berücksichtigen.

## Lösung

Die Lösung implementiert **differenzielle Strafgewichte** in der Optimierungsfunktion:

### 1. Änderungen in `constraints.py`

Die Funktion `add_staffing_constraints()` wurde geändert, um drei separate Listen zurückzugeben:
- `weekday_overstaffing_penalties` - Überbesetzung an Wochentagen
- `weekend_overstaffing_penalties` - Überbesetzung am Wochenende  
- `weekday_understaffing_penalties` - Unterbesetzung an Wochentagen

Zusätzlich wurde eine neue Strafvariable für Wochentags-Unterbesetzung hinzugefügt:
```python
# NEW: Add understaffing penalty for weekdays to encourage filling gaps
understaffing = model.NewIntVar(0, 20, f"understaff_{shift}_{d}_weekday")
model.Add(understaffing >= staffing[shift]["max"] - total_assigned)
model.Add(understaffing >= 0)
weekday_understaffing_penalties.append(understaffing)
```

### 2. Änderungen in `solver.py`

Die Gewichtungen in der Zielfunktion wurden angepasst:

```python
# Weekend overstaffing: 50x weight (SEHR HOHE Strafe)
for overstaff_var in weekend_overstaffing:
    objective_terms.append(overstaff_var * 50)

# Weekday overstaffing: 2x weight (leichte Strafe - erlaubt Flexibilität)
for overstaff_var in weekday_overstaffing:
    objective_terms.append(overstaff_var * 2)

# Weekday understaffing: 5x weight (starker Anreiz zum Füllen)
for understaff_var in weekday_understaffing:
    objective_terms.append(understaff_var * 5)
```

**Logik:**
- Sehr hohe Strafe (50x) für Wochenend-Überbesetzung verhindert, dass mehr Personal als nötig am Wochenende eingeplant wird
- Niedrige Strafe (2x) für Wochentags-Überbesetzung erlaubt Flexibilität, wenn nötig
- Mittlere Strafe (5x) für Wochentags-Unterbesetzung schafft Anreiz, Wochentagsschichten bis zur Maximalkapazität zu füllen

### 3. Test

Ein neuer Test `test_weekday_priority.py` wurde erstellt, der die korrekte Priorisierung validiert.

## Ergebnisse

### Vor dem Fix
- Wochenend-Spätschicht: 5 Mitarbeiter (überbesetzt, max=3)
- Wochentags-Lücken vorhanden

### Nach dem Fix
**Wochenend-Durchschnitt:**
- Frühdienst: 2.5/3 ✅
- Spätdienst: 3/3 ✅
- Nachtdienst: 3/3 ✅

**Wochentags-Durchschnitt:**
- Frühdienst: 7.4/8 ✅
- Spätdienst: 6/6 ✅
- Nachtdienst: 3.2/4 ✅

Die Wochentage nutzen nun die höhere Kapazität korrekt aus, während die Wochenenden die niedrigeren Maximalwerte respektieren.

## Technische Details

Die Änderung beeinflusst nur die Soft-Constraints (Optimierungsziele), nicht die Hard-Constraints:
- **Hard Constraint (unveränderlich):** Minimum-Besetzung muss eingehalten werden
- **Soft Constraint (optimiert):** Maximum-Besetzung wird durch Strafgewichte gesteuert

Die unterschiedlichen Gewichte schaffen die richtigen Anreize, ohne bestehende Constraints oder harte Anforderungen zu brechen.

## Sicherheit

CodeQL-Sicherheitsscan: 0 Warnungen gefunden ✅

## Auswirkungen

Diese Änderung stellt sicher, dass der Planungsalgorithmus Wochentagsschichten (mit höheren Kapazitätslimits) priorisiert, bevor er Wochenendschichten überbesetzt (mit niedrigeren Limits). Die differenziellen Strafgewichte schaffen die richtigen Anreize für eine bedarfsgerechte Planung.
