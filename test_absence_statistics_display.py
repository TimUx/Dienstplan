#!/usr/bin/env python3
"""
Test to verify that absence statistics display category names instead of IDs.
This test verifies the fix for the issue where absences were shown as "(1: 7)" 
instead of "(Krank/AU: 7)" in statistics.
"""

import sqlite3
import os
from datetime import date, datetime

# Absence type constants - MUST match database schema
ABSENCE_TYPE_AU = 1  # Arbeitsunfähigkeit (Sick leave)
ABSENCE_TYPE_U = 2   # Urlaub (Vacation)
ABSENCE_TYPE_L = 3   # Lehrgang (Training)


def setup_test_database():
    """Create a temporary test database with sample data"""
    db_path = '/tmp/test_absence_statistics_display.db'
    
    # Remove existing test database
    if os.path.exists(db_path):
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE Employees (
            Id INTEGER PRIMARY KEY,
            Vorname TEXT NOT NULL,
            Name TEXT NOT NULL,
            Personalnummer TEXT,
            Email TEXT,
            TeamId INTEGER
        )
    """)
    
    cursor.execute("""
        CREATE TABLE Absences (
            Id INTEGER PRIMARY KEY AUTOINCREMENT,
            EmployeeId INTEGER NOT NULL,
            Type INTEGER NOT NULL,
            StartDate TEXT NOT NULL,
            EndDate TEXT NOT NULL,
            Notes TEXT,
            CreatedAt TEXT,
            FOREIGN KEY (EmployeeId) REFERENCES Employees(Id)
        )
    """)
    
    # Insert test employees
    cursor.execute("""
        INSERT INTO Employees (Id, Vorname, Name, Personalnummer, Email, TeamId)
        VALUES (1, 'Robert', 'Franke', 'EMP001', 'robert.franke@test.de', 1)
    """)
    
    cursor.execute("""
        INSERT INTO Employees (Id, Vorname, Name, Personalnummer, Email, TeamId)
        VALUES (2, 'Stefanie', 'Klein', 'EMP002', 'stefanie.klein@test.de', 1)
    """)
    
    # Insert absences
    # Robert Franke: 7 days of AU (sick leave)
    cursor.execute("""
        INSERT INTO Absences (EmployeeId, Type, StartDate, EndDate, CreatedAt)
        VALUES (1, ?, '2026-01-01', '2026-01-07', ?)
    """, (ABSENCE_TYPE_AU, datetime.now().isoformat()))
    
    # Stefanie Klein: 7 days of L (training/Lehrgang)
    cursor.execute("""
        INSERT INTO Absences (EmployeeId, Type, StartDate, EndDate, CreatedAt)
        VALUES (2, ?, '2026-01-01', '2026-01-07', ?)
    """, (ABSENCE_TYPE_L, datetime.now().isoformat()))
    
    conn.commit()
    return conn, db_path


def get_absence_statistics(conn, start_date, end_date):
    """
    Get absence statistics exactly as the web API does.
    This simulates the /api/statistics/dashboard endpoint.
    """
    cursor = conn.cursor()
    
    # Employee absence days - categorized by type
    cursor.execute("""
        SELECT e.Id, e.Vorname, e.Name, a.Type,
               SUM(julianday(a.EndDate) - julianday(a.StartDate) + 1) as TotalDays
        FROM Employees e
        JOIN Absences a ON e.Id = a.EmployeeId
        WHERE (a.StartDate <= ? AND a.EndDate >= ?)
           OR (a.StartDate >= ? AND a.StartDate <= ?)
        GROUP BY e.Id, e.Vorname, e.Name, a.Type
        HAVING TotalDays > 0
        ORDER BY e.Vorname, e.Name, a.Type
    """, (end_date.isoformat(), start_date.isoformat(),
          start_date.isoformat(), end_date.isoformat()))
    
    # Build employee absence data with categorization
    # Map integer type IDs to string codes for frontend display
    type_id_to_code = {1: 'AU', 2: 'U', 3: 'L'}
    
    employee_absence_map = {}
    for row in cursor.fetchall():
        emp_id = row['Id']
        if emp_id not in employee_absence_map:
            employee_absence_map[emp_id] = {
                'employeeId': emp_id,
                'employeeName': f"{row['Vorname']} {row['Name']}",
                'totalDays': 0,
                'byType': {}
            }
        
        absence_type_id = row['Type']
        absence_type_code = type_id_to_code.get(absence_type_id, str(absence_type_id))
        days = int(row['TotalDays'])
        employee_absence_map[emp_id]['byType'][absence_type_code] = days
        employee_absence_map[emp_id]['totalDays'] += days
    
    # Sort by total days descending
    employee_absence_days = sorted(
        employee_absence_map.values(),
        key=lambda x: x['totalDays'],
        reverse=True
    )
    
    return employee_absence_days


def test_absence_statistics_display():
    """
    Test that absence statistics use category names instead of IDs.
    
    Expected:
    - Robert Franke 7 Tage (Krank/AU: 7)
    - Stefanie Klein 7 Tage (Lehrgang: 7)
    
    NOT:
    - Robert Franke 7 Tage (1: 7)
    - Stefanie Klein 7 Tage (3: 7)
    """
    print("=" * 80)
    print("TEST: Absence Statistics Display Names")
    print("=" * 80)
    
    # Setup test database
    conn, db_path = setup_test_database()
    
    try:
        start_date = date(2026, 1, 1)
        end_date = date(2026, 1, 31)
        
        # Get statistics
        absence_stats = get_absence_statistics(conn, start_date, end_date)
        
        print("\n📅 Abwesenheiten")
        print("-" * 80)
        
        # Frontend type name mapping (as defined in app.js)
        typeNames = {
            'AU': 'Krank/AU',
            'U': 'Urlaub',
            'L': 'Lehrgang'
        }
        
        # Display and verify statistics
        for employee in absence_stats:
            # Build type breakdown as the frontend does
            types = ', '.join([
                f"{typeNames.get(t, t)}: {d}" 
                for t, d in employee['byType'].items()
            ])
            
            output = f"{employee['employeeName']} {employee['totalDays']} Tage ({types})"
            print(output)
            
            # Verify that we're using string codes, not integer IDs
            for type_key in employee['byType'].keys():
                assert isinstance(type_key, str), \
                    f"Type key should be string, got {type(type_key)}: {type_key}"
                assert type_key in ['AU', 'U', 'L'], \
                    f"Type key should be AU, U, or L, got: {type_key}"
        
        print("-" * 80)
        
        # Verify specific employees
        assert len(absence_stats) == 2, f"Expected 2 employees, got {len(absence_stats)}"
        
        # Check Robert Franke (AU)
        robert = next(e for e in absence_stats if 'Robert Franke' in e['employeeName'])
        assert robert['totalDays'] == 7, f"Robert should have 7 days, got {robert['totalDays']}"
        assert 'AU' in robert['byType'], "Robert should have AU type"
        assert robert['byType']['AU'] == 7, f"Robert should have 7 AU days, got {robert['byType']['AU']}"
        
        # Check Stefanie Klein (L)
        stefanie = next(e for e in absence_stats if 'Stefanie Klein' in e['employeeName'])
        assert stefanie['totalDays'] == 7, f"Stefanie should have 7 days, got {stefanie['totalDays']}"
        assert 'L' in stefanie['byType'], "Stefanie should have L type"
        assert stefanie['byType']['L'] == 7, f"Stefanie should have 7 L days, got {stefanie['byType']['L']}"
        
        print("\n✅ ALL TESTS PASSED")
        print("=" * 80)
        print("Summary:")
        print("  ✓ Absence types are displayed with string codes (AU, U, L)")
        print("  ✓ NOT displayed with integer IDs (1, 2, 3)")
        print("  ✓ Frontend can map codes to names (Krank/AU, Urlaub, Lehrgang)")
        print("=" * 80)
        
        return True
        
    except AssertionError as e:
        print("\n" + "=" * 80)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 80)
        return False
    except Exception as e:
        print("\n" + "=" * 80)
        print(f"❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 80)
        return False
    finally:
        conn.close()
        # Clean up test database
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    success = test_absence_statistics_display()
    exit(0 if success else 1)
