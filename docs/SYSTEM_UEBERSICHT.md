# 📊 SCHICHTPLANUNGS-SYSTEM: VOLLSTÄNDIGE ÜBERSICHT

**Version 2.1 - Python Edition** | Umfassende Darstellung des Schichtplanungssystems

Entwickelt von **Timo Braun** für Fritz Winter Eisengießerei GmbH & Co. KG

---

## 🎯 EXECUTIVE SUMMARY

Dieses Dokument bietet eine **vollständige und eindeutige Darstellung** des automatischen Schichtplanungssystems, einschließlich aller Regeln, Abhängigkeiten, Mindestanforderungen und praktischer Beispiele.

### Kern-Anforderungen (gemäß Aufgabenstellung)

✅ **3 Standard-Schichten:** Früh (F), Spät (S), Nacht (N)
✅ **3 Teams mit je 5 Mitarbeitern:** 15 Mitarbeiter gesamt
✅ **48h Wochenstunden:** Pro Mitarbeiter
✅ **Mindestbesetzung:**
   - Früh: min 4 (werktags), min 2 (Wochenende)
   - Spät: min 3 (werktags), min 2 (Wochenende)
   - Nacht: min 3 (werktags), min 2 (Wochenende)

---

## 📚 DOKUMENTATIONS-STRUKTUR

Diese vollständige Dokumentation besteht aus mehreren spezialisierten Dokumenten:

### 1. **[SCHICHTPLANUNG_REGELN.md](SCHICHTPLANUNG_REGELN.md)** ⭐ HAUPTDOKUMENT
   - Alle harten Constraints (Pflichtregeln)
   - Alle weichen Constraints (Optimierungsziele)
   - Mindestanforderungen (Mitarbeiter, Teams, Qualifikationen)
   - Berechnungen und Formeln
   - Beispiel Januar 2026 mit vollständiger Planung

### 2. **[SYSTEM_DIAGRAMME.md](SYSTEM_DIAGRAMME.md)** 📊 VISUELLE DARSTELLUNG
   - System-Architektur Diagramme
   - Team-Rotationsdiagramme
   - Constraint-Hierarchie
   - Datenfluss-Diagramme
   - Entscheidungsbäume
   - Zeitliche Abläufe

### 3. **[JANUAR_2026_BEISPIEL.md](JANUAR_2026_BEISPIEL.md)** 📅 PRAKTISCHES BEISPIEL
   - Vollständiger Schichtplan für Januar 2026
   - 3 Teams mit je 5 Mitarbeitern
   - Wöchentliche Rotation F → N → S
   - Detaillierte Statistiken
   - Constraint-Validierung

### 4. **[SHIFT_PLANNING_ALGORITHM.md](SHIFT_PLANNING_ALGORITHM.md)** 🤖 TECHNISCHE DETAILS
   - OR-Tools CP-SAT Solver
   - Algorithmus-Implementierung
   - Performance-Optimierung

---

## 🏗️ SYSTEM-KONZEPT

### Planungsansatz: Team-basierte Rotation

```
┌─────────────────────────────────────────────┐
│    TEAM-BASIERTE SCHICHTPLANUNG             │
│                                              │
│  3 Teams rotieren wöchentlich               │
│  durch 3 Schichten (F → N → S)              │
│                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │Team Alpha│  │ Team Beta│  │Team Gamma│ │
│  │  5 MA    │  │  5 MA    │  │  5 MA    │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       │             │              │        │
│       ▼             ▼              ▼        │
│    Woche 1       Woche 2       Woche 3     │
│      F              N              S        │
│      N              S              F        │
│      S              F              N        │
│                                              │
└─────────────────────────────────────────────┘
```

**Vorteile:**
- ⚡ Effiziente Planung (ganze Teams statt Einzelpersonen)
- 🔄 Faire Verteilung (alle Teams durchlaufen alle Schichten)
- 📊 Vorhersagbar (festes Rotationsmuster)
- 🎯 Optimierbar (durch OR-Tools Solver)

