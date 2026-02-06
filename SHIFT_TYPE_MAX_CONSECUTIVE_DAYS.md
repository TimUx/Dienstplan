# Per-Shift-Type Maximum Consecutive Days Configuration

## Overview

The shift planning system now allows each shift type to have its own maximum consecutive days setting. This replaces the previous global settings for maximum consecutive shifts and maximum consecutive night shifts.

## Changes Summary

### Previous Behavior (Global Settings)

Previously, there were two global settings in `GlobalSettings`:
- `MaxConsecutiveShifts`: Applied to all shift types (default: 6 days)
- `MaxConsecutiveNightShifts`: Applied only to night shifts (default: 3 days)

These settings were applied uniformly and could not be customized per shift type.

### New Behavior (Per-Shift-Type Settings)

Now, each shift type has its own `MaxConsecutiveDays` setting that defines how many consecutive days that specific shift can be worked before requiring a break.

**Benefits:**
- More flexible configuration for different shift types
- Easier to manage as shift types grow
- More intuitive: settings are where they belong (with the shift type)
- Custom shift types can have their own limits

## Database Changes

### Schema Update

A new column `MaxConsecutiveDays` has been added to the `ShiftTypes` table:

```sql
ALTER TABLE ShiftTypes 
ADD COLUMN MaxConsecutiveDays INTEGER NOT NULL DEFAULT 6
```

### Default Values

- **Frühschicht (F)**: 6 consecutive days (works all 7 days)
- **Spätschicht (S)**: 6 consecutive days (works all 7 days)
- **Nachtschicht (N)**: 3 consecutive days (works all 7 days, but needs more rest)
- **Zwischendienst (ZD)**: 6 consecutive days (if configured)
- **BMT/BSB shifts**: 5 consecutive days (weekday-only shifts, Monday-Friday)
- **Other custom shifts**: 6 consecutive days (default)

## Migration

### For Existing Databases

Run the migration script to add the column and migrate existing settings:

```bash
python3 migrate_add_max_consecutive_days.py dienstplan.db
```

The script will:
1. Add the `MaxConsecutiveDays` column to `ShiftTypes` table
2. Read the existing `GlobalSettings` values
3. Apply `MaxConsecutiveNightShifts` value to "N" shift types
4. Apply `MaxConsecutiveShifts` value to all other shift types

**Note:** The old `MaxConsecutiveShifts` and `MaxConsecutiveNightShifts` columns in `GlobalSettings` are kept for backward compatibility but are no longer used by the algorithm.

## Algorithm Changes

### Constraint Logic

The constraint function `add_consecutive_shifts_constraints()` in `constraints.py` has been updated to:

1. Accept a `shift_types` parameter containing all shift type configurations
2. For each shift type, enforce its specific `max_consecutive_days` limit
3. Check violations per shift type rather than globally

**Key Points:**
- An employee can work up to `max_consecutive_days` consecutive days for a specific shift type
- After reaching the limit, the employee must have at least one day off from that shift type
- Switching to a different shift type is allowed (constraints are per shift type, not global)

### Example Scenarios

#### Scenario 1: Night Shift Limit
```
Settings: N shift has MaxConsecutiveDays = 3

Day 1: N ✓
Day 2: N ✓
Day 3: N ✓
Day 4: N ❌ (violation - exceeds limit of 3)
```

#### Scenario 2: Switching Shift Types
```
Settings: N shift has MaxConsecutiveDays = 3, F shift has MaxConsecutiveDays = 6

Day 1: N ✓
Day 2: N ✓
Day 3: N ✓
Day 4: F ✓ (allowed - different shift type)
Day 5: F ✓
Day 6: F ✓
```

## UI Changes

### Shift Type Management

The shift type edit form now includes a new field:

**Max. aufeinanderfolgende Tage*** (Maximum Consecutive Days)
- Type: Number input
- Range: 1-10
- Default: 6
- Description: "Maximale Anzahl aufeinanderfolgender Tage, die diese Schicht gearbeitet werden darf"

### Location

The setting is configured per shift type in:
**Verwaltung → Schichten** (Management → Shifts)

When creating or editing a shift type, administrators can set the maximum consecutive days for that specific shift.

## API Changes

### GET /api/shifttypes

Returns shift types including the new `maxConsecutiveDays` field:

```json
{
  "id": 3,
  "code": "N",
  "name": "Nachtdienst",
  "maxConsecutiveDays": 3,
  ...
}
```

### POST /api/shifttypes

When creating a shift type, include `maxConsecutiveDays` in the request body:

```json
{
  "code": "N",
  "name": "Nachtdienst",
  "maxConsecutiveDays": 3,
  ...
}
```

### PUT /api/shifttypes/{id}

When updating a shift type, include `maxConsecutiveDays` in the request body:

```json
{
  "maxConsecutiveDays": 4,
  ...
}
```

## Testing

A test script `test_max_consecutive_days.py` is provided to verify the implementation:

```bash
python3 test_max_consecutive_days.py
```

This test validates:
- Shift types have correct default values
- Night shifts have lower limits (3 days)
- Regular shifts have higher limits (6 days)
- Constraint logic works per shift type

## Backward Compatibility

- Old databases will work after running the migration script
- The `GlobalSettings` table still contains the old columns but they are not used
- The migration script can be run multiple times safely (idempotent)
- Default values ensure smooth transition for new shift types

## Recommendations

1. **Review Shift Type Settings**: After migration, review each shift type's `MaxConsecutiveDays` setting to ensure it matches your operational requirements.

2. **Night Shifts**: Consider keeping night shifts at 3 consecutive days or lower for employee health and safety.

3. **Day Shifts**: Standard day shifts (F, S) typically use 6 consecutive days, but this can be adjusted based on your needs.

4. **Special Shifts**: For special shift types (BMT, BSB, TD, etc.), configure appropriate limits based on the nature of the work.

5. **Testing**: After changing settings, run test scenarios in the shift planning to ensure the constraints work as expected.

## Support

If you encounter issues with the migration or have questions about configuring per-shift-type limits, please contact the development team or open an issue in the repository.
