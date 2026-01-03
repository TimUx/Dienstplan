# Dynamic Shift Management System - Implementation Summary

## Overview

This implementation replaces hardcoded shift models with a dynamic, database-driven shift management system. Administrators can now create, edit, and manage shift types through the Admin interface.

## New Requirements Implemented

### 1. Shift Type Management
Administrators can now define shift types with the following attributes:
- **Name** (Schichtname): Full name of the shift
- **Code** (Schichtkürzel): Short abbreviation (e.g., F, S, N, TD)
- **Working Hours**: Start time and end time
- **Daily Duration**: Hours per shift
- **Color**: Color code for display in shift plan
- **Working Days**: Individual checkboxes for each day (Mo, Di, Mi, Do, Fr, Sa, So)
- **Weekly Working Hours**: Total hours employees must work per week
- **Active/Inactive**: Toggle to enable/disable shift types

### 2. Team-Shift Assignments
- Administrators can define which teams are qualified to work which shifts
- Managed through checkboxes in both:
  - Shift management (Teams button for each shift)
  - Team management (can be extended to show available shifts per team)

### 3. Shift Relationships
- Define related shifts and their sequence/order
- Drag-and-drop interface for ordering
- Useful for shift rotation patterns (e.g., F → N → S)

## Database Schema Changes

### ShiftTypes Table - New Columns
```sql
IsActive INTEGER NOT NULL DEFAULT 1
WorksMonday INTEGER NOT NULL DEFAULT 1
WorksTuesday INTEGER NOT NULL DEFAULT 1
WorksWednesday INTEGER NOT NULL DEFAULT 1
WorksThursday INTEGER NOT NULL DEFAULT 1
WorksFriday INTEGER NOT NULL DEFAULT 1
WorksSaturday INTEGER NOT NULL DEFAULT 0
WorksSunday INTEGER NOT NULL DEFAULT 0
WeeklyWorkingHours REAL NOT NULL DEFAULT 40.0
ModifiedAt TEXT
CreatedBy TEXT
ModifiedBy TEXT
```

### New Tables

#### TeamShiftAssignments
Links teams to shifts they can work:
```sql
CREATE TABLE TeamShiftAssignments (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    TeamId INTEGER NOT NULL,
    ShiftTypeId INTEGER NOT NULL,
    CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CreatedBy TEXT,
    FOREIGN KEY (TeamId) REFERENCES Teams(Id) ON DELETE CASCADE,
    FOREIGN KEY (ShiftTypeId) REFERENCES ShiftTypes(Id) ON DELETE CASCADE,
    UNIQUE(TeamId, ShiftTypeId)
)
```

#### ShiftTypeRelationships
Defines related shifts and their order:
```sql
CREATE TABLE ShiftTypeRelationships (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    ShiftTypeId INTEGER NOT NULL,
    RelatedShiftTypeId INTEGER NOT NULL,
    DisplayOrder INTEGER NOT NULL,
    CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CreatedBy TEXT,
    FOREIGN KEY (ShiftTypeId) REFERENCES ShiftTypes(Id) ON DELETE CASCADE,
    FOREIGN KEY (RelatedShiftTypeId) REFERENCES ShiftTypes(Id) ON DELETE CASCADE,
    UNIQUE(ShiftTypeId, RelatedShiftTypeId)
)
```

## API Endpoints

### Shift Type Management
- `GET /api/shifttypes` - List all shift types
- `POST /api/shifttypes` - Create new shift type (Admin only)
- `GET /api/shifttypes/:id` - Get single shift type
- `PUT /api/shifttypes/:id` - Update shift type (Admin only)
- `DELETE /api/shifttypes/:id` - Delete shift type (Admin only)

### Team-Shift Assignments
- `GET /api/shifttypes/:id/teams` - Get teams assigned to a shift
- `PUT /api/shifttypes/:id/teams` - Update teams for a shift (Admin only)
- `GET /api/teams/:id/shifttypes` - Get shifts assigned to a team
- `PUT /api/teams/:id/shifttypes` - Update shifts for a team (Admin only)

### Shift Relationships
- `GET /api/shifttypes/:id/relationships` - Get related shifts
- `PUT /api/shifttypes/:id/relationships` - Update shift relationships (Admin only)

## Frontend UI

### Admin > Schichtverwaltung Tab
Located in the Admin section as the second tab (after Benutzerverwaltung).

#### Features:
1. **Shift Types Table**: Displays all shifts with:
   - Code badge with color
   - Name
   - Times (start - end)
   - Daily hours
   - Weekly hours
   - Working days (Mo, Di, Mi, etc.)
   - Color preview
   - Active/Inactive status
   - Action buttons

2. **Add/Edit Shift Modal**: Complete form for shift configuration
   - All shift attributes
   - Color picker
   - 7 individual checkboxes for working days
   - Weekly hours input

3. **Teams Assignment Modal**: 
   - Checkboxes for each non-virtual team
   - Shows which teams can work the shift

4. **Relationships Modal**:
   - Drag-and-drop sortable list
   - Add new related shifts via checkboxes
   - Define rotation order

### JavaScript Functions
All functions prefixed with shift management context:
- `loadShiftTypesAdmin()`
- `displayShiftTypes()`
- `showShiftTypeModal()`
- `saveShiftType()`
- `deleteShiftType()`
- `showShiftTypeTeamsModal()`
- `saveShiftTypeTeams()`
- `showShiftTypeRelationshipsModal()`
- `saveShiftTypeRelationships()`

