# Schichtplanungs-Algorithmus

## Übersicht

Der automatische Schichtplanungs-Algorithmus verwendet **Google OR-Tools CP-SAT** (Constraint Programming - Satisfiability) zur Erstellung fairer und regelkonformer Schichtpläne.

## Technologie: Google OR-Tools CP-SAT

**CP-SAT (Constraint Programming - Satisfiability)** ist ein moderner Constraint-Solver von Google, der:
- Optimal oder near-optimal Lösungen findet
- Komplexe Constraints effizient verarbeitet
- Parallele Suche für bessere Performance nutzt
- Bewährte Algorithmen für Scheduling-Probleme implementiert

## Hauptprinzipien

### 1. Deklarative Problem-Formulierung

Der Algorithmus formuliert das Schichtplanungsproblem als **Constraint Satisfaction Problem (CSP)**:

**Entscheidungsvariablen:**
```
x[mitarbeiter_id, datum, schicht_code] = Boolean
  - True: Mitarbeiter hat diese Schicht an diesem Tag
  - False: Mitarbeiter hat diese Schicht nicht

bmt[mitarbeiter_id, datum] = Boolean
  - True: Mitarbeiter ist BMT an diesem Tag

bsb[mitarbeiter_id, datum] = Boolean
  - True: Mitarbeiter ist BSB an diesem Tag
```

**Zielfunktion:**
Minimierung der Abweichungen von fairer Schichtverteilung:
```
minimize: sum(|schichten_pro_mitarbeiter - durchschnitt|)
```

### 2. Harte Constraints (MÜSSEN eingehalten werden)

#### Grundregeln
```python
# Maximal 1 Schicht pro Person und Tag
for each mitarbeiter, datum:
    sum(x[mitarbeiter, datum, schicht] for schicht in schichten) <= 1

# Keine Arbeit während Abwesenheit
for each abwesenheit:
    for datum in abwesenheit.zeitraum:
        sum(x[mitarbeiter, datum, schicht] for schicht in schichten) == 0
```

#### Mindestbesetzung
```python
# Werktags (Mo-Fr)
for datum in werktage:
    sum(x[mitarbeiter, datum, 'F'] for mitarbeiter in alle) in [4, 5]  # Früh
    sum(x[mitarbeiter, datum, 'S'] for mitarbeiter in alle) in [3, 4]  # Spät
    sum(x[mitarbeiter, datum, 'N'] for mitarbeiter in alle) == 3       # Nacht

# Wochenende (Sa-So)
for datum in wochenende:
    for schicht in ['F', 'S', 'N']:
        sum(x[mitarbeiter, datum, schicht] for mitarbeiter in alle) in [2, 3]
```

#### Ruhezeiten & Verbotene Übergänge
```python
# Verbotene Schichtwechsel (Ruhezeit < 11h)
verbotene_uebergaenge = [('S', 'F'), ('N', 'F'), ('N', 'S')]

for mitarbeiter in alle:
    for datum in datumsbereich[:-1]:
        for (schicht1, schicht2) in verbotene_uebergaenge:
            # Nicht beide Schichten aufeinanderfolgend
            x[mitarbeiter, datum, schicht1] + x[mitarbeiter, datum+1, schicht2] <= 1
```

#### Arbeitszeit-Limits
```python
# Maximal 6 aufeinanderfolgende Dienste
for mitarbeiter in alle:
    for start_datum in datumsbereich[:-6]:
        sum(x[mitarbeiter, datum, schicht] 
            for datum in range(start_datum, start_datum+7)
            for schicht in schichten) <= 6

# Maximal 5 aufeinanderfolgende Nachtschichten
for mitarbeiter in alle:
    for start_datum in datumsbereich[:-5]:
        sum(x[mitarbeiter, datum, 'N'] 
            for datum in range(start_datum, start_datum+6)) <= 5

# Maximal 48 Stunden pro Woche
for mitarbeiter in alle:
    for woche_start in wochen:
        sum(x[mitarbeiter, datum, schicht] * schicht.stunden
            for datum in woche
            for schicht in schichten) <= 48

# Maximal 192 Stunden pro Monat
for mitarbeiter in alle:
    sum(x[mitarbeiter, datum, schicht] * schicht.stunden
        for datum in monat
        for schicht in schichten) <= 192
```

#### Springer-Verfügbarkeit
```python
# Mindestens 1 Springer muss verfügbar bleiben
for datum in datumsbereich:
    sum(x[springer, datum, schicht] 
        for springer in alle_springer
        for schicht in schichten) <= (anzahl_springer - 1)
```

#### Zusatzfunktionen (BMT/BSB)
```python
# Genau 1 BMT pro Werktag (Mo-Fr)
for datum in werktage:
    sum(bmt[mitarbeiter, datum] 
        for mitarbeiter in qualifizierte_bmt) == 1

# Genau 1 BSB pro Werktag (Mo-Fr)
for datum in werktage:
    sum(bsb[mitarbeiter, datum] 
        for mitarbeiter in qualifizierte_bsb) == 1

# BMT/BSB nur wenn qualifiziert
for mitarbeiter in alle:
    if not mitarbeiter.ist_bmt:
        bmt[mitarbeiter, datum] == 0
    if not mitarbeiter.ist_bsb:
        bsb[mitarbeiter, datum] == 0
```

### 3. Weiche Constraints (werden optimiert)

