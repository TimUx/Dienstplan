# 192h Constraint Correction - Back to SOFT with Dynamic Calculation

## Datum / Date: 2026-02-07

## Hintergrund / Background

**DE**: Der Benutzer hat zu Recht darauf hingewiesen, dass die 192h Mindeststunden-Constraint in früheren PRs von HART auf WEICH umgestellt wurde, aber in einem späteren PR fälschlicherweise wieder auf HART zurückgesetzt wurde.

**EN**: The user correctly pointed out that the 192h minimum hours constraint was changed from HARD to SOFT in earlier PRs, but was incorrectly reverted back to HARD in a later PR.

---

## PR Historie / PR History

### PR #109 (2026-01-20): Dynamic Monthly Hours Calculation
✅ **Implementiert**: Dynamische Berechnung der Monatsstunden
- Formel: `(weekly_working_hours / 7) × actual_calendar_days`
- Beispiele:
  - Januar (31 Tage): 48h/7 × 31 = 212,57h
  - Februar (28 Tage): 48h/7 × 28 = 192h
  
### PR #122 (2026-01-25): Flexible Constraints
✅ **Korrekt implementiert**: 192h als WEICH Constraint
- Zitat aus PR #122: "Die in der Schichtverwaltung festgelegte Rotation muss auf Team-Ebene eingehalten werden, kann aber in Bezug auf die einzelnen Mitarbeiter bei Bedarf flexibel angepasst werden"
- Zitat: "Grundsätzlich sollen alle Regeln und Vorgaben eingehalten werden, es darf aber in Ausnahmefällen davon abgewichen werden"
- **Philosophie**: Regeln folgen, aber Flexibilität für Planbarkeit

### PR #160 (2026-02-03): Re-add Hard 192h Constraint
❌ **FEHLER**: 192h wurde fälschlicherweise wieder als HART implementiert
- Grund: Mitarbeiter erhielten nur 20-23 Schichten (160-184h) statt 24+ Schichten
- Lösung war falsch: Hätte Penalty-Gewicht erhöhen sollen, nicht HART machen
- Problem: HART macht System inflexibel bei schwierigen Szenarien

---

## Korrektur / Correction (2026-02-07)

### Änderungen in `constraints.py`

**ENTFERNT (Zeile 3041-3046):**
```python
# HARD CONSTRAINT: Absolute minimum 192h/month (24 shifts × 8h)
# This ensures employees work at least 24 shifts per month as required
# Only applies to employees without full-month absences
# Scaled: 192h × 10 = 1920
min_hours_scaled = 1920  # 192h × 10 (scaling factor)
model.Add(sum(total_hours_terms) >= min_hours_scaled)
```

**WIEDERHERGESTELLT (Zeile 3040-3072):**
```python
# SOFT CONSTRAINT: Target minimum hours based on proportional calculation
# Target = (weekly_working_hours / 7) × days_without_absence
# This is dynamic and adapts to different month lengths and weekly hours
# 
# Examples:
# - January (31 days), 48h/week: 48/7 × 31 = 212.57h ≈ 213h target (scaled: 2130)
# - February (28 days), 48h/week: 48/7 × 28 = 192h target (scaled: 1920)
# - March (31 days), 40h/week: 40/7 × 31 = 177.14h ≈ 177h target (scaled: 1770)
# 
# High penalty weight (100x) ensures this is strongly enforced, but allows
# violations when necessary for planning feasibility (per PR #122 requirements)

daily_target_hours = weekly_target_hours / 7.0
target_total_hours_scaled = int(daily_target_hours * days_without_absence * 10)

# Create variable for shortage from target (0 if at target, positive if below)
shortage_from_target = model.NewIntVar(0, target_total_hours_scaled, 
                                        f"emp{emp.id}_hours_shortage")

# shortage = max(0, target - actual)
# We model this as: shortage >= target - actual AND shortage >= 0
model.Add(shortage_from_target >= target_total_hours_scaled - sum(total_hours_terms))
model.Add(shortage_from_target >= 0)

# Add to soft objectives with HIGH penalty weight (100x)
# This makes it nearly as important as hard constraints, but still flexible
soft_objectives.append(shortage_from_target * 100)
```

### Dokumentations-Updates

**SCHICHTPLANUNGS_REGELN.md & SHIFT_PLANNING_RULES_EN.md:**

1. **Harte Constraints**: H7 "Mindeststunden pro Monat" ENTFERNT
2. **Weiche Constraints**: Eintrag #5 hinzugefügt:
   - Name: "Zielstunden-Erreichung" / "Target Hours Achievement"
   - Gewicht: 100 (KRITISCH)
   - Beschreibung: DYNAMISCH berechnet basierend auf `(weekly_hours/7) × Kalendertage`
   
3. **Version**: 1.2 mit Änderungsnotiz

---

## Kernpunkte / Key Points