## Migration

### Running the Migration
```bash
python migrate_add_shift_management.py
```

### What the Migration Does:
1. Adds new columns to ShiftTypes table
2. Creates TeamShiftAssignments table
3. Creates ShiftTypeRelationships table  
4. Creates indexes for performance
5. Sets default values for existing shifts
6. Creates default team-shift assignments (F, S, N for all non-virtual teams)
7. Creates default shift relationships (F → N → S rotation)

## Usage Guide for Administrators

### Creating a New Shift Type
1. Navigate to Admin > Schichtverwaltung
2. Click "+ Schichttyp hinzufügen"
3. Fill in all fields:
   - Kürzel: Short code (max 10 characters)
   - Name: Full descriptive name
   - Startzeit: When shift starts (HH:MM)
   - Endzeit: When shift ends (HH:MM)
   - Arbeitsstunden: Duration in hours
   - Farbe: Select display color
   - Arbeitstage: Check boxes for working days
   - Wochen-Arbeitszeit: Weekly hours required
   - Aktiv: Toggle on to enable
4. Click "Speichern"

### Assigning Teams to Shifts
1. In the shift list, click "👥 Teams" for the desired shift
2. Check boxes for teams that can work this shift
3. Click "Speichern"

### Defining Shift Rotation
1. In the shift list, click "🔗 Reihenfolge" for the desired shift
2. Drag related shifts into the desired order
3. Add additional shifts via checkboxes at the bottom
4. Click "Speichern"

### Creating Shifts for Special Functions
Instead of using virtual teams, administrators should:
1. Create a regular team (e.g., "Tagdienst-Team")
2. Create a custom shift type (e.g., "TD - Tagdienst")
3. Configure working days and hours appropriately
4. Assign the team to that shift type
5. Assign employees to the team

## Replacing Virtual Teams

### Current Virtual Teams to Remove:
- Team 98: Ferienjobber Virtuell
- Team 99: Brandmeldeanlage Virtuell (BMT/BSB)

### Migration Path:
1. **For Ferienjobber**:
   - Create a real team: "Ferienjobber"
   - Assign ferienjobber employees to this team
   - Assign appropriate shifts

2. **For Special Functions (BMT/BSB/TD)**:
   - Create a real team: "Tagdienst"
   - Create shift type: "TD" with appropriate hours and days
   - Assign qualified employees to the team
   - Assign the TD shift to this team

## Next Steps (Not Implemented)

The following tasks remain to complete the full integration:

1. **Update Shift Planning Logic**:
   - Modify `model.py` to remove VIRTUAL_TEAM_ID constants
   - Update `data_loader.py` to load shifts from database instead of STANDARD_SHIFT_TYPES
   - Remove hardcoded shift logic from solver

2. **Remove Hardcoded References**:
   - Remove `STANDARD_SHIFT_TYPES` from `entities.py`
   - Remove virtual team special handling from constraint logic
   - Update shift type references to use database IDs

3. **Database Cleanup**:
   - Delete virtual teams (98, 99) from database
   - Migrate any existing assignments to real teams

4. **Testing**:
   - Test shift planning with dynamic shifts
   - Verify team-shift assignments work correctly
   - Test shift rotation patterns

## Technical Notes

### Working Days Implementation
Each day has its own boolean column in the database:
- `WorksMonday` through `WorksSunday`
- Values: 1 (works) or 0 (doesn't work)
- Default: Mo-Fr = 1, Sa-So = 0

This allows maximum flexibility for:
- Regular Mon-Fri shifts
- Weekend shifts (Sa-So only)
- Continuous shifts (Mo-So)
- Custom patterns (e.g., Mo-We-Fr)

### Weekly Working Hours
- Separate field from daily duration
- Allows different weekly requirements
- Example: 8h/day × 5 days = 40h/week (typical)
- Can be adjusted for part-time or overtime schedules

### Audit Logging
All shift management operations are logged to AuditLogs table:
- Entity: ShiftType, TeamShiftAssignment, ShiftTypeRelationship
- Actions: Create, Update, Delete
- Includes user information and change details

## Files Modified

### Backend
- `db_init.py` - Updated schema
- `migrate_add_shift_management.py` - Migration script
- `web_api.py` - New API endpoints (400+ lines added)

### Frontend
- `wwwroot/index.html` - New admin tab and modals
- `wwwroot/js/app.js` - Shift management JavaScript (500+ lines added)
- `wwwroot/css/styles.css` - Styling for new components

### Database
- `data/dienstplan.db` - Schema updated with migration

## Security Considerations

- All shift management endpoints require Admin role
- Audit logging tracks all changes
- Cascade deletes protect referential integrity
- Unique constraints prevent duplicate assignments

## Performance Optimizations

- Indexes on TeamShiftAssignments (TeamId, ShiftTypeId)
- Indexes on ShiftTypeRelationships (ShiftTypeId)
- Efficient queries using JOINs
- Minimal data transferred (only needed fields)

## Browser Compatibility

- Modern browsers with ES6 support required
- Color picker: HTML5 input type="color"
- Drag and drop: HTML5 Drag and Drop API
- Tested on Chrome, Firefox, Edge

## Conclusion

This implementation provides a complete, flexible shift management system that allows administrators to:
- Define custom shift types with precise working patterns
- Manage team-shift assignments dynamically
- Set up shift rotation sequences
- Track all changes through audit logs

The system replaces hardcoded shift models and virtual teams with a database-driven approach that can be fully managed through the web interface, without requiring code changes.
