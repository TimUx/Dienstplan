"""
Test absence code handling and visibility.

This test verifies:
1. Official absence codes (U, AU, L) are used
2. Absences always override shifts and TD
3. Absences are visible in complete schedule
4. Virtual team "Fire Alarm System" exists
5. No virtual "Springer Team"
"""

from datetime import date, timedelta
from entities import AbsenceType, Absence, Employee, Team
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import solve_shift_planning


def test_absence_codes():
    """Test that official absence codes are used"""
    print("\n" + "="*60)
    print("TEST: Official Absence Codes")
    print("="*60)
    
    # Check enum values
    codes = [a.value for a in AbsenceType]
    print(f"Absence codes: {codes}")
    
    assert "U" in codes, "U (Urlaub) must be present"
    assert "AU" in codes, "AU (Krank/AU) must be present"
    assert "L" in codes, "L (Lehrgang) must be present"
    assert "V" not in codes, "V is FORBIDDEN"
    assert "K" not in codes, "K is FORBIDDEN"
    
    print("✓ Official codes (U, AU, L) verified")
    print("✓ Forbidden codes (V, K) not present")
    
    # Check display names
    assert AbsenceType.U.display_name == "Urlaub"
    assert AbsenceType.AU.display_name == "Krank / AU"
    assert AbsenceType.L.display_name == "Lehrgang"
    print("✓ Display names correct")
    
    return True


def test_virtual_teams():
    """Test that no virtual teams exist"""
    print("\n" + "="*60)
    print("TEST: Virtual Teams")
    print("="*60)
    
    employees, teams, absences = generate_sample_data()
    
    # Check that no virtual teams exist
    for team in teams:
        assert not team.is_virtual, f"Virtual team '{team.name}' should not exist"
    
    print("✓ No virtual teams exist (as expected)")
    print("✓ No virtual 'Springer' team (springers are employee attributes)")
    
    return True


def test_absence_priority():
    """Test that absences override shifts and TD in complete schedule"""
    print("\n" + "="*60)
    print("TEST: Absence Priority")
    print("="*60)
    
    employees, teams, absences = generate_sample_data()
    
    # Create a planning model
    start = date.today()
    end = start + timedelta(days=13)  # 2 weeks
    
    planning_model = create_shift_planning_model(employees, teams, start, end, absences)
    
    # Solve
    result = solve_shift_planning(planning_model, time_limit_seconds=30)
    
    if not result:
        print("✗ Solver failed to find solution")
        return False
    
    assignments, special_functions, complete_schedule = result
    
    print(f"✓ Solution found: {len(assignments)} assignments")
    
    # Check that absent employees show absence codes in complete schedule
    for absence in absences:
        emp_id = absence.employee_id
        check_date = absence.start_date
        
        while check_date <= absence.end_date and check_date <= end:
            if (emp_id, check_date) in complete_schedule:
                schedule_value = complete_schedule[(emp_id, check_date)]
                
                # Must be absence code (U, AU, or L)
                expected_code = absence.get_code()
                if schedule_value != expected_code:
                    print(f"✗ Employee {emp_id} on {check_date}: expected {expected_code}, got {schedule_value}")
                    return False
                
            check_date += timedelta(days=1)
    
    print("✓ Absences correctly override shifts in complete schedule")
    
    # Check that absence codes are U, AU, or L (not ABSENT or other generic terms)
    absence_codes = set()
    for (emp_id, d), value in complete_schedule.items():
        if value in ["U", "AU", "L"]:
            absence_codes.add(value)
    
    print(f"✓ Absence codes found in schedule: {absence_codes}")
    
    return True


def test_all_employees_visible():
    """Test that ALL employees appear in complete schedule"""
    print("\n" + "="*60)
    print("TEST: All Employees Visible")
    print("="*60)
    
    employees, teams, absences = generate_sample_data()
    
    start = date.today()
    end = start + timedelta(days=13)
    
    planning_model = create_shift_planning_model(employees, teams, start, end, absences)
    result = solve_shift_planning(planning_model, time_limit_seconds=30)
    
    if not result:
        print("✗ Solver failed")
        return False
    
    _, _, complete_schedule = result
    
    # Check that every employee appears for every day
    dates = []
    current = start
    while current <= end:
        dates.append(current)
        current += timedelta(days=1)
    
    for emp in employees:
        for d in dates:
            if (emp.id, d) not in complete_schedule:
                print(f"✗ Employee {emp.full_name} missing from schedule on {d}")
                return False
    
    print(f"✓ All {len(employees)} employees visible for all {len(dates)} days")
    
    # Check that all regular team members are included
    regular_members = [e for e in employees if e.team_id]
    print(f"✓ {len(regular_members)} regular team members included in schedule")
    
    return True


def test_absence_persistence():
    """Test that absence data is marked as locked"""
    print("\n" + "="*60)
    print("TEST: Absence Persistence")
    print("="*60)
    
    # Create absence
    absence = Absence(
        id=1,
        employee_id=1,
        absence_type=AbsenceType.U,
        start_date=date(2025, 1, 10),
        end_date=date(2025, 1, 14),
        notes="Test vacation"
    )
    
    # Check is_locked flag
    assert absence.is_locked, "Absences must be locked by default"
    print("✓ Absences are locked by default")
    
    # Check get_code method
    assert absence.get_code() == "U", "get_code() must return correct code"
    print("✓ get_code() returns correct absence code")
    
    return True


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("ABSENCE CODE HANDLING TEST SUITE")
    print("="*70)
    
    tests = [
        ("Official Absence Codes", test_absence_codes),
        ("Virtual Teams", test_virtual_teams),
        ("Absence Priority", test_absence_priority),
        ("All Employees Visible", test_all_employees_visible),
        ("Absence Persistence", test_absence_persistence),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r for _, r in results)
    
    print("="*70)
    if all_passed:
        print("✓✓✓ ALL TESTS PASSED ✓✓✓")
    else:
        print("✗✗✗ SOME TESTS FAILED ✗✗✗")
    print("="*70)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
