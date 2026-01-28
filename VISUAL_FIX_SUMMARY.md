# Visual Summary: Lehrgang Statistics Fix

## Before Fix ❌

### Statistics Display
```
Von: 01.01.2026  Bis: 31.01.2026
⏱️ Arbeitsstunden
Stefanie Klein    168.0h (21 Schichten)  ❌ INCORRECT
```

### What Was Happening
```
┌─────────────────────────────────────────────────────────────┐
│ Database: Absences Table                                    │
├─────────────────────────────────────────────────────────────┤
│ EmployeeId │ Type │ StartDate   │ EndDate     │            │
│ 12         │  3   │ 2026-01-12  │ 2026-01-18  │            │
│            │  ↑   │                                         │
│            │  INTEGER value (3 = Lehrgang)                 │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Statistics Query (BEFORE FIX)                               │
├─────────────────────────────────────────────────────────────┤
│ SELECT SUM(...) * 8.0 as LehrgangHours                      │
│ FROM Absences a                                             │
│ WHERE a.Type = 'L'  ← ❌ STRING never matches INTEGER!     │
│                                                              │
│ Result: 0 rows (no Lehrgang hours found)                    │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Statistics Calculation                                      │
├─────────────────────────────────────────────────────────────┤
│ Shift Hours:    168h (21 shifts × 8h)                      │
│ Lehrgang Hours:   0h ← ❌ MISSING!                          │
│ Total Hours:    168h ← ❌ INCORRECT                         │
└─────────────────────────────────────────────────────────────┘
```

## After Fix ✅

### Statistics Display
```
Von: 01.01.2026  Bis: 31.01.2026
⏱️ Arbeitsstunden
Stefanie Klein    224.0h (21 Schichten)  ✅ CORRECT
```

### What Happens Now
```
┌─────────────────────────────────────────────────────────────┐
│ Database: Absences Table                                    │
├─────────────────────────────────────────────────────────────┤
│ EmployeeId │ Type │ StartDate   │ EndDate     │            │
│ 12         │  3   │ 2026-01-12  │ 2026-01-18  │            │
│            │  ↑   │                                         │
│            │  INTEGER value (3 = Lehrgang)                 │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Statistics Query (AFTER FIX)                                │
├─────────────────────────────────────────────────────────────┤
│ SELECT SUM(...) * 8.0 as LehrgangHours                      │
│ FROM Absences a                                             │
│ WHERE a.Type = 3  ← ✅ INTEGER matches INTEGER!            │
│                                                              │
│ Result: 1 row (7 days found)                                │
└─────────────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ Statistics Calculation                                      │
├─────────────────────────────────────────────────────────────┤
│ Shift Hours:    168h (21 shifts × 8h)                      │
│ Lehrgang Hours:  56h (7 days × 8h) ← ✅ NOW INCLUDED!      │
│ Total Hours:    224h ← ✅ CORRECT                           │
└─────────────────────────────────────────────────────────────┘
```

## Detailed Scenario: Stefanie Klein

### Schedule for January 2026
```
Woche 1:  F  F  F  -  N  N  N  (6 shifts = 48h)
Woche 2:  S  S  N  -  L  L  L  (3 shifts, 4 Lehrgang days)
Woche 3:  L  L  L  L  F  F  F  (3 Lehrgang days, 3 shifts = 24h)
Woche 4:  F  F  N  -  F  F  F  (6 shifts = 48h)
Woche 5:  F  F  N              (3 shifts = 24h)

Legend:
F = Frühdienst (Early shift, 8h)
S = Spätdienst (Late shift, 8h)
N = Nachtdienst (Night shift, 8h)
L = Lehrgang (Training, counts as 8h)
- = Day off
```

### Hours Breakdown

**BEFORE FIX ❌:**
```
Shifts worked:      21 shifts × 8h = 168h
Lehrgang days:       7 days  × 8h =   0h ← Missing!
                                    ─────
Total:                              168h ← Wrong!
```

**AFTER FIX ✅:**
```
Shifts worked:      21 shifts × 8h = 168h
Lehrgang days:       7 days  × 8h =  56h ← Now included!
                                    ─────
Total:                              224h ← Correct!
```

### The Math
```
Initial planned:    27 shifts × 8h = 216h
Lehrgang period:    Jan 12-18 (7 days)
Shifts removed:     6 shifts       = -48h
Lehrgang added:     7 days × 8h    = +56h
                                    ─────
Final total:        216 - 48 + 56 = 224h ✅
```

## Type Mapping Reference

```
┌──────────┬─────────────────────────┬──────────────┐
│ Integer  │ Description             │ Code         │
├──────────┼─────────────────────────┼──────────────┤
│    1     │ Arbeitsunfähigkeit      │ AU (Sick)    │
│    2     │ Urlaub                  │ U (Vacation) │
│    3     │ Lehrgang                │ L (Training) │
└──────────┴─────────────────────────┴──────────────┘
```

## Code Change

### The Fix (One Line!)

**File:** `web_api.py` line 4880

**Before:**
```python
WHERE a.Type = 'L'  # ❌ String comparison
```

**After:**
```python
WHERE a.Type = 3    # ✅ Integer comparison
```

## Impact on All Employees

Any employee with Lehrgang absences will now see corrected hours:

**Example employees affected:**
```
BEFORE FIX              AFTER FIX
Stefanie Klein  168h  →  224h  (+56h for 7 Lehrgang days)
Robert Franke   160h  →  160h  (no Lehrgang, no change)
```

## Testing Confirmation

```
✅ test_lehrgang_statistics.py - PASS
   - AU: Shifts removed, hours NOT counted ✅
   - U:  Shifts removed, hours NOT counted ✅
   - L:  Shifts removed, hours COUNTED ✅

✅ test_lehrgang_scenario.py - PASS
   - Exact scenario: 216h → 224h ✅

✅ CodeQL Security Scan - PASS
   - 0 vulnerabilities found ✅
```

## Deployment Checklist

- [x] Code fixed in `web_api.py`
- [x] Tests updated and passing
- [x] Security scan clean
- [x] Documentation complete
- [ ] Deploy to production
- [ ] Clear browser cache
- [ ] Verify Stefanie Klein shows 224h
- [ ] Verify other employees with Lehrgang

## Expected Result After Deployment

Statistics page should now show:
```
⏱️ Arbeitsstunden
Stefanie Klein    224.0h (21 Schichten)  ✅
Robert Franke     160.0h (20 Schichten)  ✅
```

**Success Criteria:**
- ✅ Lehrgang days counted as 8h each
- ✅ Total hours = shift hours + Lehrgang hours
- ✅ Display matches actual worked time equivalent
