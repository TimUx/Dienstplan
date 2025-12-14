# Test Plan for Shift Editing and TD Function Fixes

## Test Environment Setup
1. Initialize database: `python db_init.py`
2. Start application: `python launcher.py`
3. Login as admin: admin@fritzwinter.de / Admin123!

## Test Cases

### 1. Month View - Shift Editing
**Objective**: Verify shifts are clickable in month view

**Steps**:
1. Navigate to Schedule view
2. Switch to "Monat" (Month) tab
3. Navigate to a month with planned shifts
4. Click on any shift badge (F, S, N, ZD, etc.)

**Expected Result**:
- Edit Shift modal opens
- All shift details are populated correctly
- Can modify shift details and save
- Can delete shift

**Status**: ⬜ Not Tested / ✅ Passed / ❌ Failed

---

### 2. Year View - Shift Editing
**Objective**: Verify shifts are clickable in year view

**Steps**:
1. Navigate to Schedule view
2. Switch to "Jahr" (Year) tab
3. Select a year with planned shifts
4. Click on any shift badge in the year view

**Expected Result**:
- Edit Shift modal opens
- All shift details are populated correctly

**Status**: ⬜ Not Tested / ✅ Passed / ❌ Failed

---

### 3. New Shift Button
**Objective**: Verify new shift creation functionality

**Steps**:
1. Navigate to Schedule view
2. Click on "+ Neue Schicht" button in controls area
3. Fill in all required fields:
   - Select employee
   - Select date
   - Select shift type
4. Click "Speichern" (Save)

**Expected Result**:
- Modal opens with empty form
- Date defaults to current view date
- Can successfully create new shift
- Schedule refreshes to show new shift

**Status**: ⬜ Not Tested / ✅ Passed / ❌ Failed

---

### 4. TD Qualification - Employee Management
**Objective**: Verify TD qualification field in employee form

**Steps**:
1. Navigate to Mitarbeiter (Employees) view
2. Click "+ Mitarbeiter hinzufügen"
3. Verify "TD-Qualifiziert (Tagdienst)" checkbox exists
4. Fill in employee details and check TD-Qualifiziert
5. Save employee
6. Edit employee again

**Expected Result**:
- TD checkbox appears in Sonderfunktionen section
- Can check/uncheck TD qualification
- TD qualification is saved correctly
- TD qualification is displayed when editing

**Status**: ⬜ Not Tested / ✅ Passed / ❌ Failed

---

### 5. TD Shift Planning
**Objective**: Verify TD shifts are planned and saved

**Steps**:
1. Ensure at least one employee has TD-Qualifiziert checked
2. Navigate to Schedule view
3. Click "Schichten planen"
4. Select a time period (month or year)
5. Execute planning
6. Check schedule for TD badges

**Expected Result**:
- Planning completes successfully
- TD shifts appear in schedule
- TD shifts are displayed with correct color (#673AB7)
- One TD qualified employee is assigned per week (Mon-Fri)

**Status**: ⬜ Not Tested / ✅ Passed / ❌ Failed

---

### 6. TD Shift Display
**Objective**: Verify TD shifts are displayed in all views

**Steps**:
1. Navigate to Schedule view
2. Check Week view - should see TD badges
3. Switch to Month view - should see TD badges
4. Switch to Year view - should see TD badges

**Expected Result**:
- TD badges are visible in all three views
- TD badges have purple color (#673AB7)
- TD badges are clickable (like other shifts)

**Status**: ⬜ Not Tested / ✅ Passed / ❌ Failed

---

### 7. TD Shift Editing
**Objective**: Verify TD shifts can be edited

**Steps**:
1. Find a TD shift in any view
2. Click on the TD badge
3. Modify shift details (change employee, date, or mark as fixed)
4. Save changes

**Expected Result**:
- Edit modal opens for TD shift
- Can modify TD shift details
- Changes are saved correctly
- Schedule updates to show changes

**Status**: ⬜ Not Tested / ✅ Passed / ❌ Failed

---

### 8. Database Migration
**Objective**: Verify migration script works on existing database

**Steps**:
1. Create a database without IsTdQualified field (use old schema)
2. Run migration script: `python migrate_add_td_support.py dienstplan.db`
3. Verify migration completes successfully
4. Start application and verify it works

**Expected Result**:
- Migration script runs without errors
- IsTdQualified column is added
- TD shift type is added
- Application works normally

**Status**: ⬜ Not Tested / ✅ Passed / ❌ Failed

---

### 9. Shift Badge Styling
**Objective**: Verify all shift types have proper styling

**Steps**:
1. Navigate to Schedule view with various shift types
2. Verify colors for each shift type:
   - F (Früh): Green
   - S (Spät): Orange
   - N (Nacht): Blue
   - ZD (Zwischendienst): Purple
   - TD (Tagdienst): Purple (#673AB7)
   - BMT: Red
   - BSB: Pink

**Expected Result**:
- All shift types have correct colors
- Lock icon (🔒) appears on fixed shifts
- Hover shows shift name in tooltip

**Status**: ⬜ Not Tested / ✅ Passed / ❌ Failed

---

### 10. Employee Caching
**Objective**: Verify employee cache works correctly

**Steps**:
1. Start fresh session (clear cache/reload page)
2. Open new shift modal
3. Verify employees load
4. Close modal and reopen
5. Verify employees load quickly (from cache)

**Expected Result**:
- First load fetches employees from API
- Subsequent loads use cached data
- No errors in console

**Status**: ⬜ Not Tested / ✅ Passed / ❌ Failed

---

## Regression Tests

### Week View Still Works
**Objective**: Verify week view wasn't broken by changes

**Steps**:
1. Navigate to Schedule view (default is week view)
2. Click on various shift badges
3. Create new shifts
4. Edit existing shifts

**Expected Result**:
- All functionality works as before
- Shifts are clickable
- Edit modal works correctly

**Status**: ⬜ Not Tested / ✅ Passed / ❌ Failed

---

## Security Tests

### Authentication Required
**Objective**: Verify only authenticated users can edit shifts

**Steps**:
1. Logout (if logged in)
2. Navigate to Schedule view
3. Verify shift badges are NOT clickable
4. Verify "+ Neue Schicht" button is not visible

**Expected Result**:
- Unauthenticated users cannot edit shifts
- Edit functionality only available to Admin/Disponent

**Status**: ⬜ Not Tested / ✅ Passed / ❌ Failed

---

## Notes
- All tests should be performed with admin user first
- Some tests should be repeated with different user roles
- Document any unexpected behavior or bugs found
- Check browser console for JavaScript errors during testing