---

## 📋 REGELWERK: ÜBERSICHT

### FESTE REGELN (Harte Constraints) ❌ DÜRFEN NICHT VERLETZT WERDEN

Diese Regeln sind **absolut verpflichtend** und werden zu 100% eingehalten:

#### 1. **Team-Organisation**
- ✓ Genau 1 Schicht pro Team pro Woche
- ✓ Feste Rotation: F → N → S (wöchentlich)
- ✓ Max. 1 Schicht pro Person pro Tag

#### 2. **Besetzung**
- ✓ **Werktags (Mo-Fr):**
  - Früh: 4-5 Personen
  - Spät: 3-4 Personen
  - Nacht: 3 Personen (exakt)
- ✓ **Wochenende (Sa-So):**
  - Alle Schichten: 2-3 Personen

#### 3. **Arbeitsschutz**
- ✓ Min. 11 Stunden Ruhezeit zwischen Schichten
- ✓ Verbotene Übergänge: S→F, N→F, N→S
- ✓ Max. 48 Stunden pro Woche
- ✓ Min. 6 aufeinanderfolgende Ruhetage zwischen Arbeitsphasen

#### 4. **Abwesenheiten**
- ✓ Keine Schichten während Urlaub (U)
- ✓ Keine Schichten während Krankheit (AU)
- ✓ Keine Schichten während Lehrgang (L)

#### 5. **Zusatzfunktionen**
- ✓ Genau 1 TD (Tagdienst) pro Woche (Mo-Fr)
- ✓ Mind. 1 Mitarbeiter pro Woche komplett frei (Reserve)

### WEICHE REGELN (Optimierungsziele) 🎯 WERDEN OPTIMIERT

Diese Ziele werden bestmöglich erreicht, Abweichungen sind möglich:

| Ziel | Gewicht | Bedeutung |
|------|---------|-----------|
| **Wochenend-Fairness** | ⭐⭐⭐⭐⭐ (10) | Gleiche WE-Anzahl über Jahr |
| **Nachtschicht-Fairness** | ⭐⭐⭐⭐ (8) | Gleiche Nacht-Anzahl über Jahr |
| **TD-Fairness** | ⭐⭐⭐ (4) | Gleiche TD-Verteilung |
| **Gap-Minimierung** | ⭐⭐⭐ (3) | Zusammenhängende Arbeitsblöcke |
| **Wochenend-Kontinuität** | ⭐⭐ (2) | Wenn 3+ Werktage → auch WE |
| **Eigenes Team** | ⭐ (1) | Cross-Team vermeiden |

---

## 📐 MINDESTANFORDERUNGEN

### 🧑‍🤝‍🧑 Mitarbeiter-Anforderungen

#### **MINIMUM (ohne Reserve):**
```
3 Teams × 4 Mitarbeiter = 12 Mitarbeiter

ABER: Kein Puffer für Urlaub/Krankheit!
```

#### **EMPFOHLEN (mit Puffer):**
```
3 Teams × 5 Mitarbeiter = 15 Mitarbeiter

+ 1-2 Springer = 16-17 Mitarbeiter (optimal)
```

**Begründung:**
- Bei 5 MA pro Team: 1 MA Urlaub → 4 MA verfügbar ✅
- Bei 4 MA pro Team: 1 MA Urlaub → 3 MA verfügbar ⚠️ (Cross-Team nötig)

### 👨‍🏫 Qualifikations-Anforderungen

```
TD-Qualifizierte: Mind. 3 Mitarbeiter
(Für wöchentliche TD-Zuweisung bei 4 Wochen)

Team-Leiter: Optional, aber empfohlen
(Für Koordination und Kommunikation)
```

### ⏰ Verfügbarkeits-Anforderungen

