# Analyse: Januar 2026 Schichtmodell - INFEASIBLE

## Zusammenfassung

Die exakte Konstellation aus den Anforderungen ist **NICHT UMSETZBAR (INFEASIBLE)** mit dem aktuellen Team-basierten Rotationssystem.

## Anforderungen (Original)

- **3 Teams** mit je **5 Mitarbeitern** (15 total)
- **3 Schichten**: Früh (F), Spät (S), Nacht (N)
- **48h Arbeitswoche** pro Mitarbeiter (212.6h/Monat bei 4.43 Wochen)
- **Schichtreihenfolge**: Früh → Nacht → Spät (feste Rotation)

### Schichtkonfiguration
- **Früh**: 8h/Tag, Mo-So, Wochentag Min 4 / Max 8, Wochenende Min 2 / Max 3
- **Spät**: 8h/Tag, Mo-So, Wochentag Min 3 / Max 6, Wochenende Min 2 / Max 3
- **Nacht**: 8h/Tag, Mo-So, Wochentag Min 3 / Max 3, Wochenende Min 2 / Max 3

### Allgemeine Einstellungen
- Max aufeinanderfolgende Schichten: 6 Wochen
- Max aufeinanderfolgende Nachtschichten: 3 Wochen
- Gesetzliche Ruhezeit: 11 Stunden

## Warum ist es INFEASIBLE?

### Grundproblem: Starre Team-Rotation

Das System erzwingt eine **feste Team-Rotation** nach dem Muster F → N → S:

```
Woche 0: Team 1=F (5 MA), Team 2=N (5 MA), Team 3=S (5 MA)
Woche 1: Team 1=N (5 MA), Team 2=S (5 MA), Team 3=F (5 MA)
Woche 2: Team 1=S (5 MA), Team 2=F (5 MA), Team 3=N (5 MA)
Woche 3: Team 1=F (5 MA), Team 2=N (5 MA), Team 3=S (5 MA) [wiederholt]
```

### Problem 1: Nacht-Schicht Besetzung

- **Nacht-Schicht Wochentag**: Min=3, **Max=3** (starr!)
- **Team-Größe**: 5 Mitarbeiter
- **Konflikt**: Ein Team hat 5 Mitarbeiter, aber Nacht darf nur 3 haben
  - System kann nicht 2 Mitarbeiter aus der Nacht-Woche "entfernen"
  - Alle Team-Mitglieder müssen die gleiche Schicht arbeiten (während der Wochentage)

### Problem 2: Januar 2026 Kalender

```
Januar 2026: 31 Tage, beginnt mit Donnerstag
  Woche 0 (incomplete): Do 01 - So 04 (4 Tage)
  Woche 1: Mo 05 - So 11 (7 Tage)
  Woche 2: Mo 12 - So 18 (7 Tage)
  Woche 3: Mo 19 - So 25 (7 Tage)
  Woche 4 (incomplete): Mo 26 - Sa 31 (6 Tage)
```

- 4.43 Wochen ergeben keine saubere 3-Wochen-Rotation
- Incomplete Wochen (Woche 0 und 4) passen nicht ins Rotationsmuster
- Wochenenden müssen separat behandelt werden, was zusätzliche Komplexität schafft

### Problem 3: Arbeitsstunden-Ziel

- **Soll**: 48h/Woche × 4.43 Wochen = **212.6h/Monat**
- **Tage benötigt**: 212.6h ÷ 8h/Tag = **26.6 Tage**
- **Verfügbar**: 31 Tage
- **Aber**: Mit starrer Rotation und Wochenend-Constraints ist es unmöglich, die Stunden gleichmäßig zu verteilen

### Problem 4: Wochenend-Constraints

- Wochentage: 22 Tage (Mo-Fr)
- Wochenendtage: 9 Tage (Sa-So)
- Wochenenden müssen **separat besetzt** werden (nicht Teil der Team-Rotation)
- Konflikt mit Arbeitsstunden-Zielen und Team-Rotation

## Getestete Lösungsansätze (alle INFEASIBLE)

### ✗ Lösung 1: Nacht-Schicht flexibler (Max=5)
- Erhöhung von Max=3 auf Max=5
- **Ergebnis**: INFEASIBLE
- **Grund**: Rotation bleibt zu starr

### ✗ Lösung 2: Reduzierte Arbeitsstunden (44h/Woche)
- Reduzierung auf 44h/Woche (194.9h/Monat)
- **Ergebnis**: INFEASIBLE
- **Grund**: Grundproblem bleibt (Rotation + Besetzung)

### ✗ Lösung 3: Kombiniert (46h + Flex)
- Kombination beider Ansätze
- **Ergebnis**: INFEASIBLE
- **Grund**: Architektonisches Problem nicht gelöst