#### Faire Schichtverteilung
```python
# Berechne durchschnittliche Schichten pro Person
durchschnitt = (gesamt_benoetigte_schichten / anzahl_verfuegbarer_mitarbeiter)

# Minimiere Abweichungen vom Durchschnitt
for mitarbeiter in alle:
    schichten[mitarbeiter] = sum(x[mitarbeiter, datum, schicht] 
                                  for datum, schicht)
    
    # Penalty für Abweichung
    abweichung[mitarbeiter] = |schichten[mitarbeiter] - durchschnitt|

# Zielfunktion
minimize: sum(abweichung[mitarbeiter] for mitarbeiter in alle)
```

#### Bevorzugte Rotation
```python
# Idealer Rhythmus: Früh → Nacht → Spät
bevorzugte_folgen = [('F', 'N'), ('N', 'S'), ('S', 'F')]

# Belohne bevorzugte Folgen (negative Penalty)
for mitarbeiter in alle:
    for datum in datumsbereich[:-1]:
        for (schicht1, schicht2) in bevorzugte_folgen:
            if x[mitarbeiter, datum, schicht1] and x[mitarbeiter, datum+1, schicht2]:
                bonus += 1
```

## Solver-Konfiguration

### Parameter
```python
solver = cp_model.CpSolver()

# Zeitlimit (Default: 300 Sekunden = 5 Minuten)
solver.parameters.max_time_in_seconds = 300

# Anzahl paralleler Worker (Default: 8)
solver.parameters.num_search_workers = 8

# Such-Fortschritt loggen
solver.parameters.log_search_progress = True

# Optional: Früher Stop bei guter Lösung
solver.parameters.relative_gap_limit = 0.01  # 1% vom Optimum
```

### Lösungsqualität

Der Solver gibt einen Status zurück:
- **OPTIMAL**: Optimale Lösung gefunden (best case)
- **FEASIBLE**: Gültige Lösung gefunden, aber möglicherweise nicht optimal
- **INFEASIBLE**: Keine Lösung möglich (Constraints zu restriktiv)
- **UNKNOWN**: Zeitlimit erreicht ohne Lösung

## Algorithmus-Ablauf

### 1. Daten laden
```
- Mitarbeiter (mit Teams, Springer, Qualifikationen)
- Abwesenheiten
- Bestehende feste Schichten (optional)
- Konfiguration (Zeitraum, Besetzungsstärken)
```

### 2. Modell erstellen
```
- Entscheidungsvariablen definieren
- Harte Constraints hinzufügen
- Weiche Constraints zur Zielfunktion hinzufügen
```

### 3. Solver ausführen
```
- Parallele Suche starten
- Beste Lösung innerhalb Zeitlimit finden
- Ergebnis extrahieren
```

### 4. Lösung validieren
```
- Alle Regeln nochmals prüfen
- Verletzungen dokumentieren
- Warnungen ausgeben
```

### 5. Ergebnis speichern
```
- Schichtzuweisungen in Datenbank schreiben
- Zusatzfunktionen (BMT/BSB) speichern
- Statistiken berechnen
```

## Vorteile gegenüber Heuristiken

### OR-Tools CP-SAT
- ✅ Findet optimal oder near-optimal Lösungen
- ✅ Garantiert Einhaltung aller harten Constraints
- ✅ Effiziente parallele Suche
- ✅ Bewährter industrieller Solver
- ✅ Einfach erweiterbar um neue Constraints

### Klassische Heuristiken
- ⚠️ Finden oft lokale Optima
- ⚠️ Können Constraints verletzen
- ⚠️ Schwierig zu erweitern
- ⚠️ Keine Garantien über Lösungsqualität

## Erweiterbarkeit

### Neue Constraint hinzufügen

1. **In constraints.py definieren:**
```python
def add_my_new_constraint(model, x, employees, dates, shift_codes):
    """Add my custom constraint"""
    for emp in employees:
        for date in dates:
            # Your logic here
            model.Add(constraint_expression)
```

2. **In solver.py aktivieren:**
```python
from constraints import add_my_new_constraint

# Im Modell hinzufügen
add_my_new_constraint(model, x, employees, dates, shift_codes)
```

3. **In validation.py prüfen:**
```python
def validate_my_new_constraint(assignments, employees, dates):
    """Validate the new constraint"""
    violations = []
    # Check logic
    return violations
```

### Beispiele für mögliche Erweiterungen
- Wunschschichten (Präferenzen)
- Urlaubssperren (Blackout-Periods)
- Qualifikations-Matrix (Skills)
- Standort-Constraints (Multi-Site)
- Senioritäts-Regeln
- Work-Life-Balance Metriken

## Performance-Optimierung

### Für große Probleminstanzen (>50 Mitarbeiter, >2 Monate)

1. **Zeitraum aufteilen**: Planen Sie mehrere kürzere Zeiträume
2. **Zeitlimit erhöhen**: `--time-limit 600` oder mehr
3. **Worker anpassen**: Mehr CPUs nutzen
4. **Vorplanung nutzen**: Fixe Schichten aus Vorperiode
5. **Constraints lockern**: Besetzungsbereiche erweitern

### Typische Laufzeiten (Intel i7, 8 Cores)
- 17 Mitarbeiter, 1 Monat: ~30-60 Sekunden
- 30 Mitarbeiter, 1 Monat: ~2-5 Minuten
- 50 Mitarbeiter, 1 Monat: ~5-10 Minuten
- 100 Mitarbeiter, 1 Monat: ~15-30 Minuten

## Literatur & Ressourcen

- **Google OR-Tools Dokumentation**: https://developers.google.com/optimization
- **CP-SAT Solver**: https://developers.google.com/optimization/cp/cp_solver
- **Employee Scheduling**: https://developers.google.com/optimization/scheduling/employee_scheduling

---

**Version 2.0 - Python Edition mit Google OR-Tools**

© 2025 Fritz Winter Eisengießerei GmbH & Co. KG