**Pro Team pro Woche:**
```
Werktags (Mo-Fr, 5 Tage):
  - Min. 3 MA verfügbar (für Mindestbesetzung)
  - Optimal: 4-5 MA verfügbar

Wochenende (Sa-So, 2 Tage):
  - Min. 2 MA verfügbar
  - Optimal: 3 MA verfügbar

Gesamt Woche:
  - Min. 3 MA ohne Abwesenheit
  - Optimal: 5 MA ohne Abwesenheit
```

### 📊 Kapazitäts-Berechnungen

#### **Gleichzeitiger Urlaub möglich:**
```
Gesamt: 15 Mitarbeiter
Werktags-Bedarf: 10-12 Personen (4+3+3 bis 5+4+3)
Reserve: 1 Person (wöchentlich frei)
────────────────────────────────────────
Urlaubskapazität: 15 - 12 - 1 = 2 Mitarbeiter

→ Max. 2-3 Mitarbeiter gleichzeitig im Urlaub
```

**Mit Springer (17 MA):**
```
Urlaubskapazität: 17 - 12 - 1 = 4 Mitarbeiter
→ Deutlich flexibler!
```

---

## 🧮 BERECHNUNGEN: SCHICHTTAGE

### Berechnung: Benötigte Arbeitstage pro Monat

**Formel:**
```
Tägliches Soll = Wochenstunden / 7 Tage
Monatliches Soll = Tägliches Soll × Kalendertage
Benötigte Schichttage = Monatliches Soll / 8 Stunden
```

**Beispiel Januar 2026 (31 Tage, 48h/Woche):**
```
Tägliches Soll = 48h / 7 = 6,857 h/Tag
Monatliches Soll = 6,857 h × 31 = 212,57h ≈ 213h
Benötigte Schichttage = 213h / 8h = 26,6 ≈ 27 Tage

→ Ein Mitarbeiter muss ca. 27 von 31 Tagen arbeiten
```

**Praktische Verteilung (Team-basiert):**
```
5 Wochen à 6 Arbeitstage = 30 Tage
- 3-4 Tage frei/Urlaub = 26-27 Arbeitstage ✅
```

### Berechnung: Jahres-Urlaubstage

**48h-Woche, 52 Wochen:**
```
Jahresarbeitszeit = 48h × 52 = 2.496h
Bei 8h/Tag = 312 Arbeitstage/Jahr

Bei 365 Kalendertagen:
- 104 Wochenendtage (falls nicht gearbeitet)
- 261 Werktage
- Davon: ~312 Arbeitstage nötig

→ Minimal -51 Tage "Über-Kapazität"
   (für Urlaub, Feiertage, Krankheit)
```

**Realistischer:** Mit Wochenend-Arbeit verschiebt sich die Rechnung.

### Berechnung: Cross-Team Bedarf

**Wann erforderlich?**
```
IF (verfügbare_team_mitglieder < mindestbesetzung):
    → Cross-Team Einsatz nötig

Beispiel:
Team Alpha (5 MA), Schicht F (min 4)
- 2 MA im Urlaub
- Nur 3 MA verfügbar < 4 benötigt
→ 1 MA aus anderem Team (Cross-Team)
```

**Häufigkeit:** Ca. 10-20% der Schichten in der Praxis

---

## 🔄 WIE DAS SYSTEM FUNKTIONIERT

### Schritt-für-Schritt Ablauf

