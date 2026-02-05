# Schichtrotation Implementierung - Analyse

**Datum**: 2026-02-05  
**Status**: ✅ ABGESCHLOSSEN  
**Sprache**: Deutsch / German

## Zusammenfassung

Die Schichtrotation (F → N → S) ist **HARDCODED** im Code und verwendet **NICHT** die Datenbank-Einstellungen über die `RotationGroups` und `RotationGroupShifts` Tabellen.

## Problemstellung

**Frage**: Ist die Schichtrotation hardcoded oder wird die Einstellung in der Datenbank über die Rotationsgruppen verwendet?

**Antwort**: Die Rotation ist **hardcoded**. Die Datenbanktabellen existieren zwar, werden aber vom Solver nicht verwendet.

---

## Detaillierte Analyse

### 1. Hardcoded Rotationsmuster

**Ort**: `constraints.py`, Zeile 47

```python
# Fixed rotation pattern: F → N → S
ROTATION_PATTERN = ["F", "N", "S"]
```

Diese Konstante wird in zwei Constraint-Funktionen verwendet:

#### a) Team-Rotation (HARD Constraint)

**Funktion**: `add_team_rotation_constraints()` (Zeilen 110-197)

```python
def add_team_rotation_constraints(
    model: cp_model.CpModel,
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    teams: List[Team],
    weeks: List[List[date]],
    shift_codes: List[str],
    ...
):
    """
    HARD CONSTRAINT: Teams follow fixed rotation pattern F → N → S.
    
    Each team follows the same rotation cycle with offset based on team ID.
    Week 0: Team 1=F, Team 2=N, Team 3=S
    Week 1: Team 1=N, Team 2=S, Team 3=F
    Week 2: Team 1=S, Team 2=F, Team 3=N
    Week 3: Team 1=F, Team 2=N, Team 3=S (repeats)
    """
    rotation = ["F", "N", "S"]  # HARDCODED!
    
    for team_idx, team in enumerate(sorted_teams):
        for week_idx in range(len(weeks)):
            # Calculate rotation based on ISO week number
            iso_year, iso_week, iso_weekday = monday_of_week.isocalendar()
            rotation_idx = (iso_week + team_idx) % len(rotation)
            assigned_shift = rotation[rotation_idx]
            
            # Force this team to have this specific shift
            model.Add(team_shift[(team.id, week_idx, assigned_shift)] == 1)
```

**Eigenschaften**:
- HARD Constraint (muss erfüllt werden)
- Basiert auf ISO-Wochennummern für Konsistenz über Monatsgrenzen hinweg
- Team-basiertes Offset für verschiedene Startpunkte
- Keine Verbindung zur Datenbank

#### b) Mitarbeiter Rotationsreihenfolge (SOFT Constraint)

**Funktion**: `add_employee_weekly_rotation_order_constraints()` (Zeilen 199-407)

```python
def add_employee_weekly_rotation_order_constraints(
    model: cp_model.CpModel,
    ...
):
    """
    SOFT CONSTRAINT: Enforce F → N → S rotation order for employees across weeks.
    
    Valid transitions:
    - F → N (next in sequence)
    - N → S (next in sequence)
    - S → F (wrap around)
    - Any shift can repeat (F → F, N → N, S → S)
    
    Invalid transitions (should be penalized):
    - F → S (skips N)
    - N → F (skips S)
    - S → N (skips F)
    """
    ROTATION_ORDER_VIOLATION_PENALTY = 10000
    
    # Define valid transitions in the F → N → S order
    VALID_NEXT_SHIFTS = {
        "F": ["F", "N"],  # HARDCODED!
        "N": ["N", "S"],  # HARDCODED!
        "S": ["S", "F"],  # HARDCODED!
    }
    
    # Check transitions and penalize violations...
```

**Eigenschaften**:
- SOFT Constraint (kann verletzt werden, aber mit hoher Strafe)
- Penalty: 10.000 Punkte pro Verletzung
- Erlaubt Wiederholungen (F→F, N→N, S→S)
- Verhindert ungültige Übergänge (F→S, N→F, S→N)
- Keine Verbindung zur Datenbank

### 2. Datenbank RotationGroups - Nicht verwendet!

**Schema**: `db_init.py`, Zeilen 286-313