### 1. NICHT fest 192h / NOT fixed 192h
Die Stunden werden **dynamisch berechnet** basierend auf:
- Monatslänge (28, 30, oder 31 Tage)
- Wöchentliche Arbeitszeit des Schichttyps (kann variieren!)
- Tatsächliche Arbeitstage (ohne Abwesenheiten)

### 2. WEICH, nicht HART / SOFT, not HARD
- Constraint kann verletzt werden wenn nötig für Planbarkeit
- Hohe Penalty (100x) macht Verletzungen selten aber nicht unmöglich
- Erlaubt Lösungen in schwierigen Szenarien (kleine Teams, viele Abwesenheiten)

### 3. Anpassbar / Adaptable
Verschiedene Schichttypen können verschiedene Wochenstunden haben:
- Standard: 48h/Woche
- Teilzeit: 40h/Woche
- Spezial: Andere Konfigurationen

### 4. Philosophie aus PR #122 / Philosophy from PR #122
> "Grundsätzlich sollen alle Regeln und Vorgaben eingehalten werden, es darf aber in Ausnahmefällen davon abgewichen werden. Wichtig ist, dass trotzdem eine Schicht geplant werden kann."

**Übersetzung**: Rules should be followed, but can be violated in exceptional cases. Important is that planning can still succeed.

---

## Beispiele / Examples

### Szenario 1: Standard-Monat
- **Monat**: Februar 2026 (28 Tage)
- **Wochenstunden**: 48h
- **Berechnung**: 48h/7 × 28 = 192h
- **Ergebnis**: Entspricht der ursprünglichen "192h Regel"

### Szenario 2: Langer Monat
- **Monat**: Januar 2026 (31 Tage)
- **Wochenstunden**: 48h
- **Berechnung**: 48h/7 × 31 = 212,57h ≈ 213h
- **Ergebnis**: Mehr Stunden als "192h Regel"

### Szenario 3: Teilzeit-Schicht
- **Monat**: März 2026 (31 Tage)
- **Wochenstunden**: 40h (Teilzeit)
- **Berechnung**: 40h/7 × 31 = 177,14h ≈ 177h
- **Ergebnis**: Weniger Stunden, aber proportional korrekt

### Szenario 4: Mit Abwesenheiten
- **Monat**: Januar 2026 (31 Tage)
- **Abwesenheit**: 5 Tage
- **Arbeitstage**: 26 Tage
- **Wochenstunden**: 48h
- **Berechnung**: 48h/7 × 26 = 178,29h ≈ 178h
- **Ergebnis**: Angepasst an tatsächliche Verfügbarkeit

---

## Vorteile / Benefits

### 1. Flexibilität / Flexibility
✅ System kann Lösungen finden auch bei:
- Kleinen Teams
- Vielen Abwesenheiten
- Schichtkonfigurationsänderungen
- Anderen schwierigen Konstellationen

### 2. Korrektheit / Correctness
✅ Stunden sind **proportional** zur tatsächlichen Verfügbarkeit:
- Nicht zu viel (Überlastung)
- Nicht zu wenig (Unterauslastung)
- Angepasst an Monatslänge und Schichttyp

### 3. Konsistenz / Consistency
✅ Wiederherstellung der ursprünglichen Implementierung aus PR #122:
- Entspricht Benutzeranforderungen
- Folgt dokumentierter Philosophie
- Bewahrt Flexibilität für Planbarkeit

### 4. Durchsetzung / Enforcement
✅ Hohe Penalty (100x) bedeutet:
- Verstöße sind selten
- System versucht stark, Ziel zu erreichen
- Aber blockiert nicht bei Unmöglichkeit

---

## Qualitätssicherung / Quality Assurance

✅ **Code Review**: 0 Probleme
✅ **Security Scan**: 0 Alerts  
✅ **Dokumentation**: Beide Sprachen aktualisiert
✅ **Konsistenz**: Constraints und Dokumentation stimmen überein
✅ **Version**: 1.2 mit vollständiger Änderungshistorie

---

## Zusammenfassung / Summary

**DE**: Die 192h Mindeststunden-Constraint wurde von HART zurück auf WEICH korrigiert, wie sie ursprünglich in PR #122 implementiert wurde. Die Stunden werden dynamisch basierend auf `(weekly_hours/7) × Kalendertage` berechnet, nicht fest auf 192h gesetzt. Dies ermöglicht Flexibilität für Planbarkeit bei gleichzeitig starker Durchsetzung durch hohe Penalty-Gewichte.

**EN**: The 192h minimum hours constraint has been corrected from HARD back to SOFT as originally implemented in PR #122. Hours are calculated dynamically based on `(weekly_hours/7) × calendar_days`, not fixed at 192h. This enables flexibility for planning feasibility while maintaining strong enforcement through high penalty weights.

---

**Erstellt**: 2026-02-07  
**Status**: Abgeschlossen / Complete  
**Version**: 1.2