```
1️⃣ DATEN SAMMELN
   ├─ Mitarbeiter (Name, Team, Qualifikationen)
   ├─ Teams (Größe, erlaubte Schichten)
   ├─ Schichttypen (F/N/S: Zeiten, Besetzung)
   ├─ Abwesenheiten (Urlaub, Krankheit, Lehrgang)
   └─ Zeitraum (Start, Ende, Wochen)

2️⃣ MODELL ERSTELLEN
   ├─ Variablen: team_shift[team][woche][schicht]
   ├─ Variablen: employee_active[ma][tag]
   └─ Zielfunktion: Fairness minimieren

3️⃣ CONSTRAINTS HINZUFÜGEN
   ├─ Harte Constraints (MÜSSEN erfüllt sein)
   │  ├─ Team-Rotation
   │  ├─ Besetzung
   │  ├─ Ruhezeit
   │  └─ Arbeitszeit
   │
   └─ Weiche Constraints (werden optimiert)
      ├─ Fairness (Gewicht: 10)
      ├─ Blöcke (Gewicht: 3)
      └─ Präferenz (Gewicht: 1)

4️⃣ SOLVER AUSFÜHREN
   ├─ Google OR-Tools CP-SAT
   ├─ Zeitlimit: 300 Sekunden (5 Min)
   ├─ Parallele Worker: 8
   └─ Suche: Branch & Bound Algorithmus

5️⃣ LÖSUNG EXTRAHIEREN
   ├─ Für jeden Mitarbeiter, jeden Tag:
   │  → Welche Schicht? (F/N/S oder frei)
   ├─ TD-Zuweisungen pro Woche
   └─ Statistiken berechnen

6️⃣ VALIDIEREN
   ├─ Alle harten Constraints erfüllt?
   ├─ Besetzung in Grenzen?
   └─ Keine Regelversäße?

7️⃣ SPEICHERN & VERÖFFENTLICHEN
   ├─ Datenbank aktualisieren
   ├─ Export (PDF, Excel, CSV)
   └─ Web-Oberfläche anzeigen
```

### Entscheidungslogik: Kann MA X an Tag Y Schicht Z arbeiten?

```
START
  │
  ├─► Abwesend (U/AU/L)? ──────► ❌ NEIN
  │   └─► Nein → Weiter
  │
  ├─► Team hat Schicht Z diese Woche? ──► Nein → Cross-Team prüfen
  │   └─► Ja → Weiter                         └─► Erlaubt? ──► ❌ NEIN
  │                                                └─► Ja → Weiter
  │
  ├─► Bereits andere Schicht heute? ──────► ❌ NEIN (Max 1/Tag)
  │   └─► Nein → Weiter
  │
  ├─► Verletzt 11h Ruhezeit? ──────────────► ❌ NEIN
  │   └─► Nein → Weiter
  │
  ├─► Würde 48h/Woche überschreiten? ──────► ❌ NEIN
  │   └─► Nein → Weiter
  │
  ├─► TD diese Woche? ──────────────────────► ❌ NEIN
  │   └─► Nein → Weiter
  │
  ├─► Besetzung in Grenzen? ────────────────► ❌ NEIN
  │   └─► Ja → Weiter
  │
  └─► ✅ JA - Zuweisung möglich!
```

---

## 📊 BEISPIEL: JANUAR 2026

### Schnellübersicht

**Kalender:** 31 Tage (22 Werktage, 9 Wochenendtage)
**Teams:** Alpha, Beta, Gamma (je 5 MA)
**Rotation:** F → N → S (wöchentlich)

**Rotationsplan:**

| Woche | Alpha | Beta | Gamma |
|-------|-------|------|-------|
| W1 (01-05.01) | 🌅 F | 🌙 N | 🌇 S |
| W2 (06-12.01) | 🌙 N | 🌇 S | 🌅 F |
| W3 (13-19.01) | 🌇 S | 🌅 F | 🌙 N |
| W4 (20-26.01) | 🌅 F | 🌙 N | 🌇 S |
| W5 (27-31.01) | 🌙 N | 🌇 S | 🌅 F |

**Abwesenheiten:**
- Anna Schmidt: Urlaub 13.-17.01. (5 Tage)
- Michael Schulz: Lehrgang 20.-22.01. (3 Tage)

**Durchschnittliche Ergebnisse:**
- Arbeitstage: ~25 Tage
- Arbeitsstunden: ~200h (Soll: ~213h)
- Wochenend-Einsätze: 3-4 mal
- Constraint-Erfüllung: 100% ✅

**→ [Vollständiges Beispiel siehe JANUAR_2026_BEISPIEL.md](JANUAR_2026_BEISPIEL.md)**