```python
# RotationGroups table (defines shift rotation groups with rotation rules)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS RotationGroups (
        Id INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT NOT NULL,
        Description TEXT,
        IsActive INTEGER NOT NULL DEFAULT 1,
        CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CreatedBy TEXT,
        ModifiedAt TEXT,
        ModifiedBy TEXT
    )
""")

# RotationGroupShifts table (many-to-many: which shifts belong to which rotation group)
cursor.execute("""
    CREATE TABLE IF NOT EXISTS RotationGroupShifts (
        Id INTEGER PRIMARY KEY AUTOINCREMENT,
        RotationGroupId INTEGER NOT NULL,
        ShiftTypeId INTEGER NOT NULL,
        RotationOrder INTEGER NOT NULL,  # <<<< Wichtig! Reihenfolge könnte hier gespeichert werden
        CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CreatedBy TEXT,
        FOREIGN KEY (RotationGroupId) REFERENCES RotationGroups(Id) ON DELETE CASCADE,
        FOREIGN KEY (ShiftTypeId) REFERENCES ShiftTypes(Id) ON DELETE CASCADE,
        UNIQUE(RotationGroupId, ShiftTypeId)
    )
""")
```

**Kommentar im Code** (db_init.py, Zeilen 268-271):
```python
# DEPRECATED: Use RotationGroups instead for new implementations.
# Migration strategy: This table will be maintained for backward compatibility.
# New features should use RotationGroups. A future migration script will convert
# existing ShiftTypeRelationships to RotationGroups when all features are migrated.
```

**Status**: Tabellen existieren, aber:
- ❌ Nicht im Solver verwendet
- ❌ Nicht in Constraints geladen
- ❌ Keine Verbindung zu `ROTATION_PATTERN`
- ✅ Nur über REST API verfügbar
- ✅ Nur im Web-UI verwaltbar

### 3. REST API Endpoints (nur Administration)

**Datei**: `web_api.py`, Zeilen 2367-2599

```python
@app.route('/api/rotationgroups', methods=['GET'])
@require_role(['Admin', 'Disponent'])
def get_rotation_groups():
    """Get all rotation groups"""
    # Lädt aus Datenbank, aber wird nicht vom Solver verwendet

@app.route('/api/rotationgroups', methods=['POST'])
@require_role('Admin')
def create_rotation_group():
    """Create a new rotation group"""
    # Admin kann Rotationsgruppen erstellen

@app.route('/api/rotationgroups/<int:id>', methods=['GET'])
@require_role(['Admin', 'Disponent'])
def get_rotation_group(id):
    """Get single rotation group by ID"""
    
@app.route('/api/rotationgroups/<int:id>', methods=['PUT'])
@require_role('Admin')
def update_rotation_group(id):
    """Update a rotation group"""
    
@app.route('/api/rotationgroups/<int:id>', methods=['DELETE'])
@require_role('Admin')
def delete_rotation_group(id):
    """Delete a rotation group"""
```

**Zweck**: Nur für zukünftige Verwendung und administrative Verwaltung.

### 4. Web-UI Integration

**Datei**: `wwwroot/index.html`, Zeilen 1208-1234

```html
<!-- Rotation Groups Modal -->
<div id="rotationGroupModal" class="modal">
    <div class="modal-content">
        <span class="close" onclick="closeRotationGroupModal()">&times;</span>
        <h2>Rotationsgruppe</h2>
        <form id="rotationGroupForm" onsubmit="saveRotationGroup(event)">
            <!-- Form fields for managing rotation groups -->
        </form>
    </div>
</div>
```

**JavaScript**: `wwwroot/js/app.js`, Zeilen 5672-6034

```javascript
async function loadRotationGroups() {
    // Lädt Rotationsgruppen für Anzeige
}

function displayRotationGroups(groups) {
    // Zeigt Rotationsgruppen im Admin-Bereich
}

async function saveRotationGroup(event) {
    // Speichert Rotationsgruppe in Datenbank
}
```

**Zweck**: UI für Administration, aber keine Auswirkung auf Solver.

---

## Architektur-Übersicht

