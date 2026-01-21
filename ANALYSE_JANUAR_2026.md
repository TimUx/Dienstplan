# Schichtplanung Januar 2026 - Analyse und Lösungsvorschläge

## Zusammenfassung

Die Schichtplanung für Januar 2026 mit 3 Teams à 5 Mitarbeitern und 48h-Woche ist **INFEASIBLE** (unlösbar). Dies liegt nicht an unzureichender Kapazität, sondern an einem Konflikt zwischen mehreren Constraints.

## Konfiguration

- **Teams**: 3 Teams (Alpha, Beta, Gamma)
- **Mitarbeiter pro Team**: 5
- **Gesamtzahl Mitarbeiter**: 15
- **Schichten**: F (Früh), S (Spät), N (Nacht)
- **Schichtdauer**: 8 Stunden
- **Wochenarbeitszeit**: 48 Stunden
- **Planungszeitraum**: Januar 2026 (31 Tage, 22 Werktage, 9 Wochenendtage)

## Mathematische Anforderungen

### Stunden und Tage pro Mitarbeiter

```
Wochen im Januar:     31 Tage ÷ 7 = 4,43 Wochen
Monatsstunden:        48h/Woche × 4,43 = 212,6h
Benötigte Arbeitstage: 212,6h ÷ 8h = 26,6 Tage
```

**Jeder Mitarbeiter muss 26,6 Tage im Januar arbeiten, um auf 212,6 Stunden zu kommen.**

### Kapazitätsberechnung

| Metrik | Wert |
|--------|------|
| Verfügbare Tage | 31 |
| Benötigte Tage pro MA | 26,6 |
| Prozentsatz | 85,7% aller Tage |
| Max. Arbeitstage (5 Wochen × 7) | 35 |
| Gesamt MA-Tage benötigt | 15 × 26,6 = 398,6 |
| Gesamt MA-Tage verfügbar | 465 |
| **Kapazität** | ✓ **AUSREICHEND** |

## Warum ist es trotzdem INFEASIBLE?

Die mathematische Kapazität ist ausreichend, aber der Solver findet keine Lösung wegen der **Kombination folgender Constraints**:

### 1. Teamrotation (F → N → S)
- Jedes Team arbeitet GENAU EINE Schicht pro Woche
- Alle 5 Mitglieder eines Teams arbeiten ZUSAMMEN
- Rotation: Woche 1: Team 1=F, Team 2=N, Team 3=S → Woche 2: Team 1=N, Team 2=S, Team 3=F, etc.

### 2. Aufeinanderfolgende Arbeitstage
- **Maximum: 6 Tage** am Stück
- Bei 26,6 benötigten Tagen in 31 Tagen → fast durchgängig arbeiten
- Mit 6-Tage-Limit → regelmäßige Ruhetage erforderlich

### 3. Ruhezeiten
- **Minimum: 11 Stunden** zwischen Schichten
- Verhindert schnelle Schichtwechsel (z.B. S → F)

### 4. Besetzungsanforderungen
- Werktags: min=4, max=20
- Wochenende: min=2, max=20
- Mit Teamgröße 5 grundsätzlich erfüllbar, aber in Kombination mit anderen Constraints problematisch

### Konkretes Konflikt-Szenario

```
Woche 1 (7 Tage): Team 1 auf F-Schicht
  - Mitarbeiter arbeitet 6 Tage (Maximum)
  - 1 Tag Ruhe erforderlich
  - Erreicht: 6 Tage

Woche 2 (7 Tage): Team 1 auf N-Schicht  
  - Nach 11h Ruhezeit, kann wieder arbeiten
  - Arbeitet 6 Tage
  - 1 Tag Ruhe erforderlich
  - Erreicht: 6 Tage

Woche 3 (7 Tage): Team 1 auf S-Schicht
  - Arbeitet 6 Tage
  - Erreicht: 6 Tage

Woche 4 (7 Tage): Team 1 auf F-Schicht
  - Arbeitet 6 Tage
  - Erreicht: 6 Tage

Woche 5 (3 Tage): Team 1 auf N-Schicht
  - Arbeitet 3 Tage (alle verfügbar)
  - Erreicht: 3 Tage

SUMME: 6 + 6 + 6 + 6 + 3 = 27 Tage ✓
ABER: Fairness-Constraints und Wochenendverteilung machen dies unmöglich!
```

## Staffing-Anforderungen für 48h-Woche

### Durchschnittliche Besetzung pro Tag

```
Durchschnitt = (15 Mitarbeiter × 26,6 Tage) ÷ 31 Tage = 12,9 Mitarbeiter/Tag
```

### Empfohlene Maximalbesetzung

Für die Erfüllung des 48h-Ziels:

| Zeitraum | Aktuell | Empfohlen |
|----------|---------|-----------|
| Werktags (max) | 20 | 15-16 |
| Wochenende (max) | 20 | 8-10 |

**Die aktuellen Werte (max=20) sind ausreichend.**

## Lösungsvorschläge

### ✅ Empfehlung 1: Wochenarbeitszeit reduzieren

**Von 48h auf 40-42h reduzieren**