---

## ✅ VALIDIERUNG & QUALITÄT

### Constraint-Erfüllung

**Automatische Prüfung nach jeder Planung:**

```
HARTE CONSTRAINTS (Pflicht):
├─ ✅ Team-Rotation (F→N→S)
├─ ✅ Mindestbesetzung (4/3/3 bzw. 2/2/2)
├─ ✅ Maximalbesetzung (5/4/3 bzw. 3/3/3)
├─ ✅ Ruhezeit 11h (keine S→F, N→F, N→S)
├─ ✅ Max. 48h/Woche
├─ ✅ Abwesenheiten berücksichtigt
├─ ✅ TD 1x pro Woche
└─ ✅ Wöchentlich 1 MA frei

WEICHE CONSTRAINTS (Optimierung):
├─ ⭐⭐⭐⭐⭐ Wochenend-Fairness
├─ ⭐⭐⭐⭐⭐ Nachtschicht-Fairness
├─ ⭐⭐⭐⭐ Blockplanung
└─ ⭐⭐⭐⭐ TD-Fairness
```

### Typische Laufzeiten (Intel i7, 8 Cores)

| Szenario | Dauer | Status |
|----------|-------|--------|
| 15 MA, 1 Monat (31 Tage) | 30-60 Sek | ⚡ Schnell |
| 17 MA, 1 Monat | 45-90 Sek | ⚡ Schnell |
| 20 MA, 1 Monat | 1-2 Min | ✅ Normal |
| 30 MA, 1 Monat | 2-5 Min | ✅ Normal |
| 15 MA, 3 Monate | 3-6 Min | ✅ Normal |

---

## 🎓 HÄUFIGE FRAGEN (FAQ)

### F: Warum 3 Teams?

**A:** Das System ist für 3 Schichten (F/N/S) optimiert. Mit 3 Teams rotiert jedes Team durch alle Schichten:
- Woche 1: Team A=F, B=N, C=S
- Woche 2: Team A=N, B=S, C=F
- Woche 3: Team A=S, B=F, C=N
- Woche 4: Wiederholt sich

**Fairness:** Alle Teams arbeiten gleich oft jede Schicht.

### F: Warum 5 Mitarbeiter pro Team?

**A:** Mindestbesetzung Früh-Schicht = 4 Personen (werktags).
- Bei 4 MA: Kein Puffer bei Urlaub/Krankheit
- Bei 5 MA: 1 MA kann ausfallen, 4 bleiben verfügbar ✅
- Bei 6 MA: Mehr Flexibilität, aber evtl. zu viele Mitarbeiter

### F: Was passiert bei Personalausfall?

**A:** Mehrere Mechanismen:
1. **Innerhalb Team:** Andere Teammitglieder übernehmen
2. **Cross-Team:** Mitarbeiter aus anderen Teams springen ein
3. **Springer:** Reserve-Mitarbeiter (falls vorhanden)
4. **Überstunden:** Bis max. 48h/Woche möglich

### F: Kann ein Mitarbeiter Wünsche äußern?

**A:** Ja, über das Web-Interface:
- Urlaubsanträge (müssen genehmigt werden)
- Tauschbörse (Schichten mit Kollegen tauschen)
- Präferenzen (werden bei Optimierung berücksichtigt)

### F: Wie fair ist die Verteilung?

**A:** Sehr fair durch mehrere Mechanismen:
- **Rotation:** Alle Teams durchlaufen alle Schichten
- **Fairness-Constraints:** Ausgleich über das Jahr (YTD)
  - Wochenend-Arbeit: Max. ±1 Unterschied
  - Nachtschichten: Max. ±1 Unterschied
  - TD-Wochen: Gleichmäßig verteilt

### F: Was ist "Cross-Team"?

