# 📋 Schichtplanungs-Regeln und Abhängigkeiten

**Version 2.1 - Python Edition** | Vollständige Dokumentation aller Regeln und Abhängigkeiten

---

## 📑 Inhaltsverzeichnis

1. [System-Übersicht](#1-system-übersicht)
2. [Grundlegende Annahmen](#2-grundlegende-annahmen)
3. [Harte Constraints (Pflichtregeln)](#3-harte-constraints-pflichtregeln)
4. [Weiche Constraints (Optimierungsziele)](#4-weiche-constraints-optimierungsziele)
5. [Mindestanforderungen](#5-mindestanforderungen)
6. [Berechnungen und Formeln](#6-berechnungen-und-formeln)
7. [Abhängigkeiten-Diagramm](#7-abhängigkeiten-diagramm)
8. [Beispiel: Januar 2026](#8-beispiel-januar-2026)

---

## 1. System-Übersicht

### 1.1 Planungsansatz

Das System verwendet **Team-basierte Schichtplanung** mit Google OR-Tools CP-SAT Solver:

```
┌──────────────────────────────────────────────────────┐
│           TEAM-BASIERTE SCHICHTPLANUNG               │
├──────────────────────────────────────────────────────┤
│                                                       │
│  Teams arbeiten als Einheit                          │
│  ↓                                                    │
│  Wöchentliche Rotation: F → N → S                   │
│  ↓                                                    │
│  Individuelle Verfügbarkeit (Urlaub/Krankheit)      │
│  ↓                                                    │
│  Cross-Team Einsätze (bei Bedarf)                   │
│  ↓                                                    │
│  Optimierung (Fairness, Blockeinsätze)              │
│                                                       │
└──────────────────────────────────────────────────────┘
```

### 1.2 Schichttypen (Standard)

| Code | Name | Arbeitszeit | Stunden/Tag | Wochenstunden | Farbe |
|------|------|-------------|-------------|---------------|-------|
| **F** | Frühschicht | 05:45 – 13:45 | 8.0 | 48.0 | 🟢 Grün |
| **N** | Nachtschicht | 21:45 – 05:45 | 8.0 | 48.0 | 🔵 Blau |
| **S** | Spätschicht | 13:45 – 21:45 | 8.0 | 48.0 | 🟠 Orange |

**Zusätzliche Funktionen:**
- **TD (Tagdienst)**: Organisatorische Funktion, keine separate Schicht, wird 1x pro Woche (Mo-Fr) vergeben

---

## 2. Grundlegende Annahmen

### 2.1 Team-Struktur

Gemäß Anforderung:

```
┌─────────────────────────────────────────┐
│  Gesamtsystem                            │
│  ─────────────────────────────────────  │
│                                          │
│  3 Teams × 5 Mitarbeiter = 15 MA        │
│                                          │
│  ┌───────────┐  ┌───────────┐  ┌──────┐│
│  │ Team Alpha│  │ Team Beta │  │Team  ││
│  │  5 MA     │  │  5 MA     │  │Gamma ││
│  │           │  │           │  │5 MA  ││
│  └───────────┘  └───────────┘  └──────┘│
│                                          │
│  48h Wochenstunden pro Mitarbeiter      │
└─────────────────────────────────────────┘
```

**Hinweis:** In der Praxis sind oft 16-17 Mitarbeiter vorhanden (inkl. 1-2 Reserve/Springer), aber die Planung basiert auf 3 Teams mit je 5 Mitarbeitern.

### 2.2 Rotationsmuster

**Festes wöchentliches Rotationsmuster:** F → N → S

```
Woche 1:  Team Alpha = F  |  Team Beta  = N  |  Team Gamma = S
Woche 2:  Team Alpha = N  |  Team Beta  = S  |  Team Gamma = F
Woche 3:  Team Alpha = S  |  Team Beta  = F  |  Team Gamma = N
Woche 4:  Team Alpha = F  |  Team Beta  = N  |  Team Gamma = S  (Wiederholung)
```

**Formel:**
```python
rotation_idx = (woche_nummer + team_index) % 3
schicht = ROTATION_PATTERN[rotation_idx]  # ["F", "N", "S"]
```

### 2.3 Arbeitszeitmodell

- **Wochenarbeitszeit:** 48 Stunden
- **Tägliche Schichtdauer:** 8 Stunden
- **Werktage:** Montag bis Freitag (5 Tage)
- **Wochenende:** Samstag und Sonntag (2 Tage)

**Theoretische Wochenrechnung:**
- 48h ÷ 8h = 6 Schichttage pro Woche
- 5 Werktage + mindestens 1 Wochenendtag

---

## 3. Harte Constraints (Pflichtregeln)

Diese Regeln **MÜSSEN** zu 100% eingehalten werden. Ein Verstoß macht den Plan ungültig.

### 3.1 Team-Schicht-Zuweisung

**Regel:** Jedes Team hat **genau EINE** Schicht pro Woche.

```python
für jedes Team, jede Woche:
    Summe(team_schicht[team][woche][schicht]) == 1
```

**Bedeutung:**
- Pro Woche arbeitet das gesamte Team dieselbe Schicht (F, N oder S)
- Kein Team kann mehrere Schichten gleichzeitig haben
- Kein Team darf schichtfrei sein (außer bei Sonderzuweisungen)

---

### 3.2 Team-Rotation (F → N → S)

**Regel:** Teams folgen dem festen Rotationsmuster **F → N → S**.

```python
erwartete_schicht = ROTATION_PATTERN[(woche_idx + team_idx) % 3]
team_schicht[team][woche][erwartete_schicht] == 1
```

**Ausnahmen:**
- Manuell fixierte Schichten (haben Vorrang)
- Teams mit eingeschränkter Schichtzuweisung (z.B. nur F und S)

**Beispiel 4-Wochen-Zyklus:**

| Woche | Team Alpha | Team Beta | Team Gamma |
|-------|------------|-----------|------------|
| 1 | **F** | **N** | **S** |
| 2 | **N** | **S** | **F** |
| 3 | **S** | **F** | **N** |
| 4 | **F** | **N** | **S** |

---

### 3.3 Mindest- und Maximalbesetzung

**Regel:** Für jede Schicht muss die Besetzung innerhalb der definierten Grenzen liegen.

#### 3.3.1 Werktags (Montag–Freitag)

| Schicht | Minimum | Maximum | Kommentar |
|---------|---------|---------|-----------|
| **Früh (F)** | 4 | 5 | Höchste Anforderung |
| **Spät (S)** | 3 | 4 | Mittlere Anforderung |
| **Nacht (N)** | 3 | 3 | Exakt 3 Personen (konfigurierbar) |

**Hinweis:** Die Werte sind in der Datenbank konfigurierbar. Die angegebenen Werte sind die Standard-Defaults bei Systeminitialisierung.

#### 3.3.2 Wochenende (Samstag–Sonntag)

| Schicht | Minimum | Maximum | Kommentar |
|---------|---------|---------|-----------|
| **Früh (F)** | 2 | 3 | Reduzierte Besetzung |
| **Spät (S)** | 2 | 3 | Reduzierte Besetzung |
| **Nacht (N)** | 2 | 3 | Reduzierte Besetzung |

**Constraint:**
```python
für jeden Tag, jede Schicht:
    Min_Besetzung ≤ Anzahl_Mitarbeiter_in_Schicht ≤ Max_Besetzung
```

**Zählung umfasst:**
- Reguläre Team-Mitglieder
- Cross-Team Einsätze (wenn jemand aus einem anderen Team einspringt)
- Wochenend-Schichten

---

### 3.4 Ruhezeiten und verbotene Übergänge

**Regel:** Zwischen zwei Schichten müssen **mindestens 11 Stunden Ruhezeit** liegen.

#### 3.4.1 Schichtzeiten

| Schicht | Beginn | Ende | Nächster Schichtbeginn erlaubt ab |
|---------|--------|------|-----------------------------------|
| F (Früh) | 05:45 | 13:45 | 00:45 (nächster Tag) |
| S (Spät) | 13:45 | 21:45 | 08:45 (nächster Tag) |
| N (Nacht) | 21:45 | 05:45 | 16:45 (nächster Tag) |

#### 3.4.2 Verbotene Übergänge

| Von Schicht | Zu Schicht (nächster Tag) | Ruhezeit | Erlaubt? |
|-------------|--------------------------|----------|----------|
| S (Spät) | F (Früh) | 8h 00min | ❌ **VERBOTEN** |
| N (Nacht) | F (Früh) | 0h 00min | ❌ **VERBOTEN** |
| N (Nacht) | S (Spät) | 8h 00min | ❌ **VERBOTEN** |
| F (Früh) | S (Spät) | 0h 00min | ✅ Erlaubt (gleicher Tag) |
| F (Früh) | N (Nacht) | 8h 00min | ✅ Erlaubt |
| S (Spät) | N (Nacht) | 0h 00min | ✅ Erlaubt (gleicher Tag) |

**Constraint:**
```python
für jeden Mitarbeiter, jeden Tag:
    schicht_heute[S] + schicht_morgen[F] ≤ 1
    schicht_heute[N] + schicht_morgen[F] ≤ 1
    schicht_heute[N] + schicht_morgen[S] ≤ 1
```

---

### 3.5 Abwesenheiten

**Regel:** Während Abwesenheiten darf **keine Schicht** zugewiesen werden.

**Abwesenheitstypen:**
- **U** = Urlaub
- **AU** = Arbeitsunfähigkeit / Krankheit
- **L** = Lehrgang / Schulung

**Constraint:**
```python
für jeden Mitarbeiter, jeden Abwesenheitstag:
    alle_schicht_variablen[mitarbeiter][tag] = 0
```

**Beispiel:**
```
Mitarbeiter A: Urlaub vom 10.01. - 14.01.
→ Keine Schichtzuweisung F, S, N in diesem Zeitraum
→ Keine Cross-Team Einsätze möglich
→ Keine Wochenendarbeit möglich
```

---

### 3.6 Maximal eine Schicht pro Tag

**Regel:** Ein Mitarbeiter kann **maximal eine Schicht** pro Tag arbeiten.

**Varianten:**
- Entweder: Eigene Team-Schicht
- Oder: Cross-Team Einsatz
- Nicht: Beides gleichzeitig

**Constraint:**
```python
für jeden Mitarbeiter, jeden Tag:
    team_schicht[mitarbeiter][tag] + cross_team_schicht[mitarbeiter][tag] ≤ 1
```

---

### 3.7 Arbeitszeit-Limits

#### 3.7.1 Maximale Wochenarbeitszeit

**Regel:** Maximal **48 Stunden pro Woche**

**Constraint:**
```python
für jeden Mitarbeiter, jede Woche:
    Summe(schicht_stunden × arbeitstage) ≤ 48h
```

**Berechnung:**
```
Woche 1 (7 Tage):
  - 5 × F-Schicht (je 8h) = 40h
  - 1 × F-Schicht (Sa) = 8h
  → Total = 48h ✅ OK

Woche 1 (7 Tage):
  - 6 × F-Schicht (je 8h) = 48h
  - 1 × F-Schicht (So) = 8h
  → Total = 56h ❌ VERBOTEN
```

#### 3.7.2 Minimale Gesamtarbeitszeit (Planungszeitraum)

**Regel:** Mitarbeiter müssen ihr Stundensoll über den Planungszeitraum erfüllen.

**Formel:**
```python
tägliches_soll = wöchentliche_arbeitsstunden / 7
erwartete_stunden = tägliches_soll × (gesamttage - abwesenheitstage)

für jeden Mitarbeiter:
    geleistete_stunden ≥ erwartete_stunden
```

**Beispiel Januar 2026 (31 Tage, 48h/Woche):**
```
Tägliches Soll = 48h ÷ 7 = 6,857h/Tag
Erwartete Stunden (31 Tage) = 6,857h × 31 = 212,57h ≈ 213h

Bei 5 Urlaubstagen:
Erwartete Stunden = 6,857h × (31-5) = 6,857h × 26 = 178,28h
```

---

### 3.8 Mindestruhetage zwischen Arbeitsphasen

**Regel:** Zwischen zwei Arbeitsphasen müssen **mindestens 6 aufeinanderfolgende Ruhetage** liegen.

**Constraint:**
```python
wenn Mitarbeiter an Tag X UND Tag Y arbeitet (Y > X + 6):
    → Es müssen mindestens 6 aufeinanderfolgende freie Tage dazwischen liegen
```

**Beispiel:**
```
✅ ERLAUBT:
Tag 1-5: Arbeit (Mo-Fr)
Tag 6-11: Frei (Sa-Do, 6 Tage)
Tag 12-16: Arbeit (Fr-Di)

❌ VERBOTEN:
Tag 1-5: Arbeit (Mo-Fr)
Tag 6-10: Frei (Sa-Mi, 5 Tage)  ← nur 5 Tage!
Tag 11: Arbeit (Do)
```

---

### 3.9 TD (Tagdienst) Zuweisung

**Regel:** **Genau 1 TD pro Woche** (Montag–Freitag)

**Anforderungen:**
- TD darf nur an qualifizierte Mitarbeiter vergeben werden
- TD verhindert reguläre Schichtarbeit in dieser Woche
- TD kann nicht während Abwesenheit vergeben werden

**Constraint:**
```python
für jede Woche:
    Summe(td[qualifizierter_mitarbeiter][woche]) == 1

für jeden Mitarbeiter mit TD:
    reguläre_schichten[mitarbeiter][diese_woche] = 0
```

---

### 3.10 Wöchentlich verfügbarer Mitarbeiter

**Regel:** **Mindestens 1 Mitarbeiter** aus den Schicht-Teams muss **komplett frei** sein.

**Zweck:** Reserve für kurzfristige Vertretungen (Krankheit, Notfälle)

**Constraint:**
```python
für jede Woche:
    mindestens 1 Mitarbeiter hat 0 Arbeitstage in dieser Woche
```

**Beispiel (17 Mitarbeiter, 3 Teams):**
```
Woche 1:
- 14 Mitarbeiter aktiv in Schichten
- 1 Mitarbeiter hat TD
- 1 Mitarbeiter Urlaub
- 1 Mitarbeiter FREI (Reserve) ✅
```

---

### 3.11 Cross-Team Montag-Freitag Blockplanung

**Regel:** Cross-Team Einsätze werden als **komplette Mo-Fr Blöcke** geplant.

**Constraint:**
```python
wenn Mitarbeiter einen Tag Mo-Fr cross-team arbeitet:
    → muss an ALLEN Nicht-Abwesenheits-Werktagen dieser Woche arbeiten
```

**Beispiel:**
```
✅ ERLAUBT:
Mo-Fr: Cross-Team Schicht S (kompletter Block)
Sa-So: Individuell planbar

❌ VERBOTEN:
Mo: Cross-Team S
Di: Frei
Mi-Fr: Cross-Team S  ← Lücke am Dienstag nicht erlaubt
```

---

## 4. Weiche Constraints (Optimierungsziele)

Diese Regeln sind **Optimierungsziele**. Das System versucht sie zu erfüllen, aber Verstöße machen den Plan nicht ungültig.

### 4.1 Blockplanung (Gap Minimierung)

**Ziel:** Arbeitstage zusammenhalten, Lücken vermeiden

**Penalty-Bewertung:**
```python
für jeden Mitarbeiter:
    wenn [Arbeit - Frei - Arbeit] Muster:
        Penalty += 3
```

**Beispiel:**
```
Bevorzugt: ■■■■■□□□□□■■■■  (Blöcke)
Vermeiden:  ■■□■■□■□■□■■□■  (Lücken)
```

**Gewichtung:** 3 Punkte pro Lücke

---

### 4.2 Eigenes Team bevorzugen

**Ziel:** Mitarbeiter sollen primär mit ihrem eigenen Team arbeiten

**Penalty-Bewertung:**
```python
für jeden Mitarbeiter:
    Penalty += Anzahl_Cross_Team_Tage × 1
```

**Gewichtung:** 1 Punkt pro Cross-Team Tag

---

### 4.3 Wochenend-Fairness (Jahresbasis)

**Ziel:** Gerechte Verteilung der Wochenend-Arbeit über das Jahr

**Berechnung:**
```python
für jedes Mitarbeiter-Paar mit gleichen Fähigkeiten:
    ytd_wochenenden_A = bisherige_wochenenden + aktuelle_periode
    ytd_wochenenden_B = bisherige_wochenenden + aktuelle_periode
    
    Penalty += |ytd_wochenenden_A - ytd_wochenenden_B| × 10
```

**Gewichtung:** 10 Punkte pro Differenz (**SEHR HOCH**)

**Beispiel:**
```
Januar-Juni: Mitarbeiter A = 12 Wochenenden, B = 8 Wochenenden
Juli-Planung: System bevorzugt B für Wochenend-Schichten
```

---

### 4.4 Nachtschicht-Fairness (Jahresbasis)

**Ziel:** Gerechte Verteilung der Nachtschichten über das Jahr

**Berechnung:**
```python
für jedes Mitarbeiter-Paar mit gleichen Fähigkeiten:
    ytd_nächte_A = bisherige_nächte + aktuelle_periode
    ytd_nächte_B = bisherige_nächte + aktuelle_periode
    
    Penalty += |ytd_nächte_A - ytd_nächte_B| × 8
```

**Gewichtung:** 8 Punkte pro Differenz (**HOCH**)

---

### 4.5 TD-Fairness

**Ziel:** Gleichmäßige Verteilung der TD-Funktion

**Berechnung:**
```python
für jedes Paar TD-qualifizierter Mitarbeiter:
    Penalty += |td_wochen_A - td_wochen_B| × 4
```

**Gewichtung:** 4 Punkte pro Differenz

---

### 4.6 Wochenend-zu-Wochentag Kontinuität

**Ziel:** Wenn ≥3 Werktage gearbeitet, auch Wochenende arbeiten (Blockeinsatz)

**Penalty-Bewertung:**
```python
für jeden Mitarbeiter, jede Woche:
    wenn werktage_count ≥ 3 UND wochenende_count ≥ 1:
        wenn NICHT (werktage_count ≥ 3 UND wochenende_count ≥ 1):
            Penalty += 2
```

**Gewichtung:** 2 Punkte pro unvollständigem Block

---

## 5. Mindestanforderungen

### 5.1 Minimale Mitarbeiteranzahl (Gesamt)

Um einen Schichtplan mit den **Standardanforderungen** zu erstellen, sind folgende Mindestanzahlen nötig:

#### 5.1.1 Werktags-Anforderung (Mo-Fr)

**Maximaler Tagesbedarf (Worst-Case):**
```
F: max 5 Personen
S: max 4 Personen
N: max 3 Personen
────────────────────
Total: 12 Personen/Tag (gleichzeitig)
```

**Aber:** Team-basierte Planung bedeutet:
- Ein Team arbeitet pro Woche EINE Schicht
- 3 Teams rotieren durch F, N, S

**Minimum pro Team:**
```
Team für F-Schicht: min 4 Personen (Mindestbesetzung F werktags)
Team für S-Schicht: min 3 Personen (Mindestbesetzung S werktags)
Team für N-Schicht: min 3 Personen (Mindestbesetzung N werktags)
```

**Fazit:** Mit **3 Teams à 5 Mitarbeitern = 15 Mitarbeiter** sind alle Mindestanforderungen erfüllbar.

#### 5.1.2 Wochenend-Anforderung (Sa-So)

**Maximaler Tagesbedarf:**
```
F: max 3 Personen
S: max 3 Personen
N: max 3 Personen
────────────────────
Total: 9 Personen/Tag (gleichzeitig)
```

**Mit 15 Mitarbeitern:** ✅ Erfüllbar

**Cross-Team Strategie:**
- Team 1 (5 MA): Arbeitet Werktags F-Schicht
- Am Wochenende: 2-3 Mitarbeiter von Team 1 arbeiten F-Schicht
- Rest ist frei oder arbeitet cross-team

---

### 5.2 Minimale Teamgröße

**Empfehlung: 5 Mitarbeiter pro Team**

**Begründung:**
```
Werktags (Mo-Fr):
- F braucht min 4 → Team braucht min 4 MA
- Bei 4 MA: Kein Puffer für Urlaub/Krankheit!

Mit 5 MA pro Team:
- 1 MA Urlaub → 4 MA verfügbar ✅
- 2 MA Urlaub → 3 MA verfügbar → cross-team nötig
```

**Absolute Mindestgröße:** 4 MA pro Team (ohne Puffer)
**Empfohlene Größe:** 5-6 MA pro Team (mit Puffer)

---

### 5.3 TD-Qualifizierte Mitarbeiter

**Anforderung:** Mindestens **3 TD-qualifizierte Mitarbeiter** im Gesamtsystem

**Begründung:**
```
- 1 TD pro Woche erforderlich
- Bei 4 Wochen: 4 TD-Zuweisungen
- Mit 3 qualifizierten MA: 1-2 TD-Wochen pro MA/Monat
- Bei nur 2 qualifizierten MA: zu hohe Belastung
```

---

### 5.4 Springer / Reserve

**Empfehlung:** +1 bis +2 zusätzliche Mitarbeiter als Reserve

**System mit Reserve:**
```
3 Teams × 5 MA = 15 MA (regulär)
+ 1-2 Springer = 16-17 MA (gesamt)
```

**Springer-Vorteile:**
- Deckt kurzfristige Ausfälle (Krankheit)
- Erlaubt mehr Urlaubskapazität
- Reduziert Cross-Team Bedarf
- Erfüllt "wöchentlich verfügbarer Mitarbeiter" Constraint

---

## 6. Berechnungen und Formeln

### 6.1 Benötigte Schichttage pro Mitarbeiter

**Ziel:** Alle Mitarbeiter erfüllen ihr Stundensoll

#### 6.1.1 Monatliche Berechnung (Beispiel Januar 2026)

**Gegeben:**
- Kalendermonat: Januar 2026 = 31 Tage
- Wochenarbeitszeit: 48 Stunden
- Schichtdauer: 8 Stunden/Tag

**Berechnung:**
```
Tägliches Arbeitssoll = 48h / 7 Tage = 6,857 h/Tag

Monatliches Soll (31 Tage):
= 6,857 h/Tag × 31 Tage
= 212,57 Stunden
≈ 213 Stunden

Benötigte Schichttage:
= 213h / 8h pro Schicht
= 26,625 Tage
≈ 27 Schichttage
```

**Fazit:** Ein Mitarbeiter muss im Januar 2026 etwa **27 von 31 Tagen** arbeiten.

#### 6.1.2 Praktische Aufteilung (Januar 2026)

**Januar 2026 Kalender:**
```
       Januar 2026
Mo Di Mi Do Fr Sa So
          1  2  3  4  5
 6  7  8  9 10 11 12
13 14 15 16 17 18 19
20 21 22 23 24 25 26
27 28 29 30 31
```

**Arbeitstage-Zählung:**
- Werktage (Mo-Fr): 22 Tage
- Wochenendtage (Sa-So): 9 Tage
- Gesamt: 31 Tage

**Realistische Verteilung (Team-basiert):**
```
Woche 1 (01.-05.01.): 5 Werktage + 1 Wochenendtag = 6 Tage (48h)
Woche 2 (06.-12.01.): 5 Werktage + 1 Wochenendtag = 6 Tage (48h)
Woche 3 (13.-19.01.): 5 Werktage + 1 Wochenendtag = 6 Tage (48h)
Woche 4 (20.-26.01.): 5 Werktage + 1 Wochenendtag = 6 Tage (48h)
Woche 5 (27.-31.01.): 5 Werktage (Do-Fr nur 2 Tage) = 2-3 Tage

Gesamt: 25-26 Arbeitstage → ca. 200-208 Stunden
```

**Mit Flexibilität:** 24-27 Arbeitstage je nach Wochenend-Einsätzen

---

### 6.2 Gesamtschicht-Bedarf pro Tag

#### 6.2.1 Werktag (z.B. Montag)

**Anforderung:**
```
F: 4-5 Personen
S: 3-4 Personen
N: 3 Personen
──────────────────
Total: 10-12 Personen/Schicht
       30-36 Personen-Schichten/Tag (bei 3 Schichten)
```

**Mit 15 Mitarbeitern:**
```
- Team Alpha (5 MA): Schicht F (alle 5 arbeiten) → 5 Personen
- Team Beta (5 MA): Schicht N (alle 5 arbeiten) → 5 Personen (aber nur 3 benötigt)
- Team Gamma (5 MA): Schicht S (alle 5 arbeiten) → 5 Personen (aber nur 3-4 benötigt)

Lösung: Nicht alle Teammitglieder müssen jeden Tag arbeiten
→ System plant individuell innerhalb Team-Schicht
```

#### 6.2.2 Wochenendtag (z.B. Samstag)

**Anforderung:**
```
F: 2-3 Personen
S: 2-3 Personen
N: 2-3 Personen
──────────────────
Total: 6-9 Personen/Schicht
       18-27 Personen-Schichten/Tag
```

**Mit 15 Mitarbeitern:**
```
- 6-9 Mitarbeiter arbeiten am Samstag
- 6-9 Mitarbeiter bleiben frei
```

---

### 6.3 Urlaubskapazität

**Frage:** Wie viel Urlaub ist gleichzeitig möglich?

**Berechnung (Worst-Case):**
```
Werktag-Bedarf: 10-12 Personen
Verfügbar: 15 Mitarbeiter
Reserve: 1 Mitarbeiter (wöchentlich frei)
──────────────────────────────────────
Urlaubskapazität: 15 - 12 - 1 = 2 Mitarbeiter

Max. gleichzeitiger Urlaub: 2-3 Mitarbeiter
```

**Hinweis:** Mit Springer (17 MA) erhöht sich die Kapazität auf 4-5 Mitarbeiter.

---

### 6.4 Cross-Team Einsätze

**Wann nötig?**
```
wenn Team_Größe < Mindestbesetzung_Schicht:
    → Cross-Team Einsatz erforderlich
```

**Beispiel:**
```
Team Alpha (5 MA) hat Schicht F (Mindest 4)
- 2 MA im Urlaub
- Nur 3 MA verfügbar
- 1 MA aus Team Beta arbeitet cross-team (F-Schicht)
```

**Häufigkeit:** Ca. 10-20% der Einsätze in der Praxis

---

## 7. Abhängigkeiten-Diagramm

### 7.1 Haupt-Abhängigkeiten

```
┌────────────────────────────────────────────────────────────┐
│                   SCHICHTPLAN-ERSTELLUNG                    │
└────────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
    ┌──────────────┐ ┌──────────┐ ┌─────────────┐
    │   TEAMS      │ │MITARBEITER│ │ SCHICHTTYPEN│
    │              │ │           │ │             │
    │ - 3 Teams    │ │- 15 MA    │ │ - F/N/S     │
    │ - Rotation   │ │- Qualif.  │ │ - Zeiten    │
    │ - Größe: 5   │ │- Team-ID  │ │ - Besetzung │
    └──────┬───────┘ └─────┬─────┘ └──────┬──────┘
           │               │               │
           └───────────────┼───────────────┘
                           ▼
            ┌──────────────────────────┐
            │   PLANUNGSZEITRAUM        │
            │                           │
            │  - Start/Ende Datum       │
            │  - Wocheneinteilung       │
            │  - Werktage/Wochenenden   │
            └─────────────┬─────────────┘
                          │
           ┌──────────────┼──────────────┐
           ▼              ▼              ▼
    ┌──────────┐  ┌─────────────┐  ┌────────────┐
    │ABWESENHEIT│ │HARTE REGELN │  │WEICHE REGELN│
    │           │ │             │  │             │
    │ - Urlaub  │ │- Besetzung  │  │- Fairness   │
    │ - Krank   │ │- Ruhezeit   │  │- Blöcke     │
    │ - Lehrgang│ │- Max Stunden│  │- Präferenz  │
    └─────┬─────┘ └──────┬──────┘  └──────┬──────┘
          │              │                │
          └──────────────┼────────────────┘
                         ▼
            ┌────────────────────────┐
            │   OR-TOOLS SOLVER      │
            │                        │
            │  - CP-SAT Algorithmus  │
            │  - Constraint Solving  │
            │  - Optimierung         │
            └───────────┬────────────┘
                        ▼
            ┌────────────────────────┐
            │   SCHICHTPLAN          │
            │                        │
            │  - Tages-Zuweisungen   │
            │  - TD-Zuweisungen      │
            │  - Statistiken         │
            └────────────────────────┘
```

### 7.2 Constraint-Hierarchie

```
EBENE 1: FUNDAMENTALE CONSTRAINTS
├─ Team-Schicht-Zuweisung (1 Schicht/Team/Woche)
├─ Team-Rotation (F → N → S)
└─ Abwesenheit (Keine Arbeit während Urlaub/Krank)

EBENE 2: PERSONELLE CONSTRAINTS
├─ Max 1 Schicht/Person/Tag
├─ Mitarbeiter ↔ Team Linkage
└─ Qualifikationen (TD, etc.)

EBENE 3: BETRIEBLICHE CONSTRAINTS
├─ Mindestbesetzung (4/3/3 werktags, 2/2/2 WE)
├─ Maximalbesetzung (5/4/3 werktags, 3/3/3 WE)
└─ TD-Zuweisung (1/Woche)

EBENE 4: ARBEITSSCHUTZ CONSTRAINTS
├─ Ruhezeiten (11h zwischen Schichten)
├─ Verbotene Übergänge (S→F, N→F, N→S)
├─ Max Wochenstunden (48h)
├─ Min Gesamtstunden (Stundensoll)
└─ Min Ruhetage zwischen Blöcken (6 Tage)

EBENE 5: OPTIMIERUNGSZIELE
├─ Wochenend-Fairness (Gewicht: 10)
├─ Nachtschicht-Fairness (Gewicht: 8)
├─ TD-Fairness (Gewicht: 4)
├─ Gap-Minimierung (Gewicht: 3)
├─ Kontinuität (Gewicht: 2)
└─ Eigenes Team bevorzugen (Gewicht: 1)
```

---

## 8. Beispiel: Januar 2026

### 8.1 Kalender und Wocheneinteilung

```
           JANUAR 2026
     Mo  Di  Mi  Do  Fr  Sa  So
                 1   2   3   4   5   → Woche 1 (Do-So, 4 Tage)
      6   7   8   9  10  11  12       → Woche 2 (Mo-So, 7 Tage)
     13  14  15  16  17  18  19       → Woche 3 (Mo-So, 7 Tage)
     20  21  22  23  24  25  26       → Woche 4 (Mo-So, 7 Tage)
     27  28  29  30  31               → Woche 5 (Mo-Fr, 5 Tage)

Werktage: 22 (Mo-Fr)
Wochenenden: 9 (Sa-So)
Gesamt: 31 Tage
```

### 8.2 Team-Rotationsplan

**Annahme:** Januar startet mit Woche 1 = Rotation Index 0

| Woche | Datum | Team Alpha | Team Beta | Team Gamma |
|-------|-------|------------|-----------|------------|
| **Woche 1** | 01.-05.01. | **F** (Früh) | **N** (Nacht) | **S** (Spät) |
| **Woche 2** | 06.-12.01. | **N** (Nacht) | **S** (Spät) | **F** (Früh) |
| **Woche 3** | 13.-19.01. | **S** (Spät) | **F** (Früh) | **N** (Nacht) |
| **Woche 4** | 20.-26.01. | **F** (Früh) | **N** (Nacht) | **S** (Spät) |
| **Woche 5** | 27.-31.01. | **N** (Nacht) | **S** (Spät) | **F** (Früh) |

### 8.3 Beispiel-Mitarbeiter

**Team Alpha (5 Mitarbeiter):**
1. Max Müller (MA-1001)
2. Anna Schmidt (MA-1002)
3. Peter Weber (MA-1003)
4. Lisa Meyer (MA-1004) - TD-qualifiziert
5. Tom Wagner (MA-1005)

**Team Beta (5 Mitarbeiter):**
6. Julia Becker (MA-2001)
7. Michael Schulz (MA-2002) - TD-qualifiziert
8. Sarah Hoffmann (MA-2003)
9. Daniel Koch (MA-2004)
10. Laura Bauer (MA-2005)

**Team Gamma (5 Mitarbeiter):**
11. Markus Richter (MA-3001)
12. Stefanie Klein (MA-3002)
13. Andreas Wolf (MA-3003) - TD-qualifiziert
14. Nicole Schröder (MA-3004)
15. Christian Neumann (MA-3005)

### 8.4 Beispiel-Abwesenheiten

```
Anna Schmidt (MA-1002): Urlaub 13.01. - 17.01. (5 Tage, Woche 3)
Michael Schulz (MA-2002): Lehrgang 20.01. - 22.01. (3 Tage, Woche 4)
```

### 8.5 Detaillierte Wochenplanung

#### Woche 1 (01.-05.01.): Do-So, 4 Tage

**Team-Zuweisungen:**
- Team Alpha → **F** (Frühschicht 05:45-13:45)
- Team Beta → **N** (Nachtschicht 21:45-05:45)
- Team Gamma → **S** (Spätschicht 13:45-21:45)

**Tagesplan (Beispiel Freitag, 02.01.):**

| Schicht | Werktag Bedarf | Zugewiesene Mitarbeiter | Team | Anzahl |
|---------|----------------|-------------------------|------|--------|
| **F** | min 4, max 5 | Max, Anna, Peter, Lisa, Tom | Alpha | 5 ✅ |
| **N** | min 3, max 3 | Julia, Michael, Sarah | Beta | 3 ✅ |
| **S** | min 3, max 4 | Markus, Stefanie, Andreas | Gamma | 3 ✅ |

**Tagesplan (Beispiel Samstag, 03.01. - Wochenende):**

| Schicht | Wochenend Bedarf | Zugewiesene Mitarbeiter | Team | Anzahl |
|---------|------------------|-------------------------|------|--------|
| **F** | min 2, max 3 | Max, Peter, Tom | Alpha | 3 ✅ |
| **N** | min 2, max 3 | Julia, Michael | Beta | 2 ✅ |
| **S** | min 2, max 3 | Markus, Andreas | Gamma | 2 ✅ |

**Wochenstatistik:**
- Arbeitstage: 4 Tage (Do-So)
- Stunden pro MA: 4 × 8h = 32h (< 48h OK ✅)

---

#### Woche 2 (06.-12.01.): Mo-So, 7 Tage

**Team-Zuweisungen:**
- Team Alpha → **N** (Nachtschicht)
- Team Beta → **S** (Spätschicht)
- Team Gamma → **F** (Frühschicht)

**Tagesplan (Beispiel Montag, 06.01.):**

| Schicht | Werktag Bedarf | Zugewiesene Mitarbeiter | Team | Anzahl |
|---------|----------------|-------------------------|------|--------|
| **F** | min 4, max 5 | Markus, Stefanie, Andreas, Nicole, Christian | Gamma | 5 ✅ |
| **S** | min 3, max 4 | Julia, Sarah, Daniel, Laura | Beta | 4 ✅ |
| **N** | min 3, max 3 | Max, Anna, Peter | Alpha | 3 ✅ |

**TD-Zuweisung Woche 2:** Lisa Meyer (MA-1004, TD-qualifiziert)
- Lisa hat TD → arbeitet NICHT in regulären Schichten diese Woche

**Wochenstatistik:**
- Arbeitstage: Max. 6 Tage (5 Werktage + 1 Wochenendtag)
- Stunden pro MA: Max. 48h (Limit ✅)

---

#### Woche 3 (13.-19.01.): Mo-So, 7 Tage

**Team-Zuweisungen:**
- Team Alpha → **S** (Spätschicht)
- Team Beta → **F** (Frühschicht)
- Team Gamma → **N** (Nachtschicht)

**Besonderheit: Anna Schmidt (Team Alpha) im Urlaub 13.-17.01.**

**Tagesplan (Beispiel Mittwoch, 15.01.):**

| Schicht | Werktag Bedarf | Zugewiesene Mitarbeiter | Team | Anzahl | Bemerkung |
|---------|----------------|-------------------------|------|--------|-----------|
| **F** | min 4, max 5 | Julia, Michael, Sarah, Daniel, Laura | Beta | 5 ✅ | |
| **S** | min 3, max 4 | Max, Peter, Lisa, Tom | Alpha | 4 ✅ | Anna im Urlaub |
| **N** | min 3, max 3 | Markus, Stefanie, Andreas | Gamma | 3 ✅ | |

**Wochenstatistik:**
- Anna: 0 Arbeitstage (Urlaub)
- Andere Team Alpha: 5-6 Arbeitstage

---

#### Woche 4 (20.-26.01.): Mo-So, 7 Tage

**Team-Zuweisungen:**
- Team Alpha → **F** (Frühschicht)
- Team Beta → **N** (Nachtschicht)
- Team Gamma → **S** (Spätschicht)

**Besonderheit: Michael Schulz (Team Beta) im Lehrgang 20.-22.01.**

**Tagesplan (Beispiel Dienstag, 21.01.):**

| Schicht | Werktag Bedarf | Zugewiesene Mitarbeiter | Team/Cross | Anzahl | Bemerkung |
|---------|----------------|-------------------------|------------|--------|-----------|
| **F** | min 4, max 5 | Max, Anna, Peter, Lisa, Tom | Alpha | 5 ✅ | |
| **N** | min 3, max 3 | Julia, Sarah, Daniel | Beta + Cross | 3 ✅ | Michael im Lehrgang |
| **S** | min 3, max 4 | Markus, Stefanie, Andreas, Nicole | Gamma | 4 ✅ | |

**Cross-Team:** Eventuell muss 1 MA aus Alpha oder Gamma cross-team in N-Schicht einspringen (wenn Beta < 3 MA)

**TD-Zuweisung Woche 4:** Andreas Wolf (MA-3003, TD-qualifiziert)

---

#### Woche 5 (27.-31.01.): Mo-Fr, 5 Tage

**Team-Zuweisungen:**
- Team Alpha → **N** (Nachtschicht)
- Team Beta → **S** (Spätschicht)
- Team Gamma → **F** (Frühschicht)

**Tagesplan (Beispiel Donnerstag, 29.01.):**

| Schicht | Werktag Bedarf | Zugewiesene Mitarbeiter | Team | Anzahl |
|---------|----------------|-------------------------|------|--------|
| **F** | min 4, max 5 | Markus, Stefanie, Nicole, Christian | Gamma | 4 ✅ |
| **S** | min 3, max 4 | Julia, Michael, Sarah, Daniel | Beta | 4 ✅ |
| **N** | min 3, max 3 | Max, Anna, Peter | Alpha | 3 ✅ |

**Wochenstatistik:**
- Arbeitstage: 5 Tage (nur Werktage, kein Wochenende in dieser Teil-Woche)
- Stunden pro MA: 5 × 8h = 40h

---

### 8.6 Monatliche Statistiken (Beispiel)

**Gesamtübersicht Januar 2026:**

| Mitarbeiter | Team | Arbeitstage | Stunden | F-Schichten | N-Schichten | S-Schichten | Wochenenden | TD |
|-------------|------|-------------|---------|-------------|-------------|-------------|-------------|----|
| Max Müller | Alpha | 26 | 208h | 10 | 10 | 6 | 4 | 0 |
| Anna Schmidt | Alpha | 21 | 168h | 8 | 8 | 5 | 3 | 0 |
| Peter Weber | Alpha | 27 | 216h | 11 | 10 | 6 | 4 | 0 |
| Lisa Meyer | Alpha | 20 | 160h | 9 | 6 | 5 | 3 | 1 |
| Tom Wagner | Alpha | 26 | 208h | 10 | 10 | 6 | 4 | 0 |
| Julia Becker | Beta | 26 | 208h | 6 | 10 | 10 | 4 | 0 |
| Michael Schulz | Beta | 23 | 184h | 5 | 9 | 9 | 3 | 0 |
| Sarah Hoffmann | Beta | 27 | 216h | 6 | 11 | 10 | 4 | 0 |
| Daniel Koch | Beta | 26 | 208h | 6 | 10 | 10 | 4 | 0 |
| Laura Bauer | Beta | 26 | 208h | 6 | 10 | 10 | 4 | 0 |
| Markus Richter | Gamma | 26 | 208h | 10 | 6 | 10 | 4 | 0 |
| Stefanie Klein | Gamma | 27 | 216h | 11 | 6 | 10 | 4 | 0 |
| Andreas Wolf | Gamma | 20 | 160h | 8 | 3 | 9 | 3 | 1 |
| Nicole Schröder | Gamma | 26 | 208h | 10 | 6 | 10 | 4 | 0 |
| Christian Neumann | Gamma | 26 | 208h | 10 | 6 | 10 | 4 | 0 |

**Durchschnitt:**
- Arbeitstage: ~25 Tage
- Stunden: ~200h (Soll: ~213h)
- Wochenend-Einsätze: 3-4 mal

**Abweichungen vom Soll:**
- Anna Schmidt: -5 Tage (Urlaub)
- Michael Schulz: -3 Tage (Lehrgang)
- Lisa Meyer / Andreas Wolf: -6 Tage (TD-Wochen)

---

### 8.7 Validierung gegen Constraints

**Harte Constraints:**

| Constraint | Status | Validierung |
|------------|--------|-------------|
| Team-Rotation (F→N→S) | ✅ | Alle Wochen folgen Muster |
| Mindestbesetzung Werktags | ✅ | F≥4, S≥3, N≥3 eingehalten |
| Mindestbesetzung Wochenende | ✅ | Alle Schichten ≥2 |
| Ruhezeit 11h | ✅ | Keine S→F, N→F Übergänge |
| Max 48h/Woche | ✅ | Alle Mitarbeiter ≤48h |
| Abwesenheiten | ✅ | Keine Schichten während U/L |
| TD 1x/Woche | ✅ | Genau 1 TD pro Woche |
| Wöchentlich frei | ✅ | Mind. 1 MA pro Woche frei |

**Weiche Constraints:**

| Constraint | Bewertung | Kommentar |
|------------|-----------|-----------|
| Wochenend-Fairness | ⭐⭐⭐⭐⭐ | Gleichmäßig 3-4 WE pro MA |
| Nachtschicht-Fairness | ⭐⭐⭐⭐⭐ | Ausgeglichen durch Rotation |
| Blockplanung | ⭐⭐⭐⭐ | Minimale Lücken |
| Eigenes Team | ⭐⭐⭐⭐⭐ | Wenige Cross-Team Einsätze |
| TD-Fairness | ⭐⭐⭐⭐⭐ | Gleichmäßig verteilt |

---

## 9. Zusammenfassung und Fazit

### 9.1 Kernanforderungen erfüllt

✅ **3 Teams mit je 5 Mitarbeitern:** Mindestanforderung erfüllt
✅ **48h Wochenstunden:** Durchschnittlich 25-27 Arbeitstage/Monat
✅ **Mindestbesetzung:** Werktags (4/3/3), Wochenende (2/2/2)
✅ **Feste Rotation:** F → N → S Muster eingehalten
✅ **Fairness:** Wochenenden, Nachtschichten, TD gleichmäßig verteilt

### 9.2 Systemstärken

🎯 **Automatische Optimierung:** OR-Tools findet beste Lösung
🎯 **Regelkonformität:** 100% Einhaltung harter Constraints
🎯 **Fairness:** Gleichmäßige Belastungsverteilung
🎯 **Flexibilität:** Cross-Team Einsätze bei Bedarf
🎯 **Transparenz:** Alle Regeln dokumentiert und nachvollziehbar

### 9.3 Empfehlungen

💡 **Reserve-Mitarbeiter:** +1-2 Springer für höhere Urlaubskapazität
💡 **TD-Qualifikation:** Min. 3 qualifizierte Mitarbeiter
💡 **Urlaubsplanung:** Max. 2-3 MA gleichzeitig im Urlaub
💡 **Monitoring:** Monatliche Überprüfung der Fairness-Metriken

---

**Version 2.1 - Python Edition**

Entwickelt von **Timo Braun** mit ❤️ für effiziente Schichtverwaltung

Powered by **Google OR-Tools CP-SAT Solver**

© 2025 Fritz Winter Eisengießerei GmbH & Co. KG
