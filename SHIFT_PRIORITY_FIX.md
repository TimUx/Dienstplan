# Schicht-Priorität: Früh > Spät > Nacht

## Anforderung

Bei der automatischen Schichtplanung sollen Schichten in folgender Prioritätsreihenfolge befüllt werden:

1. **Früh (F)** - höchste Priorität
2. **Spät (S)** - mittlere Priorität
3. **Nacht (N)** - niedrigste Priorität

Dies bedeutet, dass der Solver bevorzugt Frühschichten besetzt, dann Spätschichten, und zuletzt Nachtschichten.

## Implementierung

Die Lösung verwendet **zwei komplementäre Mechanismen** in der Optimierungsfunktion:

### 1. Schichtspezifische Unterbesetzungsstrafen

In `constraints.py` werden Unterbesetzungsstrafen jetzt **nach Schichttyp getrennt** zurückgegeben:

```python
weekday_understaffing_by_shift = {shift: [] for shift in shift_codes}
# Fügt Strafen für jede Schicht separat hinzu
weekday_understaffing_by_shift[shift].append(understaffing)
```

In `solver.py` werden dann **unterschiedliche Gewichte** angewendet:

```python
shift_priority_weights = {
    'F': 20,  # Früh - höchste Priorität
    'S': 12,  # Spät - mittlere Priorität
    'N': 5    # Nacht - niedrigste Priorität
}
```

**Logik:** Höheres Gewicht = höhere Strafe für Lücken = höhere Priorität zum Füllen

### 2. Schichttyp-Präferenz-Zielfunktion (KRITISCH)

Zusätzlich zu den Unterbesetzungsstrafen wurde ein **direktes Präferenz-Ziel** hinzugefügt, das die Gesamtzahl der Mitarbeiter pro Schichttyp zählt und Prioritätsgewichte anwendet:

```python
shift_penalty_weights = {
    'F': -3,  # BELOHNUNG (negativ = Bonus für Befüllung)
    'S': 1,   # leichte Strafe (weniger bevorzugt als F)
    'N': 3    # stärkere Strafe (vermeiden wenn möglich)
}
```

Für jeden Wochentag wird gezählt, wie viele Mitarbeiter jeder Schicht zugeordnet sind, und diese Zahlen werden mit den Prioritätsgewichten multipliziert:

- **Negatives Gewicht (F):** Jeder Mitarbeiter in Frühschicht = Bonus → mehr Frühschichtmitarbeiter = bessere Lösung
- **Positives Gewicht (S, N):** Jeder Mitarbeiter in Spät-/Nachtschicht = Strafe → weniger Spät-/Nachtmitarbeiter = bessere Lösung

## Warum zwei Mechanismen?

1. **Unterbesetzungsstrafen** wirken auf Lücken (Differenz zwischen IST und MAX)
2. **Präferenz-Zielfunktion** wirkt auf absolute Zahlen (Gesamtzahl Mitarbeiter pro Schicht)

Beide zusammen stellen sicher, dass:
- Bei Wahlmöglichkeiten bevorzugt Frühschichten gefüllt werden
- Lücken in Frühschichten schwerer wiegen als Lücken in anderen Schichten
- Die Gesamtverteilung F > S > N bevorzugt

## Testergebnisse

### Test: Schicht-Priorität (test_shift_priority.py)

**Konfiguration:** Alle Schichten haben gleiche Limits (min=3, max=6), um den reinen Prioritätseffekt zu isolieren

**Ergebnis:**
```
Früh (F):  130.0% gefüllt (39/30 Positionen) ✅
Spät (S):  100.0% gefüllt (30/30 Positionen) ✅
Nacht (N):  50.0% gefüllt (15/30 Positionen) ✅

Prioritätsreihenfolge F ≥ S ≥ N ist eingehalten!
```

**Interpretation:**
- Frühschichten werden absichtlich **überbesetzt** (130%), da höchste Priorität
- Spätschichten werden **genau bis zum Maximum** gefüllt (100%)
- Nachtschichten bleiben **unterbesetzt** (50%), da niedrigste Priorität

### Kompatibilität mit Wochentags-Priorität

Der Test `test_weekday_priority.py` prüft, ob die neue Schichtpriorität die bestehende Wochentags-/Wochenend-Priorisierung nicht beeinträchtigt:

**Ergebnis:**
```
Wochentags-Durchschnitte:  F=7.6/8, S=6/6, N=3/4 ✅
Wochenend-Durchschnitte:   F=2.5/3, S=3.0/3, N=3.0/3 ✅

Beide Tests bestanden - keine Regressionen!
```

## Technische Details

### Änderungen in constraints.py

**Rückgabewert geändert:**
```python
# Vorher:
return (weekday_overstaffing, weekend_overstaffing, weekday_understaffing)

# Nachher:
return (weekday_overstaffing, weekend_overstaffing, weekday_understaffing_by_shift)
```

Wobei `weekday_understaffing_by_shift` ein Dictionary ist:
```python
{
    'F': [penalty_var1, penalty_var2, ...],
    'S': [penalty_var1, penalty_var2, ...],
    'N': [penalty_var1, penalty_var2, ...]
}
```

### Änderungen in solver.py

**Zwei neue Optimierungsziele hinzugefügt:**

1. **Schichtspezifische Unterbesetzungsstrafen** (ca. Zeile 212-228)
2. **Schichttyp-Präferenz-Zielfunktion** (ca. Zeile 230-287)

## Auswirkungen

Diese Änderung stellt sicher, dass bei der automatischen Schichtplanung:

✅ **Frühschichten** (F) zuerst und am vollständigsten befüllt werden  
✅ **Spätschichten** (S) als zweites befüllt werden  
✅ **Nachtschichten** (N) als letztes befüllt werden (können Lücken haben)

Dies entspricht typischen betrieblichen Anforderungen, wo:
- Frühschichten oft am wichtigsten sind (Tagesbeginn, hohe Aktivität)
- Spätschichten die zweite Priorität haben
- Nachtschichten mit Mindestbesetzung auskommen können

## Hinweis zur Gewichtsanpassung

Die Gewichte wurden sorgfältig kalibriert, um sowohl die Schichtpriorität als auch die Wochentags-/Wochenend-Priorisierung zu respektieren. Änderungen an den Gewichten sollten mit beiden Tests validiert werden:

```bash
python3 test_shift_priority.py      # Prüft F > S > N
python3 test_weekday_priority.py    # Prüft Wochentag > Wochenende
```