```
┌──────────────────────────────────────────────────────────────┐
│                      WEB-UI / API                             │
│  (Admin kann RotationGroups verwalten)                       │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    DATENBANK                                  │
│                                                               │
│  ┌────────────────────────────────────────┐                 │
│  │ RotationGroups                         │                 │
│  │  - Id, Name, Description               │                 │
│  │  - IsActive                            │                 │
│  └────────────────────────────────────────┘                 │
│                    │                                         │
│                    ▼                                         │
│  ┌────────────────────────────────────────┐                 │
│  │ RotationGroupShifts                    │                 │
│  │  - RotationGroupId                     │                 │
│  │  - ShiftTypeId                         │                 │
│  │  - RotationOrder ◄── KÖNNTE verwendet werden            │
│  └────────────────────────────────────────┘                 │
└──────────────────────────────────────────────────────────────┘
                            │
                            │ ❌ KEINE VERBINDUNG!
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    SOLVER / CONSTRAINTS                       │
│                                                               │
│  constraints.py:                                             │
│  ┌────────────────────────────────────────┐                 │
│  │ ROTATION_PATTERN = ["F", "N", "S"]     │ ◄── HARDCODED!  │
│  │                                        │                 │
│  │ add_team_rotation_constraints()        │                 │
│  │   → Verwendet ROTATION_PATTERN         │                 │
│  │                                        │                 │
│  │ add_employee_weekly_rotation_order..() │                 │
│  │   → VALID_NEXT_SHIFTS hardcoded        │                 │
│  └────────────────────────────────────────┘                 │
└──────────────────────────────────────────────────────────────┘
```

---

## Warum ist das so?

### Historischer Kontext

1. **Ursprüngliche Implementierung**: Das System wurde mit fester F→N→S Rotation entwickelt
2. **Spätere Erweiterung**: RotationGroups-Tabellen wurden als "zukünftige Funktion" hinzugefügt
3. **Migration ausstehend**: Kommentare im Code zeigen, dass eine Migration geplant aber nicht umgesetzt ist

### Code-Kommentar (db_init.py, Zeile 268-271):

```python
# DEPRECATED: Use RotationGroups instead for new implementations.
# Migration strategy: This table will be maintained for backward compatibility.
# New features should use RotationGroups. A future migration script will convert
# existing ShiftTypeRelationships to RotationGroups when all features are migrated.
```

**Interpretation**: 
- Die Entwickler **wollten** auf RotationGroups umstellen
- Die Migration wurde **noch nicht** implementiert
- Der aktuelle Code verwendet weiterhin hardcoded Rotation

---

## Vorteile und Nachteile

### Aktuelle Implementierung (Hardcoded)

#### ✅ Vorteile:
- Einfach und direkt
- Keine Abhängigkeit von Datenbank-Konfiguration
- Konsistentes Verhalten garantiert
- Schneller (keine DB-Abfragen)
- Gut getestet (siehe `test_rotation_order.py`, `ROTATION_ORDER_FIX.md`)

#### ❌ Nachteile:
- Nicht flexibel - Änderungen erfordern Code-Änderungen
- Kann nicht per UI konfiguriert werden
- Andere Rotationsmuster (z.B. F→S→N) nicht möglich
- Datenbank-Tabellen existieren, werden aber nicht genutzt
- Verwirrend für Administratoren (UI zeigt Rotationsgruppen, aber sie haben keine Wirkung)

### Datenbank-basierte Implementierung (Potenzial)

#### ✅ Potenzielle Vorteile:
- Flexible Konfiguration per UI
- Verschiedene Rotationsmuster möglich
- Teams können unterschiedliche Rotationen haben
- Keine Code-Änderungen bei Rotationsänderungen
- Administratoren haben volle Kontrolle

#### ❌ Potenzielle Herausforderungen:
- Komplexere Implementierung
- Migration notwendig
- Validierung erforderlich (ungültige Konfigurationen verhindern)
- Tests müssen angepasst werden
- Backward Compatibility sicherstellen

---

## Empfehlungen

### Option A: Aktuellen Zustand beibehalten ✅ EINFACH

**Wann sinnvoll**: 
- F→N→S Rotation ist ausreichend
- Keine Änderungen geplant
- Einfachheit wird bevorzugt

**Maßnahmen**:
1. ✅ Dokumentation erstellen (dieses Dokument)
2. UI-Warnung hinzufügen: "Rotationsgruppen sind aktuell nur für zukünftige Verwendung"
3. RotationGroups-Verwaltung aus UI entfernen oder als "Beta-Feature" markieren

### Option B: Migration zur Datenbank-basierten Rotation ⚠️ KOMPLEX

