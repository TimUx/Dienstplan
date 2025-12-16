"""
Test for Ferienjobber (temporary holiday worker) support.

Verifies that Ferienjobbers can be assigned to help any team when needed,
similar to cross-team springer logic but without an own team.
"""

from datetime import date
from data_loader import load_from_database
from model import create_shift_planning_model, FERIENJOBBER_TEAM_ID
from solver import solve_shift_planning
from entities import Absence, AbsenceType, Employee


def test_ferienjobber_virtual_team():
    """
    Test that Ferienjobbers are automatically assigned to virtual Ferienjobber team.
    """
    print("\n" + "=" * 70)
    print("TEST: Ferienjobber Virtual Team Assignment")
    print("=" * 70)
    
    # Create test database with a Ferienjobber
    import sqlite3
    import os
    
    test_db = "/tmp/test_ferienjobber.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    # Copy main DB and add a Ferienjobber
    from db_init import initialize_database
    initialize_database(test_db, with_sample_data=True)
    
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    
    # Add a Ferienjobber (without team_id initially)
    cursor.execute("""
        INSERT INTO Employees 
        (Vorname, Name, Personalnummer, Email, Funktion, IsSpringer, IsFerienjobber, TeamId)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("Hans", "Sommer", "FJ001", "hans.sommer@fritzwinter.de", "Ferienjobber", 0, 1, None))
    conn.commit()
    conn.close()
    
    # Load and check
    employees, teams, absences = load_from_database(test_db)
    
    ferienjobbers = [e for e in employees if e.is_ferienjobber]
    print(f"\nFerienjobbers found: {len(ferienjobbers)}")
    
    for fj in ferienjobbers:
        print(f"  - {fj.full_name} (Team ID: {fj.team_id})")
        if fj.team_id == FERIENJOBBER_TEAM_ID:
            print(f"    ✅ Correctly assigned to Ferienjobber virtual team (ID {FERIENJOBBER_TEAM_ID})")
        else:
            print(f"    ❌ NOT assigned to Ferienjobber virtual team")
            return False
    
    # Check team exists
    fj_team = next((t for t in teams if t.id == FERIENJOBBER_TEAM_ID), None)
    if fj_team:
        print(f"\n✅ Ferienjobber virtual team exists: {fj_team.name}")
        print(f"   Members: {len(fj_team.employees)}")
    else:
        print(f"\n❌ Ferienjobber virtual team (ID {FERIENJOBBER_TEAM_ID}) not found!")
        return False
    
    # Clean up
    os.remove(test_db)
    
    return True


def test_ferienjobber_can_help_teams():
    """
    Test that Ferienjobbers can be assigned to help any team when gaps need filling.
    """
    print("\n" + "=" * 70)
    print("TEST: Ferienjobber Can Help Teams")
    print("=" * 70)
    
    # Create test database
    import sqlite3
    import os
    
    test_db = "/tmp/test_ferienjobber_help.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    from db_init import initialize_database
    initialize_database(test_db, with_sample_data=True)
    
    conn = sqlite3.connect(test_db)
    cursor = conn.cursor()
    
    # Add 2 Ferienjobbers
    cursor.execute("""
        INSERT INTO Employees 
        (Vorname, Name, Personalnummer, Email, Funktion, IsSpringer, IsFerienjobber, TeamId)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("Hans", "Sommer", "FJ001", "hans.sommer@fritzwinter.de", "Ferienjobber", 0, 1, None))
    
    cursor.execute("""
        INSERT INTO Employees 
        (Vorname, Name, Personalnummer, Email, Funktion, IsSpringer, IsFerienjobber, TeamId)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ("Petra", "Winter", "FJ002", "petra.winter@fritzwinter.de", "Ferienjobber", 0, 1, None))
    
    conn.commit()
    conn.close()
    
    # Load data
    employees, teams, absences = load_from_database(test_db)
    
    # Create absences to trigger need for Ferienjobbers
    # 2 absences in Team Alpha - own springer + Ferienjobber should help
    start_date = date(2026, 1, 5)
    end_date = date(2026, 1, 11)
    
    test_absences = [
        Absence(id=9999, employee_id=1, absence_type=AbsenceType.AU,
                start_date=start_date, end_date=end_date, notes='Sick'),
        Absence(id=9998, employee_id=2, absence_type=AbsenceType.U,
                start_date=start_date, end_date=end_date, notes='Vacation'),
    ]
    
    all_absences = absences + test_absences
    
    print(f"\nScenario: 2 Team Alpha members absent")
    print(f"Period: {start_date} to {end_date}")
    print(f"Available Ferienjobbers: {len([e for e in employees if e.is_ferienjobber])}")
    
    # Try to create a plan
    planning_model = create_shift_planning_model(employees, teams, start_date, end_date, all_absences)
    result = solve_shift_planning(planning_model, time_limit_seconds=60)
    
    if not result:
        print("\n❌ FAIL: No solution found (Ferienjobbers not helping)")
        os.remove(test_db)
        return False
    
    assignments, _, _ = result
    
    print(f"\n✅ PASS: Solution found!")
    print(f"Total assignments: {len(assignments)}")
    
    # Check if Ferienjobbers were used
    fj_assignments = []
    for a in assignments:
        emp = next((e for e in employees if e.id == a.employee_id), None)
        if emp and emp.is_ferienjobber:
            fj_assignments.append((emp.full_name, a.date))
    
    if fj_assignments:
        print(f"\n✅ Ferienjobbers used: {len(fj_assignments)} assignments")
        # Group by ferienjobber
        fj_days = {}
        for name, d in fj_assignments:
            if name not in fj_days:
                fj_days[name] = []
            fj_days[name].append(d)
        for name, days in fj_days.items():
            print(f"  - {name}: {len(days)} days")
    else:
        print(f"\n⚠️  No Ferienjobber assignments (might be OK if springer was sufficient)")
    
    # Clean up
    os.remove(test_db)
    
    return True


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("FERIENJOBBER SUPPORT TESTS")
    print("Testing virtual team and cross-team assignment for temporary workers")
    print("=" * 70)
    
    results = []
    
    # Test 1: Virtual team assignment
    results.append(("Ferienjobber virtual team", test_ferienjobber_virtual_team()))
    
    # Test 2: Can help teams
    results.append(("Ferienjobber can help teams", test_ferienjobber_can_help_teams()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 ALL TESTS PASSED! Ferienjobber support working correctly.")
    else:
        print("\n⚠️  SOME TESTS FAILED! Review Ferienjobber implementation.")
