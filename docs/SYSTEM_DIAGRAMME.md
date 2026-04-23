# 📊 Schichtplanungs-System: Visuelle Diagramme

**Version 2.1 - Python Edition** | Grafische Darstellung aller Systemkomponenten

---

## 📑 Inhaltsverzeichnis

1. [System-Architektur](#1-system-architektur)
2. [Team-Rotationsdiagramm](#2-team-rotationsdiagramm)
3. [Constraint-Hierarchie](#3-constraint-hierarchie)
4. [Datenfluss](#4-datenfluss)
5. [Entscheidungsbaum](#5-entscheidungsbaum)
6. [Zeitlicher Ablauf](#6-zeitlicher-ablauf)

---

## 1. System-Architektur

### 1.1 Gesamtarchitektur

```
╔════════════════════════════════════════════════════════════════════╗
║                    DIENSTPLAN-SYSTEM ARCHITEKTUR                   ║
╚════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────┐
│                         WEB-INTERFACE                             │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌───────────┐ │
│  │ Dashboard  │  │Mitarbeiter │  │ Schichten  │  │Statistik  │ │
│  │            │  │ -verwaltung│  │ -planung   │  │           │ │
│  └────────────┘  └────────────┘  └────────────┘  └───────────┘ │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP REST API
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                       BACKEND (Python)                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Web API                       │   │
│  │  - Endpunkte (GET/POST/PUT/DELETE)                       │   │
│  │  - Authentifizierung & Autorisierung                     │   │
│  │  - Input Validierung                                      │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           ▼                                       │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              SCHICHTPLANUNGS-SOLVER                        │ │
│  │  ┌──────────┐  ┌────────────┐  ┌──────────────────────┐  │ │
│  │  │ Solver   │  │  Model     │  │    Constraints       │  │ │
│  │  │          │  │            │  │                      │  │ │
│  │  │OR-Tools  │→ │Variables   │→ │- Team-Rotation (H)  │  │ │
│  │  │CP-SAT    │  │Objective   │  │- Besetzung (H)      │  │ │
│  │  │          │  │            │  │- Ruhezeit (H)       │  │ │
│  │  │          │  │            │  │- Fairness (W)       │  │ │
│  │  └──────────┘  └────────────┘  └──────────────────────┘  │ │
│  └─────────────────────┬──────────────────────────────────────┘ │
│                        ▼                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │               VALIDATION & REPORTING                     │    │
│  │  - Constraint Checking                                   │    │
│  │  - Statistiken                                           │    │
│  │  - Export (PDF, Excel, CSV)                             │    │
│  └──────────────────────┬───────────────────────────────────┘   │
└─────────────────────────┼───────────────────────────────────────┘
                          ▼
┌──────────────────────────────────────────────────────────────────┐
│                      DATENBANK (SQLite)                           │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐ ┌──────────────┐   │
│  │Employees │ │  Teams   │ │ShiftTypes   │ │Assignments   │   │
│  │          │ │          │ │             │ │              │   │
│  │- Name    │ │- Name    │ │- Code (F/N/S│ │- Datum       │   │
│  │- Team_ID │ │- Members │ │- Zeiten     │ │- Employee_ID │   │
│  │- Qualif. │ │- Rotation│ │- Besetzung  │ │- Shift_Code  │   │
│  └──────────┘ └──────────┘ └─────────────┘ └──────────────┘   │
│                                                                   │
│  ┌──────────┐ ┌──────────┐ ┌─────────────┐                     │
│  │Absences  │ │ Settings │ │Statistics   │                     │
│  │- Type    │ │- Limits  │ │- Hours      │                     │
│  │- Period  │ │- Rules   │ │- Fairness   │                     │
│  └──────────┘ └──────────┘ └─────────────┘                     │
└──────────────────────────────────────────────────────────────────┘
```

### 1.2 Komponenten-Interaktion

```
┌─────────────┐
│   Benutzer  │
│  (Browser)  │
└──────┬──────┘
       │ 1. Anfrage
       ▼
┌──────────────────────┐
│   Web API            │
│   (web_api.py)       │
└──────┬───────────────┘
       │ 2. Daten laden
       ▼
┌──────────────────────┐
│   Data Loader        │◄──────────┐
│   (data_loader.py)   │           │
└──────┬───────────────┘           │
       │ 3. Entities              6. Speichern
       ▼                            │
┌──────────────────────┐           │
│   Solver             │           │
│   (solver.py)        │           │
└──────┬───────────────┘           │
       │ 4. Modell                 │
       ▼                            │
┌──────────────────────┐           │
│   Model Builder      │           │
│   (model.py)         │           │
└──────┬───────────────┘           │
       │ 5. Constraints            │
       ▼                            │
┌──────────────────────┐           │
│   Constraints        │           │
│   (constraints.py)   │           │
└──────┬───────────────┘           │
       │ 6. OR-Tools              │
       ▼                            │
┌──────────────────────┐           │
│   CP-SAT Solver      │           │
│   (Google OR-Tools)  │           │
└──────┬───────────────┘           │
       │ 7. Lösung                 │
       ▼                            │
┌──────────────────────┐           │
│   Validation         │           │
│   (validation.py)    │           │
└──────┬───────────────┘           │
       │ 8. Ergebnis               │
       ▼                            │
┌──────────────────────┐           │
│   Database           ├───────────┘
│   (dienstplan.db)    │
└──────┬───────────────┘
       │ 9. Rückgabe
       ▼
┌──────────────────────┐
│   Web API Response   │
└──────┬───────────────┘
       │
       ▼
┌─────────────┐
│   Benutzer  │
│  (Browser)  │
└─────────────┘
```

---

## 2. Team-Rotationsdiagramm

### 2.1 4-Wochen Rotationszyklus

```
╔═══════════════════════════════════════════════════════════════════╗
║              TEAM-ROTATION: F → N → S (4-Wochen-Zyklus)          ║
╚═══════════════════════════════════════════════════════════════════╝

         WOCHE 1           WOCHE 2           WOCHE 3           WOCHE 4
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │ Mo Di Mi Do Fr   │ Mo Di Mi Do Fr   │ Mo Di Mi Do Fr   │ Mo Di Mi Do Fr
    │ Sa So        │   │ Sa So        │   │ Sa So        │   │ Sa So        │
    └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ TEAM ALPHA                                                                │
├──────────────────────────────────────────────────────────────────────────┤
│   🌅 FRÜH (F)  →    🌙 NACHT (N)  →    🌇 SPÄT (S)  →    🌅 FRÜH (F)   │
│   05:45-13:45       21:45-05:45        13:45-21:45       05:45-13:45     │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ TEAM BETA                                                                 │
├──────────────────────────────────────────────────────────────────────────┤
│   🌙 NACHT (N)  →    🌇 SPÄT (S)  →    🌅 FRÜH (F)  →    🌙 NACHT (N)   │
│   21:45-05:45       13:45-21:45        05:45-13:45       21:45-05:45     │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│ TEAM GAMMA                                                                │
├──────────────────────────────────────────────────────────────────────────┤
│   🌇 SPÄT (S)  →    🌅 FRÜH (F)  →    🌙 NACHT (N)  →    🌇 SPÄT (S)    │
│   13:45-21:45       05:45-13:45        21:45-05:45       13:45-21:45     │
└──────────────────────────────────────────────────────────────────────────┘

                              ROTATION WIEDERHOLT SICH →
```

### 2.2 Tagesübersicht mit 3 Teams

```
╔═══════════════════════════════════════════════════════════════════╗
║                  TAGESABLAUF MIT 3 SCHICHTEN                      ║
╚═══════════════════════════════════════════════════════════════════╝

Zeit:  00:00   06:00   12:00   18:00   00:00   06:00
       │       │       │       │       │       │
       ├───────┼───────┼───────┼───────┼───────┤

🌙 NACHT (N)   ████████████████         21:45─────►05:45
Team Beta       ││││││││││││││
(3 Personen)    └─ 8 Stunden ─┘

                      🌅 FRÜH (F)   ████████████████
                      Team Alpha     05:45──►13:45
                      (4-5 Personen)  ││││││││
                                     └─ 8 Std ─┘

                              🌇 SPÄT (S)   ████████████████
                              Team Gamma     13:45──►21:45
                              (3-4 Personen)  ││││││││
                                             └─ 8 Std ─┘

ÜBERLAPPUNGEN:
  ├─ N endet ─┤  05:45  F beginnt
  ├─ F endet ─┤  13:45  S beginnt
  ├─ S endet ─┤  21:45  N beginnt

KEINE LÜCKEN: 24/7 Abdeckung durch 3 Schichten
```

### 2.3 Wochenstruktur (Beispiel)

```
╔═══════════════════════════════════════════════════════════════════╗
║              WOCHENSTRUKTUR (Team Alpha: Frühschicht)            ║
╚═══════════════════════════════════════════════════════════════════╝

Mitarbeiter: 5 Personen (Max, Anna, Peter, Lisa, Tom)

WERKTAGE (Mo-Fr):                      WOCHENENDE (Sa-So):
Mindestbesetzung: 4                    Mindestbesetzung: 2
Maximalbesetzung: 5                    Maximalbesetzung: 3

Mo    Di    Mi    Do    Fr    │    Sa    So
──────────────────────────────┼──────────────
■■■■  ■■■■  ■■■■  ■■■■  ■■■■  │    ■■    ■■
■     ■     ■     ■     ■     │    ■     □
(5)   (5)   (5)   (5)   (5)   │   (3)   (2)

Legende:
■ = Mitarbeiter arbeitet
□ = Mitarbeiter frei

Beispiel Samstag:
✓ Max arbeitet
✓ Peter arbeitet
✓ Tom arbeitet
  Anna frei (Urlaub/Rotation)
  Lisa frei (TD diese Woche)

Total Wochenstunden: (5×5 + 3×1)×8h = 44h < 48h ✅
```

---

## 3. Constraint-Hierarchie

### 3.1 Constraint-Pyramide

```
╔═══════════════════════════════════════════════════════════════════╗
║                    CONSTRAINT-HIERARCHIE                          ║
╚═══════════════════════════════════════════════════════════════════╝

                         ┌───────────────┐
                         │ OPTIMIERUNGS- │
                         │    ZIELE      │ ◄─── Weiche Constraints
                         │  (Fairness)   │      (werden optimiert)
                    ┌────┴───────────────┴────┐
                    │  ARBEITSSCHUTZ-REGELN   │
                    │  (Ruhezeit, Max-Stunden)│ ◄─── Harte Constraints
               ┌────┴─────────────────────────┴────┐  (MÜSSEN erfüllt sein)
               │    BETRIEBLICHE ANFORDERUNGEN     │
               │    (Mindestbesetzung, TD)         │
          ┌────┴───────────────────────────────────┴────┐
          │        PERSONELLE CONSTRAINTS               │
          │    (Max 1 Schicht/Tag, Abwesenheit)         │
     ┌────┴─────────────────────────────────────────────┴────┐
     │            FUNDAMENTALE CONSTRAINTS                    │
     │  (Team-Schicht-Zuweisung, Team-Rotation F→N→S)        │
     └────────────────────────────────────────────────────────┘

     EBENE 1: Muss IMMER erfüllt sein (Basis)
     EBENE 2: Personenzuordnung und Verfügbarkeit
     EBENE 3: Operative Anforderungen
     EBENE 4: Gesetzliche Vorgaben
     EBENE 5: Optimierung für beste Lösung
```

### 3.2 Constraint-Abhängigkeiten

```
┌──────────────────────────────────────────────────────────────────┐
│                   CONSTRAINT-ABHÄNGIGKEITEN                       │
└──────────────────────────────────────────────────────────────────┘

           ┌─────────────────────────┐
           │  TEAM-ROTATION (F→N→S)  │
           │   (Wöchentlich)         │
           └───────────┬─────────────┘
                       │ definiert
                       ▼
           ┌─────────────────────────┐
           │  TEAM-SCHICHT-ZUWEISUNG │
           │  (1 Schicht/Team/Woche) │
           └───────────┬─────────────┘
                       │ bestimmt
                       ▼
      ┌────────────────────────────────────┐
      │  MITARBEITER-AKTIVITÄT             │
      │  (abhängig von Team-Schicht)       │
      └────────┬───────────────────┬───────┘
               │                   │
         ┌─────▼─────┐       ┌────▼──────┐
         │ABWESENHEIT│       │ MAX 1     │
         │ blockiert │       │SCHICHT/TAG│
         │  Arbeit   │       │           │
         └─────┬─────┘       └────┬──────┘
               │                   │
               └────────┬──────────┘
                        │ zusammen bestimmen
                        ▼
               ┌──────────────────┐
               │  TAGES-BESETZUNG │
               │  (pro Schicht)   │
               └────────┬─────────┘
                        │ muss erfüllen
                        ▼
            ┌───────────────────────┐
            │ MINDEST-/MAXBESETZUNG │
            │  Werktag: 4-5 / 3-4   │
            │  WE: 2-3 / 2-3        │
            └───────────────────────┘
```

---

## 4. Datenfluss

### 4.1 Planungsprozess

```
╔═══════════════════════════════════════════════════════════════════╗
║                  SCHICHTPLANUNGS-DATENFLUSS                       ║
╚═══════════════════════════════════════════════════════════════════╝

START: Planungsanfrage (z.B. Januar 2026)
  │
  ▼
┌─────────────────────────────────────────┐
│ 1. DATEN SAMMELN                        │
│                                         │
│ ┌─────────────┐  ┌──────────────────┐ │
│ │ Mitarbeiter │  │ Teams            │ │
│ │ - 15 Pers.  │  │ - 3 Teams (5 MA) │ │
│ │ - Qualif.   │  │ - Rotation       │ │
│ └─────────────┘  └──────────────────┘ │
│                                         │
│ ┌─────────────┐  ┌──────────────────┐ │
│ │Schichttypen │  │ Abwesenheiten    │ │
│ │ - F/N/S     │  │ - Urlaub         │ │
│ │ - Zeiten    │  │ - Krankheit      │ │
│ │ - Besetzung │  │ - Lehrgang       │ │
│ └─────────────┘  └──────────────────┘ │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 2. MODELL ERSTELLEN                     │
│                                         │
│ ┌──────────────────────────────────┐  │
│ │ Entscheidungsvariablen:          │  │
│ │                                   │  │
│ │ team_shift[team][week][shift]    │  │
│ │   → Boolean (Team hat Schicht)   │  │
│ │                                   │  │
│ │ employee_active[emp][date]       │  │
│ │   → Boolean (MA arbeitet)        │  │
│ │                                   │  │
│ │ td_vars[emp][week]               │  │
│ │   → Boolean (MA hat TD)          │  │
│ └──────────────────────────────────┘  │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 3. CONSTRAINTS HINZUFÜGEN               │
│                                         │
│ ┌──────────────────────┐               │
│ │ HARTE CONSTRAINTS    │               │
│ │ - Team-Rotation      │               │
│ │ - Besetzung          │               │
│ │ - Ruhezeit           │               │
│ │ - Arbeitszeit        │               │
│ │ - Abwesenheit        │               │
│ └──────────────────────┘               │
│                                         │
│ ┌──────────────────────┐               │
│ │ WEICHE CONSTRAINTS   │               │
│ │ - Fairness (×10)     │               │
│ │ - Blöcke (×3)        │               │
│ │ - TD-Fairness (×4)   │               │
│ └──────────────────────┘               │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 4. SOLVER AUSFÜHREN                     │
│                                         │
│   Google OR-Tools CP-SAT                │
│   ┌──────────────────────────┐         │
│   │ Zeitlimit: 300 Sekunden  │         │
│   │ Parallele Worker: 8      │         │
│   │ Suche: Branch & Bound    │         │
│   └──────────────────────────┘         │
│                                         │
│   Status: OPTIMAL / FEASIBLE            │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 5. LÖSUNG EXTRAHIEREN                   │
│                                         │
│ ┌──────────────────────────────────┐  │
│ │ Für jeden Mitarbeiter, jeden Tag:│  │
│ │                                   │  │
│ │ if x[emp][date][shift] == 1:     │  │
│ │   → Mitarbeiter hat Schicht      │  │
│ │                                   │  │
│ │ if td[emp][week] == 1:           │  │
│ │   → Mitarbeiter hat TD           │  │
│ └──────────────────────────────────┘  │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 6. VALIDIERUNG                          │
│                                         │
│ ✓ Alle harten Constraints erfüllt?     │
│ ✓ Besetzung in Grenzen?                │
│ ✓ Keine Ruhezeit-Verletzungen?         │
│ ✓ Stundensoll erreicht?                │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ 7. ERGEBNIS SPEICHERN                   │
│                                         │
│ ┌──────────────────────────────────┐  │
│ │ ShiftAssignments Tabelle:        │  │
│ │ - EmployeeId, Date, ShiftCode    │  │
│ │                                   │  │
│ │ Statistiken:                     │  │
│ │ - Arbeitsstunden pro MA          │  │
│ │ - Wochenend-Count                │  │
│ │ - Nachtschicht-Count             │  │
│ └──────────────────────────────────┘  │
└───────────────┬─────────────────────────┘
                │
                ▼
               END: Schichtplan erstellt ✅
```

### 4.2 Echtzeit-Anpassungen

```
┌────────────────────────────────────────────────────────────┐
│          DYNAMISCHE PLAN-ANPASSUNG                         │
└────────────────────────────────────────────────────────────┘

  Bestehender Plan
        │
        ├─► Änderung erkannt (z.B. Krankheitsausfall)
        │
        ▼
  ┌──────────────────┐
  │ Betroffene Tage  │
  │ identifizieren   │
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────────────┐
  │ Optionen prüfen:         │
  │                          │
  │ 1. Cross-Team Einsatz    │──► Andere Teams verfügbar?
  │ 2. Springer einsetzen    │──► Reserve vorhanden?
  │ 3. Überstunden           │──► < 48h/Woche?
  │ 4. Besetzung reduzieren  │──► > Mindestbesetzung?
  └────────┬─────────────────┘
           │
           ▼
  ┌──────────────────┐
  │ Beste Lösung     │
  │ umsetzen         │
  └────────┬─────────┘
           │
           ▼
  Aktualisierter Plan
```

---

## 5. Entscheidungsbaum

### 5.1 Schichtzuweisung

```
╔═══════════════════════════════════════════════════════════════════╗
║              ENTSCHEIDUNGSBAUM: SCHICHTZUWEISUNG                  ║
╚═══════════════════════════════════════════════════════════════════╝

START: Kann Mitarbeiter X an Tag Y Schicht Z arbeiten?
  │
  ├─► Ist Mitarbeiter abwesend (U/AU/L)?
  │   ├─ JA → ❌ NEIN, keine Zuweisung möglich
  │   └─ NEIN → Weiter
  │
  ├─► Gehört Tag Y zur Schicht des Teams in dieser Woche?
  │   ├─ NEIN → Prüfe Cross-Team Möglichkeit
  │   │         ├─► Ist Cross-Team erlaubt?
  │   │         │   ├─ JA → Prüfe weitere Bedingungen
  │   │         │   └─ NEIN → ❌ NEIN
  │   │         │
  │   │         └─► Cross-Team Block-Regel:
  │   │             Wenn Mo-Fr: Alle Werktage oder keine
  │   │             ├─ Erfüllt → Weiter
  │   │             └─ Nicht erfüllt → ❌ NEIN
  │   │
  │   └─ JA → Weiter
  │
  ├─► Hat Mitarbeiter bereits eine Schicht an Tag Y?
  │   ├─ JA → ❌ NEIN (Max 1 Schicht/Tag)
  │   └─ NEIN → Weiter
  │
  ├─► Verletzt Zuweisung Ruhezeit-Regel (11h)?
  │   │
  │   ├─► Schicht am Vortag (Y-1)?
  │   │   ├─ S (Spät) → Ziel F? → ❌ NEIN (nur 8h Ruhe)
  │   │   ├─ N (Nacht) → Ziel F? → ❌ NEIN (0h Ruhe)
  │   │   ├─ N (Nacht) → Ziel S? → ❌ NEIN (8h Ruhe)
  │   │   └─ Sonst → ✅ OK
  │   │
  │   └─ Keine Schicht am Vortag → ✅ OK, Weiter
  │
  ├─► Würde Zuweisung 48h/Woche überschreiten?
  │   ├─ JA → ❌ NEIN (Max 48h/Woche)
  │   └─ NEIN → Weiter
  │
  ├─► Hat Mitarbeiter TD in dieser Woche?
  │   ├─ JA → ❌ NEIN (TD blockiert Schichten)
  │   └─ NEIN → Weiter
  │
  ├─► Würde Besetzung in Grenzen bleiben?
  │   │
  │   ├─► Werktag?
  │   │   ├─ F: 4-5 → In Grenzen? → Weiter / ❌ NEIN
  │   │   ├─ S: 3-4 → In Grenzen? → Weiter / ❌ NEIN
  │   │   └─ N: 3-3 → In Grenzen? → Weiter / ❌ NEIN
  │   │
  │   └─► Wochenende?
  │       └─ Alle: 2-3 → In Grenzen? → Weiter / ❌ NEIN
  │
  └─► Alle Prüfungen bestanden
      └─► ✅ JA, Zuweisung ist möglich!
```

### 5.2 TD-Zuweisung

```
START: Kann Mitarbeiter X TD in Woche Y übernehmen?
  │
  ├─► Ist Mitarbeiter TD-qualifiziert?
  │   ├─ NEIN → ❌ NEIN, nicht qualifiziert
  │   └─ JA → Weiter
  │
  ├─► Ist Mitarbeiter in Woche Y abwesend?
  │   ├─ JA → ❌ NEIN, nicht verfügbar
  │   └─ NEIN → Weiter
  │
  ├─► Hat Mitarbeiter bereits reguläre Schichten in Woche Y?
  │   ├─ JA → Muss Schichten blockieren
  │   └─ NEIN → OK
  │
  ├─► Ist TD-Fairness gewährleistet?
  │   (Vergleich mit anderen TD-qualifizierten)
  │   ├─ Hat X signifikant weniger TD als andere? → Bevorzugen
  │   └─ Hat X signifikant mehr TD? → Benachteiligen
  │
  └─► ✅ JA, TD-Zuweisung ist möglich!
```

---

## 6. Zeitlicher Ablauf

### 6.1 Monatsplanung Timeline

```
╔═══════════════════════════════════════════════════════════════════╗
║           ZEITLICHER ABLAUF: MONATSPLANUNG (Januar 2026)          ║
╚═══════════════════════════════════════════════════════════════════╝

TAG -30                    TAG -7            TAG 0          TAG +31
 │                          │                 │               │
 │ Vorplanung               │ Finale          │ Plan-         │ Plan-
 │ beginnen                 │ Anpassungen     │ ausführung    │ abschluss
 │                          │                 │ startet       │
 ▼                          ▼                 ▼               ▼
 ├──────────────────────────┼─────────────────┼───────────────┤
 │                          │                 │               │
 │ ┌──────────────────┐    │ ┌────────────┐ │ ┌──────────┐ │
 │ │ Daten sammeln:   │    │ │ Urlaubs-   │ │ │ Tägliche │ │
 │ │ - Mitarbeiter    │    │ │ anträge    │ │ │ Anpassung│ │
 │ │ - Abwesenheiten  │    │ │ genehmigen │ │ │ bei Bedarf│ │
 │ │ - Präferenzen    │    │ │            │ │ │          │ │
 │ └──────────────────┘    │ └────────────┘ │ └──────────┘ │
 │                          │                 │               │
 │ ┌──────────────────┐    │ ┌────────────┐ │ ┌──────────┐ │
 │ │ Grob-Planung:    │    │ │ Solver     │ │ │ Statistik│ │
 │ │ - Team-Rotation  │    │ │ ausführen  │ │ │ sammeln  │ │
 │ │ - Besetzungs-    │    │ │ (finale    │ │ │          │ │
 │ │   anforderungen  │    │ │ Version)   │ │ │          │ │
 │ └──────────────────┘    │ └────────────┘ │ └──────────┘ │
 │                          │                 │               │
 │ ┌──────────────────┐    │ ┌────────────┐ │               │
 │ │ Test-Durchlauf:  │    │ │ Plan       │ │               │
 │ │ - Constraints    │    │ │ veröffent- │ │               │
 │ │   prüfen         │    │ │ lichen     │ │               │
 │ │ - Machbarkeit    │    │ └────────────┘ │               │
 │ └──────────────────┘    │                 │               │
 │                          │                 │               │
```

### 6.2 Tagesablauf (Beispiel Montag)

```
╔═══════════════════════════════════════════════════════════════════╗
║              TAGESABLAUF: MONTAG, 06. JANUAR 2026                 ║
╚═══════════════════════════════════════════════════════════════════╝

00:00                     12:00                     23:59
  │                         │                         │
  ├─────────────────────────┼─────────────────────────┤

  │ 🌙 NACHT (N)
  │ 21:45 (Vortag) ──────► 05:45
  │ ┌─────────────────────────┐
  │ │ Team Alpha              │
  │ │ Max, Anna, Peter        │
  │ │ (3 Personen)            │
  │ └─────────────────────────┘
  │                       │
  │                       │ Schichtübergabe
  │                       ▼
  │                 🌅 FRÜH (F)
  │                 05:45 ──────────────────► 13:45
  │                 ┌────────────────────────────────┐
  │                 │ Team Gamma                     │
  │                 │ Markus, Stefanie, Andreas,    │
  │                 │ Nicole, Christian              │
  │                 │ (5 Personen)                   │
  │                 └────────────────────────────────┘
  │                                           │
  │                                           │ Schichtübergabe
  │                                           ▼
  │                                     🌇 SPÄT (S)
  │                                     13:45 ─────────────► 21:45
  │                                     ┌─────────────────────────┐
  │                                     │ Team Beta               │
  │                                     │ Julia, Michael, Sarah,  │
  │                                     │ Daniel                  │
  │                                     │ (4 Personen)            │
  │                                     └─────────────────────────┘
  │                                                           │
  └───────────────────────────────────────────────────────────┤
                                                              │
                                          Schichtübergabe zu Nacht
                                          (Dienstag 21:45) ──►

TD (Tagdienst): Lisa Meyer arbeitet als TD (nicht in Schichten)
                Mo-Fr im Tagdienst-Modus

GESAMT: 3 + 5 + 4 = 12 Personen in Schichten
        + 1 Person TD = 13 Personen aktiv
        Verfügbar: 2 Personen (Reserve/Frei)
```

---

## 7. Zusammenfassung

### 7.1 Wichtigste Diagramm-Erkenntnisse

```
┌────────────────────────────────────────────────────────────────┐
│                   SYSTEM-ÜBERSICHT KOMPAKT                      │
└────────────────────────────────────────────────────────────────┘

1. STRUKTUR
   ├─ 3 Teams mit je 5 Mitarbeitern = 15 MA
   ├─ 3 Schichten: F (Früh), N (Nacht), S (Spät)
   └─ Wöchentliche Rotation: F → N → S

2. ABLAUF
   ├─ Daten sammeln → Modell erstellen → Constraints hinzufügen
   ├─ Solver ausführen (OR-Tools CP-SAT)
   └─ Validieren → Speichern → Veröffentlichen

3. CONSTRAINTS
   ├─ Ebene 1: Team-Rotation (Fundamental)
   ├─ Ebene 2: Personenzuordnung (1 Schicht/Tag)
   ├─ Ebene 3: Besetzung (4/3/3 werktags, 2/2/2 WE)
   ├─ Ebene 4: Arbeitsschutz (Ruhezeit 11h, Max 48h/Woche)
   └─ Ebene 5: Fairness (Wochenenden, Nächte, TD)

4. ENTSCHEIDUNGEN
   ├─ Prüfe Abwesenheit
   ├─ Prüfe Team-Schicht-Match oder Cross-Team
   ├─ Prüfe Ruhezeit (keine S→F, N→F, N→S)
   ├─ Prüfe Wochenstunden (≤48h)
   └─ Prüfe Besetzungsgrenzen

5. TIMELINE
   ├─ -30 Tage: Vorplanung beginnen
   ├─ -7 Tage: Finale Anpassungen
   ├─ Tag 0: Plan startet
   └─ Tag +31: Plan abschließen, Statistiken sammeln
```

---

**Version 2.1 - Python Edition**

Entwickelt von **Timo Braun** mit ❤️

Powered by **Google OR-Tools CP-SAT Solver**

© 2025 Fritz Winter Eisengießerei GmbH & Co. KG
