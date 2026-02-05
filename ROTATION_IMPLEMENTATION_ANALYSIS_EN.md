# Shift Rotation Implementation - Analysis

**Date**: 2026-02-05  
**Status**: ✅ COMPLETE  
**Language**: English

## Executive Summary

The shift rotation pattern (F → N → S) is **HARDCODED** in the source code and does **NOT use** the database settings from the `RotationGroups` and `RotationGroupShifts` tables.

## Problem Statement

**Question**: Is the shift rotation hardcoded or does it use database settings via rotation groups?

**Answer**: The rotation is **hardcoded**. While database tables exist, they are not used by the solver.

---

## Detailed Analysis

### 1. Hardcoded Rotation Pattern

**Location**: `constraints.py`, line 47

```python
# Fixed rotation pattern: F → N → S
ROTATION_PATTERN = ["F", "N", "S"]
```

This constant is used in two constraint functions:

#### a) Team Rotation (HARD Constraint)

**Function**: `add_team_rotation_constraints()` (lines 110-197)

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

**Characteristics**:
- HARD constraint (must be satisfied)
- Based on ISO week numbers for consistency across month boundaries
- Team-based offset for different starting points
- No connection to database

#### b) Employee Rotation Order (SOFT Constraint)

**Function**: `add_employee_weekly_rotation_order_constraints()` (lines 199-407)

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

**Characteristics**:
- SOFT constraint (can be violated with high penalty)
- Penalty: 10,000 points per violation
- Allows repetitions (F→F, N→N, S→S)
- Prevents invalid transitions (F→S, N→F, S→N)
- No connection to database

### 2. Database RotationGroups - Not Used!

**Schema**: `db_init.py`, lines 286-313

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
        RotationOrder INTEGER NOT NULL,  # <<<< Important! Order could be stored here
        CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        CreatedBy TEXT,
        FOREIGN KEY (RotationGroupId) REFERENCES RotationGroups(Id) ON DELETE CASCADE,
        FOREIGN KEY (ShiftTypeId) REFERENCES ShiftTypes(Id) ON DELETE CASCADE,
        UNIQUE(RotationGroupId, ShiftTypeId)
    )