```
Bei 40h/Woche:
  - Monatsstunden: 40h × 4,43 = 177,1h
  - Benötigte Tage: 177,1h ÷ 8h = 22,1 Tage
  - Prozentsatz: 71,3% (statt 85,7%)
  - Mehr Spielraum für Ruhetage
```

**Dies ist die einfachste und empfohlene Lösung!**

### ✅ Empfehlung 2: Maximum aufeinanderfolgende Tage erhöhen

**Von 6 auf 7-8 Tage erhöhen**

```
Mit 7 Tagen:
  - Mehr Flexibilität pro Woche
  - Weniger erzwungene Ruhetage
  - Bessere Erfüllung des Stundenziels
```

Achtung: Arbeitsrechtliche Prüfung erforderlich!

### ✅ Empfehlung 3: Ruhezeit flexibilisieren

**11h Ruhezeit beibehalten, aber Cross-Team-Arbeit erlauben**

- Mitarbeiter können zwischen Teams wechseln ("Springer")
- Aber nur mit ausreichend Ruhezeit
- Erhöht Komplexität

### ❌ Nicht empfohlen: Teamrotation aufweichen

Die F → N → S Rotation ist vermutlich aus gutem Grund festgelegt (Fairness, Planbarkeit). Änderungen hier würden das gesamte System destabilisieren.

## Detaillierte Tagesberechnung

### Wochendarstellung Januar 2026

| Woche | Zeitraum | Tage | Werktage | Wochenende |
|-------|----------|------|----------|------------|
| 1 | 01.01-07.01 | 7 | 5 | 2 |
| 2 | 08.01-14.01 | 7 | 5 | 2 |
| 3 | 15.01-21.01 | 7 | 5 | 2 |
| 4 | 22.01-28.01 | 7 | 5 | 2 |
| 5 | 29.01-31.01 | 3 | 2 | 1 |
| **Σ** | | **31** | **22** | **9** |

### Teamzuteilungen

| Woche | Team 1 | Team 2 | Team 3 |
|-------|--------|--------|--------|
| 1 (7T) | F (5MA) | N (5MA) | S (5MA) |
| 2 (7T) | N (5MA) | S (5MA) | F (5MA) |
| 3 (7T) | S (5MA) | F (5MA) | N (5MA) |
| 4 (7T) | F (5MA) | N (5MA) | S (5MA) |
| 5 (3T) | N (5MA) | S (5MA) | F (5MA) |

### Maximal mögliche Arbeitstage pro Team

```
Team 1: 7 + 7 + 7 + 7 + 3 = 31 Tage möglich
Team 2: 7 + 7 + 7 + 7 + 3 = 31 Tage möglich
Team 3: 7 + 7 + 7 + 7 + 3 = 31 Tage möglich

Pro Mitarbeiter theoretisch: 31 Tage
Benötigt: 26,6 Tage
Reserve: 4,4 Tage
```

**Theoretisch ausreichend, aber Constraints verhindern die Nutzung dieser Reserve!**

## Verwendete Analyseskripte

Drei Skripte wurden erstellt:

1. **`analyze_january_2026.py`**: Grundlegende mathematische Analyse
2. **`analyze_team_rotation_infeasibility.py`**: Detaillierte Rotation und Constraints
3. **`test_january_2026_feasibility.py`**: Solver-Test (benötigt DB)

## Konkrete Handlungsempfehlung

### Sofort umsetzbar:

1. **Wochenarbeitszeit in STANDARD_SHIFT_TYPES anpassen (entities.py Zeile 241-244):**
   
   Den Parameter `weekly_working_hours` von 48.0 auf 40.0 ändern:
   ```python
   # Beispiel für F-Schicht (analog für S und N):
   # ShiftType(id, code, name, start, end, color, hours, weekly_hours, min_weekday, max_weekday, ...)
   ShiftType(1, "F", "Frühdienst", "05:45", "13:45", "#FFD700", 8.0, 40.0, 4, 20, 2, 20, True, True, True, True, True, True, True)
   ```
   
   Der 8. Parameter (weekly_working_hours) ist der relevante Wert: **von 48.0 auf 40.0**

2. **Solver erneut ausführen** - sollte dann FEASIBLE sein

### Alternativ:

1. **In `constraints.py` max_consecutive_days erhöhen:**
   ```python
   MAX_CONSECUTIVE_DAYS = 7  # statt 6
   ```

2. **Solver erneut ausführen**

## Fazit

Die Schichtplanung ist mathematisch möglich, aber die **48h-Woche ist zu anspruchsvoll** in Kombination mit:
- Team-basierter Rotation
- 6-Tage-Maximum
- 11h Ruhezeit
- Fairness-Zielen

**Empfohlene Lösung**: Wochenarbeitszeit auf 40h reduzieren (STANDARD_SHIFT_TYPES anpassen).

Dies ergibt:
- 22,1 Tage statt 26,6 Tage pro Mitarbeiter
- 71% statt 86% Auslastung
- Ausreichend Puffer für Constraints
- **Solver sollte OPTIMAL/FEASIBLE zurückgeben**

---

**Erstellt**: 2026-01-21  
**Analysiert für**: Januar 2026 (31 Tage)  
**Konfiguration**: 3 Teams × 5 Mitarbeiter, F/S/N Schichten
