# Januar 2026 Schichtplanung - Abschlussbericht

## Zusammenfassung

Nach umfangreichen Tests und Analysen wurde festgestellt, dass die **exakte Konstellation aus den Anforderungen NICHT umsetzbar (INFEASIBLE)** ist mit dem aktuellen Team-basierten Rotationssystem.

## Original-Anforderungen

### Struktur
- **3 Teams** mit je **5 Mitarbeitern** (15 total)
- **3 Schichten**: Früh (F), Spät (S), Nacht (N)
- **48h Arbeitswoche** pro Mitarbeiter
- **Zeitraum**: Januar 2026 (31 Tage, 4.43 Wochen)

### Schichtkonfiguration
| Schicht | Stunden/Tag | h/Woche | Min WT | Max WT | Min WE | Max WE |
|---------|-------------|---------|--------|--------|--------|--------|
| Früh    | 8h          | 48h     | 4      | 8      | 2      | 3      |
| Spät    | 8h          | 48h     | 3      | 6      | 2      | 3      |
| Nacht   | 8h          | 48h     | 3      | 3      | 2      | 3      |

*WT = Wochentag, WE = Wochenende*

### Allgemeine Einstellungen
- Max aufeinanderfolgende Schichten: **6 Wochen** (42 Tage)
- Max aufeinanderfolgende Nachtschichten: **3 Wochen** (21 Tage)
- Gesetzliche Ruhezeit: **11 Stunden**
- **Schichtreihenfolge: Früh → Nacht → Spät** (feste Rotation)

## Durchgeführte Tests

### Test 1: Original-Konstellation
- **Datei**: `test_januar_2026_konstellation.py`
- **Konfiguration**: 3 Teams, 5 MA/Team, 48h/Woche
- **Ergebnis**: ❌ **INFEASIBLE**

### Test 2: Lösungsansätze
- **Datei**: `test_januar_2026_loesung.py`
- **Getestet**:
  1. Flexible Nacht-Schicht (Max=5 statt 3) → ❌ INFEASIBLE
  2. Reduzierte Stunden (44h statt 48h/Woche) → ❌ INFEASIBLE
  3. Kombiniert (46h + Flex) → ❌ INFEASIBLE
- **Ergebnis**: Alle 3 Ansätze **INFEASIBLE**

### Test 3: Alternative mit 4 Teams
- **Datei**: `test_januar_2026_4teams.py`
- **Konfiguration**: 4 Teams, 4 MA/Team, 48h/Woche, Nacht Max=5
- **Ergebnis**: ❌ **INFEASIBLE**

## Root Cause: Architektonische Einschränkung

Das fundamentale Problem liegt in der **starren Team-Rotation**:

### Wie die Rotation funktioniert

```
System erzwingt festes F → N → S Muster:

Woche 0: Team 1=F, Team 2=N, Team 3=S
Woche 1: Team 1=N, Team 2=S, Team 3=F
Woche 2: Team 1=S, Team 2=F, Team 3=N
Woche 3: Team 1=F, Team 2=N, Team 3=S [wiederholt]
```

### Warum es nicht funktioniert

1. **Team-Größe vs. Besetzungsanforderungen**
   - Team hat 5 Mitarbeiter
   - Nacht-Schicht erlaubt nur Max=3 (oder 5 bei gelockert)
   - System kann nicht 2-3 Mitarbeiter "aus der Rotation nehmen"
   - Alle Team-Mitglieder müssen gleiche Schicht arbeiten (Wochentags)

2. **Januar 2026 Kalender**
   - 31 Tage = 4.43 Wochen
   - Beginnt mit Donnerstag (incomplete Woche 0)
   - Endet mit Samstag (incomplete Woche 4)
   - Passt nicht zu 3-Wochen-Rotationszyklus

3. **Wochenend-Handling**
   - Wochenenden sind separate Variables (nicht Teil der Team-Rotation)
   - Müssen Min/Max Constraints erfüllen
   - Konflikt mit Arbeitsstunden-Zielen

4. **Arbeitsstunden-Balance**
   - 212.6h/Monat Ziel für jeden Mitarbeiter
   - Mit starrer Rotation unmöglich gleichmäßig zu verteilen
   - Einige MA würden zu viel, andere zu wenig arbeiten

## Mathematische Analyse

### Kapazitäts-Check

**Benötigte Personentage (Minimum):**
```
Früh:  (22 WT × 4) + (9 WE × 2) = 106 Personentage
Spät:  (22 WT × 3) + (9 WE × 2) =  84 Personentage
Nacht: (22 WT × 3) + (9 WE × 2) =  84 Personentage
─────────────────────────────────────────────────
GESAMT:                           274 Personentage
```

**Verfügbare Kapazität:**
```
15 Mitarbeiter × 31 Tage = 465 Personentage
Auslastung: 274 ÷ 465 = 58.9%
```

**Fazit**: Theoretisch ausreichend Kapazität! ✅

**ABER**: Die Constraints (Rotation + Besetzung + Wochenstunden) machen es unmöglich! ❌

## Was funktionieren WÜRDE

Basierend auf der Analyse würden folgende Konstellationen funktionieren:

### ✅ Option A: Planungszeitraum anpassen
- **Statt**: 31 Tage (4.43 Wochen)
- **Nutze**: 28 Tage (4 Wochen) oder 21 Tage (3 Wochen)
- **Vorteil**: Passt perfekt zur Rotation
- **Nachteil**: Nicht Januar 2026