## Mathematische Analyse

### Personentage-Berechnung

**Minimale Personentage benötigt:**
- Früh: (22 Wochentage × 4) + (9 Wochenenden × 2) = 106 Personentage
- Spät: (22 × 3) + (9 × 2) = 84 Personentage
- Nacht: (22 × 3) + (9 × 2) = 84 Personentage
- **Gesamt**: 274 Personentage

**Verfügbare Personentage:**
- 15 Mitarbeiter × 31 Tage = 465 Personentage
- **Auslastung**: 274 ÷ 465 = 58.9%

**Theoretisch machbar**: ✓ JA (genug Kapazität)

**ABER**: Die **Constraints** (starre Team-Rotation + Besetzungsanforderungen) machen es unmöglich!

## Mögliche Lösungen

### Option 1: System-Architektur ändern (EMPFOHLEN)

**Entferne die starre Team-Rotation und verwende flexiblere Modell:**

1. **Individuelle Mitarbeiter-Planung** statt Team-Rotation
2. **Weiche Rotation-Präferenzen** statt harter Constraints
3. **Flexible Team-Zuordnung** für bestimmte Wochen

**Vorteile:**
- System kann optimale Lösung finden
- Mehr Flexibilität bei Abwesenheiten
- Bessere Arbeitsstunden-Balance

**Nachteile:**
- Größere Änderung an der Codebasis
- Andere Use-Cases könnten betroffen sein

### Option 2: Mehr Teams (6 statt 3)

**Mit 6 Teams à 2-3 Mitarbeiter:**
- Mehr Flexibilität bei Rotation
- Bessere Anpassung an Besetzungsanforderungen
- Aber: Team-Größe von 2-3 ist sehr klein

### Option 3: Größere Teams (6 statt 5 MA/Team)

**Mit 6 Mitarbeitern pro Team (18 total):**
- Mehr Puffer für Besetzung
- Besser für Abwesenheiten
- Aber: 18 statt 15 Mitarbeiter (Kosten!)

### Option 4: Angepasste Anforderungen

**Pragmatische Anpassungen:**

1. **Arbeitsstunden reduzieren**: 40h statt 48h/Woche
   - Reduziert Druck auf System
   - 177.2h/Monat statt 212.6h
   - 22.2 Arbeitstage statt 26.6

2. **Flexiblere Besetzung**: 
   - Nacht: Min=2, Max=5 (statt Min=Max=3)
   - Erlaubt mehr Variabilität

3. **Andere Rotation**:
   - Z.B. 2-Wochen-Blocks statt 1-Woche
   - Oder flexible Rotation ohne festes Muster

4. **Teamübergreifende Einsätze aktivieren**:
   - System unterstützt dies bereits
   - Ermöglicht temporäre Zuordnungen

## Empfehlung

Für die spezifischen Anforderungen (3 Teams, 5 MA, 48h, feste Rotation F→N→S) gibt es **drei realistische Wege**:

### Empfehlung A: Architektur-Änderung (langfristig)
Entferne die starre Team-Rotation und implementiere ein flexibleres Modell. Dies erfordert:
- Änderungen in `constraints.py` (Team-Rotation deaktivierbar machen)
- Neue Constraint-Logik für flexible Rotation
- Tests und Validierung

### Empfehlung B: Angepasste Parameter (kurzfristig)
Nutze das bestehende System mit realistischeren Parametern:
- **40h Woche** (statt 48h)
- **Nacht-Schicht flexibler**: Min=2, Max=5
- **4 Teams** à 4-5 Mitarbeiter (statt 3 Teams)

### Empfehlung C: Hybrid-Ansatz (mittelfristig)
Kombiniere Team-Rotation mit mehr Flexibilität:
- Behalte Team-Rotation für Wochentage
- Flexible Besetzung für Wochenenden
- Erlaubt teamübergreifende Einsätze bei Bedarf
- Reduziere Arbeitsstunden-Ziel auf realistisches Level

## Fazit

Die **exakte Konstellation aus den Anforderungen ist NICHT umsetzbar** mit dem aktuellen Team-basierten Rotationssystem. 

Das System ist für einen anderen Use-Case optimiert (z.B. größere Teams, flexiblere Rotation, oder längere Planungszeiträume).

Für Januar 2026 mit 3 Teams à 5 Mitarbeitern ist eine **Architektur-Änderung oder Anpassung der Parameter erforderlich**.

## Tests

Siehe folgende Test-Dateien:
- `test_januar_2026_konstellation.py` - Original-Konstellation (INFEASIBLE)
- `test_januar_2026_loesung.py` - Getestete Lösungsansätze (alle INFEASIBLE)
- Diese Analyse-Datei: `JANUAR_2026_ANALYSE.md`

## Datum

Erstellt: 2026-01-21