""")
```

**Code Comment** (db_init.py, lines 268-271):
```python
# DEPRECATED: Use RotationGroups instead for new implementations.
# Migration strategy: This table will be maintained for backward compatibility.
# New features should use RotationGroups. A future migration script will convert
# existing ShiftTypeRelationships to RotationGroups when all features are migrated.
```

**Status**: Tables exist, but:
- ❌ Not used in solver
- ❌ Not loaded in constraints
- ❌ No connection to `ROTATION_PATTERN`
- ✅ Only available via REST API
- ✅ Only manageable in web UI

### 3. REST API Endpoints (Administration Only)

**File**: `web_api.py`, lines 2367-2599

```python
@app.route('/api/rotationgroups', methods=['GET'])
@require_role(['Admin', 'Disponent'])
def get_rotation_groups():
    """Get all rotation groups"""
    # Loads from database, but not used by solver

@app.route('/api/rotationgroups', methods=['POST'])
@require_role('Admin')
def create_rotation_group():
    """Create a new rotation group"""
    # Admin can create rotation groups

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

**Purpose**: Only for future use and administrative management.

### 4. Web UI Integration

**File**: `wwwroot/index.html`, lines 1208-1234

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

**JavaScript**: `wwwroot/js/app.js`, lines 5672-6034

```javascript
async function loadRotationGroups() {
    // Loads rotation groups for display
}

function displayRotationGroups(groups) {
    // Displays rotation groups in admin area
}

async function saveRotationGroup(event) {
    // Saves rotation group to database
}
```

**Purpose**: UI for administration, but no effect on solver.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────┐
│                      WEB UI / API                             │
│  (Admin can manage RotationGroups)                           │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    DATABASE                                   │
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
│  │  - RotationOrder ◄── COULD BE USED                      │
│  └────────────────────────────────────────┘                 │
└──────────────────────────────────────────────────────────────┘
                            │
                            │ ❌ NO CONNECTION!
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
│  │   → Uses ROTATION_PATTERN              │                 │
│  │                                        │                 │
│  │ add_employee_weekly_rotation_order..() │                 │
│  │   → VALID_NEXT_SHIFTS hardcoded        │                 │
│  └────────────────────────────────────────┘                 │
└──────────────────────────────────────────────────────────────┘
```

---

## Why Is It Like This?

### Historical Context

1. **Original Implementation**: System was developed with fixed F→N→S rotation
2. **Later Extension**: RotationGroups tables were added as "future feature"
3. **Pending Migration**: Code comments show migration was planned but not implemented

### Code Comment (db_init.py, lines 268-271):

```python
# DEPRECATED: Use RotationGroups instead for new implementations.
# Migration strategy: This table will be maintained for backward compatibility.
# New features should use RotationGroups. A future migration script will convert
# existing ShiftTypeRelationships to RotationGroups when all features are migrated.
```

**Interpretation**: 
- Developers **wanted** to switch to RotationGroups
- Migration was **not yet** implemented
- Current code still uses hardcoded rotation

---

## Pros and Cons

### Current Implementation (Hardcoded)

#### ✅ Advantages:
- Simple and straightforward
- No dependency on database configuration
- Consistent behavior guaranteed
- Fast (no database queries)
- Well tested (see `test_rotation_order.py`, `ROTATION_ORDER_FIX.md`)

#### ❌ Disadvantages:
- Not flexible - changes require code modifications
- Cannot be configured via UI
- Other rotation patterns (e.g., F→S→N) not possible
- Database tables exist but are unused
- Confusing for administrators (UI shows rotation groups but they have no effect)

### Database-based Implementation (Potential)

#### ✅ Potential Advantages:
- Flexible configuration via UI
- Different rotation patterns possible
- Teams can have different rotations
- No code changes when rotation changes
- Administrators have full control

#### ❌ Potential Challenges:
- More complex implementation
- Migration necessary
- Validation required (prevent invalid configurations)
- Tests need adjustment
- Ensure backward compatibility

---

## Recommendations

### Option A: Keep Current State ✅ SIMPLE

**When appropriate**: 
- F→N→S rotation is sufficient
- No changes planned
- Simplicity is preferred

**Actions**:
1. ✅ Create documentation (this document)
2. Add UI warning: "Rotation groups are currently for future use only"
3. Remove RotationGroups management from UI or mark as "Beta feature"

### Option B: Migrate to Database-based Rotation ⚠️ COMPLEX

**When appropriate**:
- Flexible rotation patterns desired
- Teams need different rotations
- Configurability important

**Implementation Steps**:
1. **Extend Data Loader** (`data_loader.py`):
   ```python
   def load_rotation_groups(db_path: str) -> Dict[int, List[str]]:
       """Load rotation patterns from RotationGroups tables"""
       # Query RotationGroups and RotationGroupShifts
       # Return mapping: rotation_group_id -> [shift_codes in order]
   ```

2. **Link Teams with RotationGroups**:
   - New column in Teams table: `RotationGroupId`
   - Migration for existing data

3. **Adjust Constraints** (`constraints.py`):
   ```python
   def add_team_rotation_constraints(
       ...,
       rotation_patterns: Dict[int, List[str]] = None  # New!
   ):
       # If rotation_patterns given, use them
       # Otherwise fallback to ROTATION_PATTERN
       rotation = rotation_patterns.get(team.rotation_group_id, ["F", "N", "S"])
   ```

4. **Adjust Solver** (`solver.py`):
   ```python
   # In __init__ or add_all_constraints:
   rotation_patterns = data_loader.load_rotation_groups(db_path)
   add_team_rotation_constraints(..., rotation_patterns=rotation_patterns)
   ```

5. **Implement Validation**:
   - Ensure RotationOrder is continuous (1, 2, 3, ...)
   - At least 2 shifts per group
   - All shifts in group exist

6. **Extend Tests**:
   - Test with different rotation patterns
   - Test backward compatibility
   - Edge cases (empty group, single shift, etc.)

7. **Migration Script**:
   ```python
   # migrate_to_rotation_groups.py
   def migrate():
       # Create default RotationGroup "Standard F→N→S"
       # Link all teams to this group
       # Verify solver still works
   ```

**Estimated Effort**: 2-3 development days + testing

### Option C: Hybrid Solution ⚙️ MEDIUM

**Concept**: Database as optional extension

**Implementation**:
- Fallback to hardcoded pattern when no DB configuration
- Allows gradual migration
- Minimal breaking changes

```python
def get_rotation_pattern(team: Team, db_patterns: Dict) -> List[str]:
    """Get rotation pattern for team - DB or hardcoded fallback"""
    if team.rotation_group_id and team.rotation_group_id in db_patterns:
        return db_patterns[team.rotation_group_id]
    return ["F", "N", "S"]  # Fallback
```

---

## Conclusion

**Current Situation**:
- ✅ Shift rotation is **HARDCODED**
- ✅ F → N → S pattern is fixed in code
- ❌ RotationGroups tables exist but are **NOT USED**
- ⚠️ UI allows management of rotation groups but **without effect on planning**

**Next Steps**:
1. ✅ Share this documentation with team
2. ⚠️ Make decision: Option A, B, or C?
3. ⚠️ If Option A: Add UI warning or remove feature
4. ⚠️ If Option B/C: Plan and implement migration

**Recommendation**: 
- For immediate use: **Option A** (keep status quo)
- For future flexibility: **Option C** (hybrid solution)
- Only if strong need: **Option B** (complete migration)

---

## Affected Files

### Code Files:
- ✅ `constraints.py` - Rotation logic (hardcoded)
- ✅ `solver.py` - Constraint integration
- ✅ `entities.py` - Data models (RotationGroup, RotationGroupShift)
- ✅ `db_init.py` - Database schema
- ✅ `web_api.py` - REST API for RotationGroups (not used in solver)
- ⚠️ `data_loader.py` - Does NOT load RotationGroups

### Test Files:
- ✅ `test_rotation_order.py` - Tests hardcoded rotation

### Documentation:
- ✅ `ROTATION_ORDER_FIX.md` - Describes current implementation
- ✅ `ROTATION_IMPLEMENTATION_ANALYSIS.md` - Analysis (German)
- ✅ `ROTATION_IMPLEMENTATION_ANALYSIS_EN.md` - This document

### Frontend:
- ⚠️ `wwwroot/index.html` - UI for RotationGroups (no effect on solver)
- ⚠️ `wwwroot/js/app.js` - JavaScript for RotationGroups management

---

## Appendix: Example Code for Migration (Option B)

If migration is desired, here's an example implementation:

```python
# data_loader.py - New function
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


# constraints.py - Modified function
def add_team_rotation_constraints(
    model: cp_model.CpModel,
    team_shift: Dict[Tuple[int, int, str], cp_model.IntVar],
    teams: List[Team],
    weeks: List[List[date]],
    shift_codes: List[str],
    locked_team_shift: Dict[Tuple[int, int], str] = None,
    shift_types: List[ShiftType] = None,
    rotation_patterns: Dict[int, List[str]] = None  # NEW: Optional DB patterns
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


# solver.py - Modified add_all_constraints
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
        rotation_patterns=rotation_patterns  # NEW: Pass DB patterns
    )
    # ...
```

---

**End of Analysis**

**Created by**: GitHub Copilot Agent  
**Date**: 2026-02-05  
**Version**: 1.0