**Wann sinnvoll**:
- Flexible Rotationsmuster gewünscht
- Teams benötigen verschiedene Rotationen
- Konfigurierbarkeit wichtig

**Implementierungsschritte**:
1. **Data Loader erweitern** (`data_loader.py`):
   ```python
   def load_rotation_groups(db_path: str) -> Dict[int, List[str]]:
       """Load rotation patterns from RotationGroups tables"""
       # Query RotationGroups and RotationGroupShifts
       # Return mapping: rotation_group_id -> [shift_codes in order]
   ```

2. **Teams mit RotationGroups verknüpfen**:
   - Neue Spalte in Teams-Tabelle: `RotationGroupId`
   - Migration für bestehende Daten

3. **Constraints anpassen** (`constraints.py`):
   ```python
   def add_team_rotation_constraints(
       ...,
       rotation_patterns: Dict[int, List[str]] = None  # Neu!
   ):
       # Wenn rotation_patterns gegeben, verwende diese
       # Sonst Fallback auf ROTATION_PATTERN
       rotation = rotation_patterns.get(team.rotation_group_id, ["F", "N", "S"])
   ```

4. **Solver anpassen** (`solver.py`):
   ```python
   # In __init__ oder add_all_constraints:
   rotation_patterns = data_loader.load_rotation_groups(db_path)
   add_team_rotation_constraints(..., rotation_patterns=rotation_patterns)
   ```

5. **Validierung implementieren**:
   - Sicherstellen, dass RotationOrder lückenlos ist (1, 2, 3, ...)
   - Mindestens 2 Schichten pro Gruppe
   - Alle Schichten in Gruppe existieren

6. **Tests erweitern**:
   - Testen mit verschiedenen Rotationsmustern
   - Backward Compatibility testen
   - Edge Cases (leere Gruppe, einzelne Schicht, etc.)

7. **Migration Script**:
   ```python
   # migrate_to_rotation_groups.py
   def migrate():
       # Create default RotationGroup "Standard F→N→S"
       # Link all teams to this group
       # Verify solver still works
   ```

**Geschätzter Aufwand**: 2-3 Entwicklungstage + Testing

### Option C: Hybride Lösung ⚙️ MITTEL

**Konzept**: Datenbank als optionale Erweiterung

**Implementierung**:
- Fallback auf hardcoded Pattern, wenn keine DB-Konfiguration
- Erlaubt schrittweise Migration
- Minimale Breaking Changes

```python
def get_rotation_pattern(team: Team, db_patterns: Dict) -> List[str]:
    """Get rotation pattern for team - DB or hardcoded fallback"""
    if team.rotation_group_id and team.rotation_group_id in db_patterns:
        return db_patterns[team.rotation_group_id]
    return ["F", "N", "S"]  # Fallback
```

---

## Fazit

**Aktuelle Situation**:
- ✅ Schichtrotation ist **HARDCODED**
- ✅ F → N → S Pattern ist fest im Code definiert
- ❌ RotationGroups-Tabellen existieren, werden aber **NICHT verwendet**
- ⚠️ UI erlaubt Verwaltung von Rotationsgruppen, aber **ohne Effekt auf Planung**

**Nächste Schritte**:
1. ✅ Diese Dokumentation mit Team teilen
2. ⚠️ Entscheidung treffen: Option A, B oder C?
3. ⚠️ Wenn Option A: UI-Warnung hinzufügen oder Feature entfernen
4. ⚠️ Wenn Option B/C: Migration planen und umsetzen

**Empfehlung**: 
- Für sofortige Nutzung: **Option A** (Status Quo beibehalten)
- Für zukünftige Flexibilität: **Option C** (Hybride Lösung)
- Nur bei starkem Bedarf: **Option B** (Vollständige Migration)

---

## Dateien betroffen

### Code-Dateien:
- ✅ `constraints.py` - Rotationslogik (hardcoded)
- ✅ `solver.py` - Constraint-Integration
- ✅ `entities.py` - Datenmodelle (RotationGroup, RotationGroupShift)
- ✅ `db_init.py` - Datenbank-Schema
- ✅ `web_api.py` - REST API für RotationGroups (nicht im Solver verwendet)
- ⚠️ `data_loader.py` - Lädt KEINE RotationGroups

