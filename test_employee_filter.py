"""
Test that only active employees with team assignments are loaded for shift planning.
"""

import sqlite3
import tempfile
import os
from datetime import date
from data_loader import load_from_database


def test_employee_filter():
    """Test that inactive employees and employees without teams are excluded."""
    
    # Create a temporary database
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db') as f:
        db_path = f.name
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE ShiftTypes (
                Id INTEGER PRIMARY KEY,
                Code TEXT NOT NULL,
                Name TEXT NOT NULL,
                StartTime TEXT NOT NULL,
                EndTime TEXT NOT NULL,
                DurationHours REAL NOT NULL,
                ColorCode TEXT,
                IsActive INTEGER NOT NULL DEFAULT 1,
                WeeklyWorkingHours REAL NOT NULL DEFAULT 40.0,
                MinStaffWeekday INTEGER NOT NULL DEFAULT 3,
                MaxStaffWeekday INTEGER NOT NULL DEFAULT 5,
                MinStaffWeekend INTEGER NOT NULL DEFAULT 2,
                MaxStaffWeekend INTEGER NOT NULL DEFAULT 3,
                WorksMonday INTEGER NOT NULL DEFAULT 1,
                WorksTuesday INTEGER NOT NULL DEFAULT 1,
                WorksWednesday INTEGER NOT NULL DEFAULT 1,
                WorksThursday INTEGER NOT NULL DEFAULT 1,
                WorksFriday INTEGER NOT NULL DEFAULT 1,
                WorksSaturday INTEGER NOT NULL DEFAULT 0,
                WorksSunday INTEGER NOT NULL DEFAULT 0,
                MaxConsecutiveDays INTEGER NOT NULL DEFAULT 6
            )
        """)
        
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
                Email TEXT,
                Geburtsdatum TEXT,
                Funktion TEXT,
                IsFerienjobber INTEGER NOT NULL DEFAULT 0,
                IsBrandmeldetechniker INTEGER NOT NULL DEFAULT 0,
                IsBrandschutzbeauftragter INTEGER NOT NULL DEFAULT 0,
                TeamId INTEGER,
                IsActive INTEGER NOT NULL DEFAULT 1
            )
        """)
        
        cursor.execute("""
            CREATE TABLE TeamShiftAssignments (
                Id INTEGER PRIMARY KEY,
                TeamId INTEGER NOT NULL,
                ShiftTypeId INTEGER NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE Absences (
                Id INTEGER PRIMARY KEY,
                EmployeeId INTEGER NOT NULL,
                Type INTEGER NOT NULL,
                StartDate TEXT NOT NULL,
                EndDate TEXT NOT NULL,
                Notes TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE VacationRequests (
                Id INTEGER PRIMARY KEY,
                EmployeeId INTEGER NOT NULL,
                StartDate TEXT NOT NULL,
                EndDate TEXT NOT NULL,
                Status TEXT NOT NULL DEFAULT 'InBearbeitung',
                Notes TEXT
            )
        """)
        
        # Insert test data
        # Shift types
        cursor.execute("""
            INSERT INTO ShiftTypes (Id, Code, Name, StartTime, EndTime, DurationHours, ColorCode)
            VALUES (1, 'F', 'Frühschicht', '05:45', '13:45', 8.0, '#4caf50')
        """)
        cursor.execute("""
            INSERT INTO ShiftTypes (Id, Code, Name, StartTime, EndTime, DurationHours, ColorCode)
            VALUES (2, 'S', 'Spätschicht', '13:45', '21:45', 8.0, '#ff9800')
        """)
        cursor.execute("""
            INSERT INTO ShiftTypes (Id, Code, Name, StartTime, EndTime, DurationHours, ColorCode)
            VALUES (3, 'N', 'Nachtschicht', '21:45', '05:45', 8.0, '#2196f3')
        """)
        
        # Teams
        cursor.execute("""
            INSERT INTO Teams (Id, Name, Description)
            VALUES (1, 'Team Alpha', 'First team')
        """)
        cursor.execute("""
            INSERT INTO Teams (Id, Name, Description)
            VALUES (2, 'Team Beta', 'Second team')
        """)
        
        # Employees
        # Active employee with team - SHOULD BE LOADED
        cursor.execute("""
            INSERT INTO Employees (Id, Vorname, Name, Personalnummer, Email, Geburtsdatum, 
                                  Funktion, TeamId, IsActive)
            VALUES (1, 'Max', 'Müller', 'PN001', 'max@test.de', '1990-01-01', 
                    'Techniker', 1, 1)
        """)
        
        # Active employee with team - SHOULD BE LOADED
        cursor.execute("""
            INSERT INTO Employees (Id, Vorname, Name, Personalnummer, Email, Geburtsdatum,
                                  Funktion, TeamId, IsActive)
            VALUES (2, 'Anna', 'Schmidt', 'PN002', 'anna@test.de', '1991-02-02',
                    'Techniker', 1, 1)
        """)
        
        # Inactive employee with team - SHOULD NOT BE LOADED
        cursor.execute("""
            INSERT INTO Employees (Id, Vorname, Name, Personalnummer, Email, Geburtsdatum,
                                  Funktion, TeamId, IsActive)
            VALUES (3, 'Peter', 'Inactive', 'PN003', 'peter@test.de', '1992-03-03',
                    'Techniker', 1, 0)
        """)
        
        # Active employee without team (like Admin) - SHOULD NOT BE LOADED
        cursor.execute("""
            INSERT INTO Employees (Id, Vorname, Name, Personalnummer, Email, Geburtsdatum,
                                  Funktion, TeamId, IsActive)
            VALUES (4, 'Admin', 'User', 'ADMIN001', 'admin@test.de', '1990-01-01',
                    'Administrator', NULL, 1)
        """)
        
        # Active employee with team - SHOULD BE LOADED
        cursor.execute("""
            INSERT INTO Employees (Id, Vorname, Name, Personalnummer, Email, Geburtsdatum,
                                  Funktion, TeamId, IsActive)
            VALUES (5, 'Julia', 'Becker', 'PN005', 'julia@test.de', '1993-05-05',
                    'Techniker', 2, 1)
        """)
        
        # Team shift assignments
        cursor.execute("INSERT INTO TeamShiftAssignments (TeamId, ShiftTypeId) VALUES (1, 1)")
        cursor.execute("INSERT INTO TeamShiftAssignments (TeamId, ShiftTypeId) VALUES (1, 2)")
        cursor.execute("INSERT INTO TeamShiftAssignments (TeamId, ShiftTypeId) VALUES (1, 3)")
        cursor.execute("INSERT INTO TeamShiftAssignments (TeamId, ShiftTypeId) VALUES (2, 1)")
        cursor.execute("INSERT INTO TeamShiftAssignments (TeamId, ShiftTypeId) VALUES (2, 2)")
        cursor.execute("INSERT INTO TeamShiftAssignments (TeamId, ShiftTypeId) VALUES (2, 3)")
        
        conn.commit()
        conn.close()
        
        # Load data
        employees, teams, absences, shift_types = load_from_database(db_path)
        
        # Verify results
        print("\n=== Test Results ===")
        print(f"Total employees loaded: {len(employees)}")
        print(f"Expected: 3 (only active employees with teams)")
        
        # Check that we only loaded the correct employees
        employee_ids = {emp.id for emp in employees}
        expected_ids = {1, 2, 5}  # Only Max, Anna, and Julia
        
        print(f"\nLoaded employee IDs: {sorted(employee_ids)}")
        print(f"Expected IDs: {sorted(expected_ids)}")
        
        # Verify team assignments
        print(f"\nTeam Alpha members: {len(teams[0].employees)}")
        print(f"Team Beta members: {len(teams[1].employees)}")
        
        # Assertions
        assert len(employees) == 3, f"Expected 3 employees, got {len(employees)}"
        assert employee_ids == expected_ids, f"Employee IDs mismatch: {employee_ids} vs {expected_ids}"
        assert len(teams[0].employees) == 2, f"Team Alpha should have 2 members, got {len(teams[0].employees)}"
        assert len(teams[1].employees) == 1, f"Team Beta should have 1 member, got {len(teams[1].employees)}"
        
        # Verify that Admin (no team) and Peter (inactive) are NOT loaded
        assert 3 not in employee_ids, "Inactive employee should not be loaded"
        assert 4 not in employee_ids, "Employee without team should not be loaded"
        
        print("\n✓ All tests passed!")
        print("✓ Only active employees with team assignments are loaded")
        print("✓ Inactive employees are excluded")
        print("✓ Employees without teams are excluded")
        
    finally:
        # Clean up
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    test_employee_filter()
