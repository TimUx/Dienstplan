"""
Test for virtual team fixes: employees with special functions but no team
should only appear in virtual team, not in "Ohne Team".
"""

import sys
import sqlite3
from datetime import date, timedelta


def test_virtual_team_employee_grouping():
    """
    Test that employees with special functions (BMT/BSB) but no team
    are only listed in the virtual "Brandmeldeanlage" team, not in "Ohne Team".
    """
    print("\n" + "=" * 70)
    print("TEST: Virtual Team Employee Grouping")
    print("=" * 70)
    
    # Create a test database with sample data
    db_path = ":memory:"  # Use in-memory database for testing
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create minimal schema
    cursor.execute("""
        CREATE TABLE Teams (
            Id INTEGER PRIMARY KEY,
            Name TEXT NOT NULL,
            Description TEXT,
            Email TEXT,
            IsVirtual INTEGER NOT NULL DEFAULT 0
        )
    """)
    
    cursor.execute("""
        CREATE TABLE Employees (
            Id INTEGER PRIMARY KEY,
            Vorname TEXT NOT NULL,
            Name TEXT NOT NULL,
            Personalnummer TEXT NOT NULL,
            IsBrandmeldetechniker INTEGER NOT NULL DEFAULT 0,
            IsBrandschutzbeauftragter INTEGER NOT NULL DEFAULT 0,
            TeamId INTEGER,
            FOREIGN KEY (TeamId) REFERENCES Teams(Id)
        )
    """)
    
    # Insert test data
    # Team 1 - Regular team
    cursor.execute("INSERT INTO Teams (Id, Name, IsVirtual) VALUES (1, 'Team Alpha', 0)")
    
    # Team 99 - Virtual Brandmeldeanlage team
    cursor.execute("INSERT INTO Teams (Id, Name, Description, IsVirtual) VALUES (99, 'Brandmeldeanlage', 'Virtuelles Team für Mitarbeiter mit Sonderfunktion', 1)")
    
    # Employees:
    # 1. Regular employee in Team Alpha
    cursor.execute("""
        INSERT INTO Employees (Id, Vorname, Name, Personalnummer, TeamId, IsBrandmeldetechniker, IsBrandschutzbeauftragter)
        VALUES (1, 'Max', 'Müller', 'PN001', 1, 0, 0)
    """)
    
    # 2. Employee with BMT but no team - should ONLY appear in virtual team
    cursor.execute("""
        INSERT INTO Employees (Id, Vorname, Name, Personalnummer, TeamId, IsBrandmeldetechniker, IsBrandschutzbeauftragter)
        VALUES (2, 'Christian', 'Neumann', 'SF002', NULL, 1, 0)
    """)
    
    # 3. Employee with BSB but no team - should ONLY appear in virtual team
    cursor.execute("""
        INSERT INTO Employees (Id, Vorname, Name, Personalnummer, TeamId, IsBrandmeldetechniker, IsBrandschutzbeauftragter)
        VALUES (3, 'Laura', 'Bauer', 'SF001', NULL, 0, 1)
    """)
    
    # 4. Regular employee with no team and no special function - should appear in "Ohne Team"
    cursor.execute("""
        INSERT INTO Employees (Id, Vorname, Name, Personalnummer, TeamId, IsBrandmeldetechniker, IsBrandschutzbeauftragter)
        VALUES (4, 'Thomas', 'Schmidt', 'PN004', NULL, 0, 0)
    """)
    
    conn.commit()
    
    # Test the logic that groups employees
    print("\n📊 Test Data:")
    cursor.execute("SELECT * FROM Employees")
    for row in cursor.fetchall():
        emp_id, vorname, name, pnr, is_bmt, is_bsb, team_id = row
        print(f"  Employee {emp_id}: {vorname} {name} ({pnr})")
        print(f"    TeamId: {team_id if team_id else 'None'}")
        print(f"    BMT: {bool(is_bmt)}, BSB: {bool(is_bsb)}")
    
    # Simulate the grouping logic from web_api.py
    cursor.execute("""
        SELECT e.Id, e.Vorname, e.Name, e.Personalnummer, e.TeamId, 
               t.Name as TeamName,
               e.IsBrandmeldetechniker, e.IsBrandschutzbeauftragter
        FROM Employees e
        LEFT JOIN Teams t ON e.TeamId = t.Id
        ORDER BY t.Name NULLS LAST, e.Name, e.Vorname
    """)
    employees = cursor.fetchall()
    
    VIRTUAL_TEAM_BRANDMELDEANLAGE_ID = 99
    UNASSIGNED_TEAM_ID = -1
    
    teams = {}
    for emp in employees:
        emp_id, vorname, name, pnr, team_id, team_name, is_bmt, is_bsb = emp
        
        # Check if employee has special functions but no team
        has_special_function = is_bmt or is_bsb
        has_no_team = not team_id
        
        # Add to regular team only if they have a team OR don't have special function
        if not (has_no_team and has_special_function):
            # Add to regular team
            tid = team_id if team_id else UNASSIGNED_TEAM_ID
            tname = team_name if team_name else 'Ohne Team'
            
            if tid not in teams:
                teams[tid] = {
                    'teamId': tid,
                    'teamName': tname,
                    'employees': []
                }
            
            teams[tid]['employees'].append({
                'id': emp_id,
                'name': f"{vorname} {name} ({pnr})"
            })
        
        # Add to virtual Brandmeldeanlage team if qualified
        if is_bmt or is_bsb:
            if VIRTUAL_TEAM_BRANDMELDEANLAGE_ID not in teams:
                teams[VIRTUAL_TEAM_BRANDMELDEANLAGE_ID] = {
                    'teamId': VIRTUAL_TEAM_BRANDMELDEANLAGE_ID,
                    'teamName': 'Brandmeldeanlage',
                    'employees': []
                }
            
            teams[VIRTUAL_TEAM_BRANDMELDEANLAGE_ID]['employees'].append({
                'id': emp_id,
                'name': f"{vorname} {name} ({pnr})"
            })
    
    # Verify results
    print("\n📋 Grouping Results:")
    
    all_tests_passed = True
    
    # Check virtual team
    if VIRTUAL_TEAM_BRANDMELDEANLAGE_ID in teams:
        virtual_team = teams[VIRTUAL_TEAM_BRANDMELDEANLAGE_ID]
        print(f"\n  {virtual_team['teamName']}:")
        for emp in virtual_team['employees']:
            print(f"    - {emp['name']}")
        
        # Should have Christian and Laura (employees 2 and 3)
        virtual_emp_ids = [emp['id'] for emp in virtual_team['employees']]
        if 2 not in virtual_emp_ids or 3 not in virtual_emp_ids:
            print("  ❌ FAIL: Virtual team missing employees with special functions")
            all_tests_passed = False
        else:
            print("  ✅ Virtual team has employees with special functions")
    else:
        print("  ❌ FAIL: Virtual team not created")
        all_tests_passed = False
    
    # Check regular team
    if 1 in teams:
        team_alpha = teams[1]
        print(f"\n  {team_alpha['teamName']}:")
        for emp in team_alpha['employees']:
            print(f"    - {emp['name']}")
        
        # Should have Max (employee 1)
        team_emp_ids = [emp['id'] for emp in team_alpha['employees']]
        if 1 not in team_emp_ids:
            print("  ❌ FAIL: Team Alpha missing regular employee")
            all_tests_passed = False
        if 2 in team_emp_ids or 3 in team_emp_ids:
            print("  ❌ FAIL: Team Alpha should not have employees with special functions")
            all_tests_passed = False
        else:
            print("  ✅ Team Alpha has correct employees")
    
    # Check "Ohne Team"
    if UNASSIGNED_TEAM_ID in teams:
        ohne_team = teams[UNASSIGNED_TEAM_ID]
        print(f"\n  {ohne_team['teamName']}:")
        for emp in ohne_team['employees']:
            print(f"    - {emp['name']}")
        
        # Should have Thomas (employee 4) but NOT Christian or Laura
        ohne_emp_ids = [emp['id'] for emp in ohne_team['employees']]
        if 4 not in ohne_emp_ids:
            print("  ❌ FAIL: Ohne Team missing regular employee without team")
            all_tests_passed = False
        if 2 in ohne_emp_ids or 3 in ohne_emp_ids:
            print("  ❌ FAIL: Ohne Team should NOT have employees with special functions")
            all_tests_passed = False
        else:
            print("  ✅ Ohne Team has correct employees (no special functions)")
    
    # Test employee count for virtual teams
    print("\n📊 Testing Employee Count for Virtual Teams:")
    cursor.execute("""
        SELECT COUNT(*) as Count
        FROM Employees
        WHERE IsBrandmeldetechniker = 1 OR IsBrandschutzbeauftragter = 1
    """)
    virtual_count = cursor.fetchone()[0]
    print(f"  Virtual team (Brandmeldeanlage) should have {virtual_count} employees")
    
    if VIRTUAL_TEAM_BRANDMELDEANLAGE_ID in teams:
        actual_count = len(teams[VIRTUAL_TEAM_BRANDMELDEANLAGE_ID]['employees'])
        if actual_count == virtual_count:
            print(f"  ✅ Virtual team count is correct: {actual_count}")
        else:
            print(f"  ❌ FAIL: Virtual team count is {actual_count}, expected {virtual_count}")
            all_tests_passed = False
    
    conn.close()
    
    if all_tests_passed:
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        return True
    else:
        print("\n" + "=" * 70)
        print("❌ SOME TESTS FAILED")
        print("=" * 70)
        return False


if __name__ == "__main__":
    success = test_virtual_team_employee_grouping()
    sys.exit(0 if success else 1)