### Test-Dateien:
- ✅ `test_rotation_order.py` - Testet hardcoded Rotation

### Dokumentation:
- ✅ `ROTATION_ORDER_FIX.md` - Beschreibt aktuelle Implementierung
- ✅ `ROTATION_IMPLEMENTATION_ANALYSIS.md` - Dieses Dokument

### Frontend:
- ⚠️ `wwwroot/index.html` - UI für RotationGroups (keine Wirkung auf Solver)
- ⚠️ `wwwroot/js/app.js` - JavaScript für RotationGroups-Verwaltung

---

## Anhang: Beispiel-Code für Migration (Option B)

Falls eine Migration gewünscht wird, hier ein Beispiel:

```python
# data_loader.py - Neue Funktion
def load_rotation_groups_from_db(db_path: str) -> Dict[int, List[str]]:
    """
    Load rotation patterns from RotationGroups and RotationGroupShifts tables.
    
    Returns:
        Dict mapping rotation_group_id to list of shift codes in rotation order.
        Example: {1: ["F", "N", "S"], 2: ["F", "S"], 3: ["N", "S", "F"]}
    """
    import sqlite3
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    rotation_patterns = {}
    
    # Get all active rotation groups
    cursor.execute("""
        SELECT Id FROM RotationGroups WHERE IsActive = 1
    """)
    
    for (group_id,) in cursor.fetchall():
        # Get shifts in rotation order
        cursor.execute("""
            SELECT st.Code
            FROM RotationGroupShifts rgs
            JOIN ShiftTypes st ON st.Id = rgs.ShiftTypeId
            WHERE rgs.RotationGroupId = ?
            ORDER BY rgs.RotationOrder ASC
        """, (group_id,))
        
        shifts = [row[0] for row in cursor.fetchall()]
        if shifts:  # Only add if group has shifts
            rotation_patterns[group_id] = shifts
    
    conn.close()
    return rotation_patterns


# constraints.py - Modifizierte Funktion
def add_team_rotation_constraints(
    model: cp_model.CpModel,
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    teams: List[Team],
    weeks: List[List[date]],
    shift_codes: List[str],
    locked_team_shift: Dict[Tuple[int, int], str] = None,
    shift_types: List[ShiftType] = None,
    rotation_patterns: Dict[int, List[str]] = None  # NEU: Optional DB patterns
):
    """
    HARD CONSTRAINT: Teams follow rotation pattern.
    
    If rotation_patterns is provided, uses team-specific patterns from database.
    Otherwise falls back to hardcoded F → N → S pattern.
    """
    # Default fallback pattern
    DEFAULT_ROTATION = ["F", "N", "S"]
    
    for team_idx, team in enumerate(sorted_teams):
        # Get rotation pattern for this team
        if rotation_patterns and hasattr(team, 'rotation_group_id') and team.rotation_group_id:
            rotation = rotation_patterns.get(team.rotation_group_id, DEFAULT_ROTATION)
        else:
            rotation = DEFAULT_ROTATION
        
        # Rest of logic unchanged...
        for week_idx in range(len(weeks)):
            rotation_idx = (iso_week + team_idx) % len(rotation)
            assigned_shift = rotation[rotation_idx]
            # ...


# solver.py - Modified __init__ or add_all_constraints
def add_all_constraints(self):
    """Add all constraints with optional DB-based rotation patterns"""
    
    # Try to load rotation patterns from database
    rotation_patterns = None
    try:
        from data_loader import load_rotation_groups_from_db
        rotation_patterns = load_rotation_groups_from_db("dienstplan.db")
        print(f"  Loaded {len(rotation_patterns)} rotation patterns from database")
    except Exception as e:
        print(f"  Using hardcoded rotation pattern (DB load failed: {e})")
    
    # Team rotation (F → N → S or DB patterns)
    add_team_rotation_constraints(
        self.planning_model.model,
        self.planning_model.team_shift,
        self.planning_model.teams,
        self.planning_model.weeks,
        self.planning_model.shift_codes,
        locked_team_shift=self.planning_model.locked_team_shift,
        shift_types=self.planning_model.shift_types,
        rotation_patterns=rotation_patterns  # NEU: Pass DB patterns
    )
    # ...
```

---

**Ende der Analyse**

**Erstellt von**: GitHub Copilot Agent  
**Datum**: 2026-02-05  
**Version**: 1.0