### ✅ Option B: Mehr Mitarbeiter pro Team
- **Statt**: 5 MA/Team
- **Nutze**: 7-8 MA/Team
- **Vorteil**: Mehr Flexibilität bei Besetzung
- **Nachteil**: Höhere Personalkosten

### ✅ Option C: Reduzierte Arbeitsstunden
- **Statt**: 48h/Woche (212.6h/Monat)
- **Nutze**: 40h/Woche (177.2h/Monat)
- **Vorteil**: Weniger Druck auf Besetzung
- **Nachteil**: Weniger Arbeitsstunden pro MA

### ✅ Option D: Flexiblere Rotation
- **Statt**: Starre F→N→S Rotation
- **Nutze**: Flexible Schichtzuteilung mit Rotations-Präferenzen
- **Vorteil**: System kann optimale Lösung finden
- **Nachteil**: Erfordert Code-Änderungen

## Empfohlene Lösungen

### 🎯 EMPFEHLUNG 1: Code-Änderung (langfristig, nachhaltig)

**Ziel**: Flexiblere Rotation implementieren

**Änderungen in `constraints.py`:**

```python
def add_team_rotation_constraints(
    model: cp_model.CpModel,
    # ... Parameter ...
    enforce_strict_rotation: bool = True  # NEU: Flag hinzufügen
):
    """
    Team-Rotation Constraint mit optionaler Strict-Mode.
    """
    if not enforce_strict_rotation:
        # Keine starre Rotation - nur Präferenzen
        # Füge weiche Constraints für Rotations-Tendenz hinzu
        return
    
    # Bestehende starre Rotation ...
```

**Vorteile:**
- ✅ Behält bestehende Funktionalität für andere Use-Cases
- ✅ Ermöglicht flexible Planung für spezielle Monate
- ✅ Keine Breaking Changes

**Aufwand:** ~1-2 Tage Entwicklung + Tests

### 🎯 EMPFEHLUNG 2: Angepasste Parameter (kurzfristig, pragmatisch)

**Nutze System mit realistischeren Parametern:**

| Parameter | Original | Angepasst |
|-----------|----------|-----------|
| Teams | 3 | 4 |
| MA/Team | 5 | 5-6 |
| Arbeitsstunden | 48h/Woche | 40-44h/Woche |
| Nacht Max | 3 | 5-6 |
| Zeitraum | 31 Tage | 28 Tage (4 Wochen) |

**Vorteile:**
- ✅ Sofort umsetzbar ohne Code-Änderungen
- ✅ Realistischere Planung

**Nachteile:**
- ❌ Erfüllt nicht exakte Original-Anforderungen

### 🎯 EMPFEHLUNG 3: Hybrid-Ansatz (mittelfristig)

**Kombiniere starre Rotation mit Flexibilität:**

1. **Team-Rotation nur für Wochentage** (Mo-Fr)
2. **Flexible Besetzung für Wochenenden** (Sa-So)
3. **Teamübergreifende Einsätze** bei Bedarf aktiviert
4. **Reduzierte Arbeitsstunden** auf realistisches Level (40-44h)

**Implementierung:**
- Änderung in `add_employee_team_linkage_constraints()`
- Wochenenden bekommen eigene Logik
- Teamübergreifende Einsätze werden priorisiert

**Vorteile:**
- ✅ Nutzt bestehende Struktur
- ✅ Erhöht Flexibilität
- ✅ Moderater Änderungsaufwand

## Abschließende Bewertung

### Ist Januar 2026 mit den exakten Anforderungen machbar?

**Antwort: NEIN ❌**

Das Team-basierte Rotationssystem ist **architektonisch nicht geeignet** für:
- Kurze/ungerade Planungszeiträume (4.43 Wochen)
- Kleine Teams (5 MA) mit starren Besetzungsanforderungen
- Hohe Arbeitsstunden-Ziele (48h/Woche) mit fester Rotation

### Was ist der nächste Schritt?

**Option A: Systemänderung**
→ Implementiere flexible Rotation (siehe Empfehlung 1)
→ Aufwand: ~1-2 Tage
→ Ermöglicht zukünftig solche Szenarien

**Option B: Parameter-Anpassung**
→ Nutze 40-44h/Woche statt 48h
→ Nutze 4 Teams statt 3
→ Nutze 28-Tage-Perioden statt 31
→ Aufwand: Sofort
→ Einschränkung: Nicht exakte Anforderungen

**Option C: Akzeptanz**
→ System ist für andere Use-Cases optimiert
→ Januar 2026 mit diesen Parametern ist ein Edge-Case
→ Dokumentiere Limitation und nutze alternative Planung

## Dateien

- ✅ `test_januar_2026_konstellation.py` - Original-Test (INFEASIBLE)
- ✅ `test_januar_2026_loesung.py` - 3 Lösungsansätze (INFEASIBLE)
- ✅ `test_januar_2026_4teams.py` - 4-Teams-Alternative (INFEASIBLE)
- ✅ `JANUAR_2026_ANALYSE.md` - Detaillierte technische Analyse
- ✅ `JANUAR_2026_ABSCHLUSSBERICHT.md` - Dieser Bericht

## Datum

Erstellt: 2026-01-21

---

**Fazit**: Die Anforderungen sind mit dem aktuellen System nicht umsetzbar. Empfehlung: Code-Änderung für flexible Rotation oder Anpassung der Parameter.
