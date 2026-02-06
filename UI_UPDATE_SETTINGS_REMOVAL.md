# UI Update: Removed Obsolete Consecutive Shift Settings

## Problem

The GlobalSettings UI still displayed the old "Maximale aufeinanderfolgende Schichten" and "Maximale aufeinanderfolgende Nachtschichten" fields, even though these settings have been moved to per-shift-type configuration.

## Solution

Removed these obsolete fields from the GlobalSettings UI and added an informational notice directing users to the correct location.

## Changes Made

### Before (❌ Old UI)

The GlobalSettings page showed:

```
┌─────────────────────────────────────────────────────────────┐
│ Allgemeine Einstellungen                                     │
├─────────────────────────────────────────────────────────────┤
│ ℹ️ Diese Einstellungen gelten für die automatische          │
│   Schichtplanung und Validierung.                           │
│                                                              │
│ Maximale aufeinanderfolgende Schichten: [    6    ]         │
│ Standard: 6 Schichten (inkl. Wochenenden)                   │
│                                                              │
│ Maximale aufeinanderfolgende Nachtschichten: [    3    ]    │
│ Standard: 3 Nachtschichten                                  │
│                                                              │
│ Gesetzliche Ruhezeit zwischen Schichten (Stunden): [ 11 ]   │
│ Standard: 11 Stunden (gesetzlich vorgeschrieben)            │
│                                                              │
│ [ 💾 Einstellungen speichern ]                              │
└─────────────────────────────────────────────────────────────┘
```

### After (✅ New UI)

The GlobalSettings page now shows:

```
┌─────────────────────────────────────────────────────────────┐
│ Allgemeine Einstellungen                                     │
├─────────────────────────────────────────────────────────────┤
│ ℹ️ Diese Einstellungen gelten für die automatische          │
│   Schichtplanung und Validierung.                           │
│                                                              │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ 📌 Hinweis: Die maximale Anzahl aufeinanderfolgender │   │
│ │    Schichten wird jetzt pro Schichttyp konfiguriert. │   │
│ │    Bitte gehen Sie zu Verwaltung → Schichten, um     │   │
│ │    diese Einstellungen für jeden Schichttyp einzeln  │   │
│ │    festzulegen.                                       │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                              │
│ Gesetzliche Ruhezeit zwischen Schichten (Stunden): [ 11 ]   │
│ Standard: 11 Stunden (gesetzlich vorgeschrieben)            │
│                                                              │
│ [ 💾 Einstellungen speichern ]                              │
└─────────────────────────────────────────────────────────────┘
```

## Where to Configure Consecutive Shift Limits Now

The consecutive shift limits are now configured per shift type:

**Navigation:** Verwaltung → Schichten → [Edit Shift Type]

Each shift type now has a field:
- **Max. aufeinanderfolgende Tage**: 1-10 (configurable per shift type)

Example:
- Frühschicht (F): 6 Tage
- Spätschicht (S): 6 Tage
- Nachtschicht (N): 3 Tage
- BMT/BSB: 5 Tage (Monday-Friday only)

## Code Changes

### Frontend (wwwroot/js/app.js)

1. **Removed from `displayGlobalSettings()`:**
   - Input field for "Maximale aufeinanderfolgende Schichten"
   - Input field for "Maximale aufeinanderfolgende Nachtschichten"

2. **Added to `displayGlobalSettings()`:**
   - Warning info box with navigation guidance

3. **Updated `saveGlobalSettings()`:**
   - Removed `maxConsecutiveShifts` from request payload
   - Removed `maxConsecutiveNightShifts` from request payload
   - Only sends `minRestHoursBetweenShifts` now

4. **Removed:**
   - Old duplicate `saveGlobalSettings()` function that used localStorage

### Backend (web_api.py)

1. **Updated `update_global_settings()` endpoint:**
   - Added comment explaining deprecation of consecutive shift fields
   - Preserves existing values for deprecated fields (backward compatibility)
   - Only updates `MinRestHoursBetweenShifts` from user input
   - Updated SQL to only modify `MinRestHoursBetweenShifts` on conflict

## Benefits

✅ **Cleaner UI**: Removed confusing duplicate settings
✅ **Better UX**: Clear guidance where to find the settings
✅ **Consistency**: Settings are where users expect them (with shift types)
✅ **Backward Compatible**: Old database values preserved
✅ **Future-proof**: Supports custom shift types with individual limits

## Testing

- [x] JavaScript compiles without errors
- [x] Python code compiles without errors
- [x] No breaking changes to API
- [x] Backward compatible with existing databases
- [x] UI clearly directs users to new location