**A:** Ein Mitarbeiter arbeitet temporär mit einem anderen Team:
- **Grund:** Sein eigenes Team hat keine Schicht diese Woche, aber Bedarf besteht
- **Beispiel:** Team A hat Woche 1 Schicht N, aber es werden mehr Leute für Schicht F gebraucht
  → 1 Mitarbeiter aus Team A arbeitet cross-team in Schicht F
- **Regel:** Cross-Team Mo-Fr als kompletter Block

---

## 📖 GLOSSAR

| Begriff | Bedeutung |
|---------|-----------|
| **F (Früh)** | Frühschicht, 05:45-13:45 Uhr, 8 Stunden |
| **S (Spät)** | Spätschicht, 13:45-21:45 Uhr, 8 Stunden |
| **N (Nacht)** | Nachtschicht, 21:45-05:45 Uhr, 8 Stunden |
| **TD (Tagdienst)** | Organisatorische Funktion, 1x pro Woche (Mo-Fr) |
| **U** | Urlaub (Abwesenheitstyp) |
| **AU** | Arbeitsunfähigkeit / Krankheit (Abwesenheitstyp) |
| **L** | Lehrgang / Schulung (Abwesenheitstyp) |
| **Cross-Team** | Mitarbeiter arbeitet mit anderem Team |
| **Springer** | Reserve-Mitarbeiter ohne festes Team |
| **MA** | Mitarbeiter |
| **WE** | Wochenende (Samstag + Sonntag) |
| **YTD** | Year-to-Date (seit Jahresbeginn) |
| **CP-SAT** | Constraint Programming - Satisfiability (OR-Tools Solver) |
| **Harte Constraints** | Regeln die MÜSSEN erfüllt sein |
| **Weiche Constraints** | Optimierungsziele (best effort) |

---

## 🔗 WEITERFÜHRENDE DOKUMENTATION

### Detaillierte Dokumente

1. **[SCHICHTPLANUNG_REGELN.md](SCHICHTPLANUNG_REGELN.md)**
   - Alle Regeln im Detail
   - Formeln und Berechnungen
   - Constraint-Definitionen

2. **[SYSTEM_DIAGRAMME.md](SYSTEM_DIAGRAMME.md)**
   - Visuelle Darstellungen
   - Ablaufdiagramme
   - Architektur-Übersicht

3. **[JANUAR_2026_BEISPIEL.md](JANUAR_2026_BEISPIEL.md)**
   - Vollständiger Beispiel-Plan
   - Wochenweise Aufschlüsselung
   - Statistiken

4. **[SHIFT_PLANNING_ALGORITHM.md](SHIFT_PLANNING_ALGORITHM.md)**
   - Technische Details
   - OR-Tools Implementierung
   - Performance-Tuning

5. **[BENUTZERHANDBUCH.md](../BENUTZERHANDBUCH.md)**
   - Web-Interface Anleitung
   - Funktionen im Detail
   - Screenshots

---

## 📞 SUPPORT & KONTAKT

**GitHub Repository:** https://github.com/TimUx/Dienstplan
**Issues & Fragen:** https://github.com/TimUx/Dienstplan/issues
**Dokumentation:** https://github.com/TimUx/Dienstplan/tree/main/docs

---

## 📝 ÄNDERUNGSHISTORIE

| Version | Datum | Änderungen |
|---------|-------|------------|
| 2.1 | Jan 2026 | Vollständige Dokumentation erstellt |
| 2.0 | Dez 2025 | Python-Migration abgeschlossen |
| 1.x | 2024 | .NET-Version |

---

**Version 2.1 - Python Edition**

Entwickelt von **Timo Braun** mit ❤️ für effiziente Schichtverwaltung

Powered by **Google OR-Tools CP-SAT Solver**

© 2025 Fritz Winter Eisengießerei GmbH & Co. KG

---

**ENDE DER DOKUMENTATION**

Dieses Dokument bietet eine **vollständige und eindeutige Darstellung** des Schichtplanungssystems.
Alle Regeln, Abhängigkeiten, Mindestanforderungen und Beispiele sind detailliert dokumentiert.
