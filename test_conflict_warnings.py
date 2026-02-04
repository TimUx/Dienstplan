"""
Test to verify that the warnings are actually printed when conflicts are detected.
This test captures stdout to verify warning messages.
"""

from datetime import date, timedelta
from entities import Employee, Team, Absence, ShiftType
from model import ShiftPlanningModel
import sys
from io import StringIO


def test_warning_messages_printed():
    """
    Test that warning messages are actually printed when conflicts are detected.
    """
    print("=" * 70)
    print("TEST: Verify Warning Messages Are Printed")
    print("=" * 70)
    
    # Create shift types
    shift_types = [
        ShiftType(id=1, code='F', name='Früh', start_time='06:00', end_time='14:30', 
                 hours=8.5, min_staff_weekday=4, max_staff_weekday=6),
        ShiftType(id=2, code='S', name='Spät', start_time='13:30', end_time='22:00',
                 hours=8.5, min_staff_weekday=3, max_staff_weekday=5),
        ShiftType(id=3, code='N', name='Nacht', start_time='21:30', end_time='06:30',
                 hours=9, min_staff_weekday=3, max_staff_weekday=4),
    ]
    
    # Create teams
    teams = [
        Team(id=1, name='Alpha', allowed_shift_type_ids=[1, 2, 3]),
    ]
    
    # Create employees
    employees = []
    for i in range(5):
        emp_id = i + 1
        emp = Employee(
            id=emp_id,
            vorname=f'First{emp_id}',
            name=f'Last{emp_id}',
            personalnummer=f'{emp_id:04d}',
            team_id=1,
        )
        employees.append(emp)
    
    # Planning period: March 1-31, 2026
    start_date = date(2026, 3, 1)  # Sunday
    end_date = date(2026, 3, 31)    # Tuesday
    absences = []
    
    # Create conflicting locked assignments
    # Team 1, Week 0 -> 'F'
    locked_team_shift = {
        (1, 0): 'F'
    }
    
    # Multiple employees locked to 'S' for dates in week 0
    # This should trigger multiple warnings
    locked_employee_shift = {}
    for emp_id in [2, 3, 4]:
        for day_offset in range(5):  # Mon-Fri
            d = date(2026, 2, 23) + timedelta(days=day_offset)
            locked_employee_shift[(emp_id, d)] = 'S'
    
    print("\nSetup:")
    print(f"  Planning period: {start_date} to {end_date}")
    print(f"  locked_team_shift: Team 1, Week 0 -> 'F'")
    print(f"  locked_employee_shift: Employees 2,3,4 (Team 1), Week 0 dates -> 'S'")
    print(f"  ⚠️  CONFLICT: Team locked to 'F' but employees locked to 'S'")
    
    # Capture stdout to check for warning messages
    print("\nCreating model (should print warnings)...")
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    try:
        model = ShiftPlanningModel(
            employees=employees,
            teams=teams,
            start_date=start_date,
            end_date=end_date,
            absences=absences,
            shift_types=shift_types,
            locked_team_shift=locked_team_shift,
            locked_employee_shift=locked_employee_shift
        )
        
        # Get captured output
        warnings_output = captured_output.getvalue()
        sys.stdout = old_stdout
        
        # Check if warnings were printed
        if "WARNING: Skipping conflicting locked shift" in warnings_output:
            print("✓ Warnings were printed:")
            print(warnings_output)
            warning_count = warnings_output.count("WARNING: Skipping conflicting locked shift")
            print(f"\nTotal warnings: {warning_count}")
            print(f"✓ Model created successfully despite {warning_count} conflicts")
            print("✅ TEST PASSED: Conflicts detected and handled gracefully")
            return True
        else:
            print("❌ TEST FAILED: Expected warnings but none were printed")
            print(f"Captured output: {warnings_output}")
            return False
            
    except Exception as e:
        sys.stdout = old_stdout
        print(f"❌ TEST FAILED: Exception during model creation")
        print(f"   Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🔧 Testing Warning Message Output 🔧\n")
    
    test_passed = test_warning_messages_printed()
    
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    if test_passed:
        print("✅ TEST PASSED")
        print("\nThe fix successfully:")
        print("  1. Detects conflicting locked shifts")
        print("  2. Prints appropriate warning messages")
        print("  3. Skips conflicting constraints to prevent INFEASIBLE")
    else:
        print("❌ TEST FAILED")
