#!/usr/bin/env python3
"""
Test January 2026 shift planning with the new soft constraint system.

Configuration:
- 3 teams × 5 employees (15 total)
- 48h/week target  
- January 2026: Thu Jan 1 - Sat Jan 31 (31 days)
- Extended to complete weeks: Mon Dec 29, 2025 - Sun Feb 1, 2026 (35 days = 5 weeks)

Changes implemented:
- ✅ Hard 192h minimum REMOVED - now only soft proportional target
- ✅ Hard weekly maximum REMOVED - allows flexible week-to-week variation
- ✅ Max staffing now SOFT - can be exceeded with penalty
- ✅ Rest time exception for Sunday→Monday team rotation boundaries
- ✅ Violation tracking system with German reports

Expected: FEASIBLE with violation tracking
"""

import sqlite3
from datetime import date, timedelta

def setup_test_database():
    """Create test database with 3 teams × 5 employees."""
    db_path = "test_january_soft.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables (simplified schema)
    cursor.executescript("""
        DROP TABLE IF EXISTS ShiftAssignments;
        DROP TABLE IF EXISTS Absences;
        DROP TABLE IF EXISTS Employees;
        DROP TABLE IF EXISTS Teams;
        DROP TABLE IF EXISTS ShiftTypes;
        DROP TABLE IF EXISTS GlobalSettings;
        
        CREATE TABLE ShiftTypes (
            Id INTEGER PRIMARY KEY,
            Name TEXT NOT NULL,
            StartTime TEXT,
            EndTime TEXT,
            MinWorkers INTEGER DEFAULT 3,
            MaxWorkers INTEGER DEFAULT 10,
            WeeklyWorkingHours REAL DEFAULT 48.0
        );
        
        CREATE TABLE Teams (
            Id INTEGER PRIMARY KEY,
            Name TEXT NOT NULL,
            Description TEXT,
            Email TEXT,
            IsVirtual INTEGER DEFAULT 0
        );
        
        CREATE TABLE Employees (
            Id INTEGER PRIMARY KEY,
            Vorname TEXT NOT NULL,
            Name TEXT NOT NULL,
            Personalnummer TEXT UNIQUE,
            Email TEXT,
            TeamId INTEGER,
            IsTdQualified INTEGER DEFAULT 0,
            IsSpringer INTEGER DEFAULT 0,
            IsActive INTEGER DEFAULT 1,
            FOREIGN KEY (TeamId) REFERENCES Teams(Id)
        );
        
        CREATE TABLE Absences (
            Id INTEGER PRIMARY KEY,
            EmployeeId INTEGER,
            StartDate TEXT,
            EndDate TEXT,
            Reason TEXT,
            FOREIGN KEY (EmployeeId) REFERENCES Employees(Id)
        );
        
        CREATE TABLE ShiftAssignments (
            Id INTEGER PRIMARY KEY,
            EmployeeId INTEGER,
            ShiftTypeId INTEGER,
            Date TEXT,
            FOREIGN KEY (EmployeeId) REFERENCES Employees(Id),
            FOREIGN KEY (ShiftTypeId) REFERENCES ShiftTypes(Id)
        );
        
        CREATE TABLE GlobalSettings (
            Id INTEGER PRIMARY KEY,
            SettingName TEXT UNIQUE,
            SettingValue TEXT
        );
    """)
    
    # Insert shift types with SOFT max staffing
    cursor.executescript("""
        INSERT INTO ShiftTypes (Name, StartTime, EndTime, MinWorkers, MaxWorkers, WeeklyWorkingHours)
        VALUES 
            ('F', '06:00', '14:00', 4, 10, 48.0),
            ('S', '14:00', '22:00', 3, 10, 48.0),
            ('N', '22:00', '06:00', 3, 10, 48.0);
    """)
    
    # Insert teams
    teams_data = [
        ("Team Alpha", "First shift team", "team-alpha@test.com"),
        ("Team Beta", "Second shift team", "team-beta@test.com"),
        ("Team Gamma", "Third shift team", "team-gamma@test.com")
    ]
    
    for name, desc, email in teams_data:
        cursor.execute(
            "INSERT INTO Teams (Name, Description, Email) VALUES (?, ?, ?)",
            (name, desc, email)
        )
    
    # Insert employees (5 per team = 15 total)
    employees_data = [
        # Team 1
        ("Max", "Müller", "E101", "max.mueller@test.com", 1),
        ("Anna", "Schmidt", "E102", "anna.schmidt@test.com", 1),
        ("Peter", "Weber", "E103", "peter.weber@test.com", 1),
        ("Lisa", "Meyer", "E104", "lisa.meyer@test.com", 1),
        ("Tom", "Wagner", "E105", "tom.wagner@test.com", 1),
        # Team 2
        ("Julia", "Becker", "E201", "julia.becker@test.com", 2),
        ("Michael", "Schulz", "E202", "michael.schulz@test.com", 2),
        ("Sarah", "Hoffmann", "E203", "sarah.hoffmann@test.com", 2),
        ("Daniel", "Koch", "E204", "daniel.koch@test.com", 2),
        ("Laura", "Bauer", "E205", "laura.bauer@test.com", 2),
        # Team 3
        ("Markus", "Richter", "E301", "markus.richter@test.com", 3),
        ("Stefanie", "Klein", "E302", "stefanie.klein@test.com", 3),
        ("Andreas", "Wolf", "E303", "andreas.wolf@test.com", 3),
        ("Nicole", "Schröder", "E304", "nicole.schroeder@test.com", 3),
        ("Christian", "Neumann", "E305", "christian.neumann@test.com", 3),
    ]
    
    for vorname, name, persnr, email, team_id in employees_data:
        cursor.execute("""
            INSERT INTO Employees (Vorname, Name, Personalnummer, Email, TeamId, IsActive)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (vorname, name, persnr, email, team_id))
    
    # Insert global settings
    cursor.execute("""
        INSERT INTO GlobalSettings (SettingName, SettingValue)
        VALUES ('MAXIMUM_CONSECUTIVE_SHIFTS_WEEKS', '4')
    """)
    
    conn.commit()
    conn.close()
    return db_path

def run_test():
    """Run the test."""
    from data_loader import load_from_database
    from solver import solve_shift_planning
    
    print("=" * 80)
    print("TEST: Januar 2026 mit Soft Constraints System")
    print("=" * 80)
    
    # Setup test database
    print("\n📦 Erstelle Test-Datenbank...")
    db_path = setup_test_database()
    print(f"✓ Datenbank erstellt: {db_path}")
    
    # Load data
    print("\n📊 Lade Daten...")
    employees, teams, absences, shift_types = load_from_database(db_path)
    print(f"  Mitarbeiter: {len(employees)}")
    print(f"  Teams: {len(teams)}")
    print(f"  Schichttypen: {len(shift_types)}")
    
    # January 2026 dates
    start_date = date(2026, 1, 1)  # Thursday
    end_date = date(2026, 1, 31)   # Saturday
    
    # Extend to complete weeks
    start_weekday = start_date.weekday()
    extended_start = start_date - timedelta(days=start_weekday) if start_weekday != 0 else start_date
    
    end_weekday = end_date.weekday()
    extended_end = end_date + timedelta(days=(6 - end_weekday)) if end_weekday != 6 else end_date
    
    days = (extended_end - extended_start).days + 1
    weeks = days / 7
    
    print(f"\n📅 Planungszeitraum:")
    print(f"  Monat:      {start_date} bis {end_date} (31 Tage)")
    print(f"  Erweitert:  {extended_start} bis {extended_end} ({days} Tage = {weeks:.1f} Wochen)")
    
    # Calculate target hours
    target_hours = 48 / 7 * days
    print(f"\n🎯 Zielstunden:")
    print(f"  Berechnung: 48h/7 × {days} Tage = {target_hours:.1f}h pro Mitarbeiter")
    print(f"  ✅ SOFT: Ziel wird angestrebt")
    print(f"  ❌ ENTFERNT: Keine harte 192h Untergrenze")
    print(f"  ❌ ENTFERNT: Keine harte Wochenstunden-Obergrenze")
    
    print(f"\n🔧 Aktive Constraint-Hierarchie:")
    print(f"  HART (kann nicht verletzt werden):")
    print(f"    - Team-Rotation F→N→S")
    print(f"    - Mindestbesetzung (F≥4, S≥3, N≥3)")
    print(f"    - 11h Ruhezeit (AUSSER Sonntag→Montag)")
    print(f"  WEICH (kann verletzt werden mit Penalty):")
    print(f"    - Zielstunden {target_hours:.0f}h (Gewicht 1x)")
    print(f"    - Max-Besetzung ≤10 (Gewicht 5x bei Überschreitung)")
    print(f"    - Block-Scheduling (Bonus-Maximierung)")
    
    # Run solver
    print(f"\n🔍 Starte Solver...")
    result = solve_shift_planning(
        db_path=db_path,
        start_date=extended_start,
        end_date=extended_end,
        solver_timeout_seconds=180
    )
    
    print(f"\n{'='*80}")
    print(f"ERGEBNIS")
    print(f"{'='*80}")
    
    if result.get('status') in ['FEASIBLE', 'OPTIMAL']:
        print(f"✅ STATUS: {result['status']}")
        print(f"✅ Lösung gefunden mit Soft Constraints!")
        
        # Analyze results
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT e.Id, e.Vorname, e.Name, COUNT(*) * 8 as Hours
            FROM ShiftAssignments sa
            JOIN Employees e ON sa.EmployeeId = e.Id
            WHERE sa.Date BETWEEN ? AND ?
            GROUP BY e.Id, e.Vorname, e.Name
            ORDER BY Hours
        """, (extended_start.isoformat(), extended_end.isoformat()))
        
        results = cursor.fetchall()
        
        if results:
            print(f"\n👤 Arbeitsstunden pro Mitarbeiter:")
            hours_list = [r[3] for r in results]
            min_h = min(hours_list)
            max_h = max(hours_list)
            avg_h = sum(hours_list) / len(hours_list)
            
            print(f"  Minimum:      {min_h}h")
            print(f"  Maximum:      {max_h}h")
            print(f"  Durchschnitt: {avg_h:.1f}h")
            print(f"  Ziel:         {target_hours:.0f}h")
            print(f"  Abweichung:   {avg_h - target_hours:+.1f}h")
            
            below_192 = sum(1 for h in hours_list if h < 192)
            if below_192 > 0:
                print(f"\n  ℹ️ {below_192} Mitarbeiter unter 192h")
                print(f"     (Alte harte Grenze - jetzt als Soft erlaubt!)")
            
            # Show distribution
            print(f"\n📊 Stundenverteilung:")
            for emp_id, vorname, name, hours in results:
                diff = hours - target_hours
                marker = "✓" if abs(diff) < 10 else "⚠" if abs(diff) < 20 else "❌"
                print(f"  {marker} {vorname} {name}: {hours}h ({diff:+.0f}h vom Ziel)")
        
        # Check violations
        if 'violations' in result and result['violations']:
            print(f"\n⚠️ Violations protokolliert:")
            viol = result['violations']
            if hasattr(viol, 'get_summary'):
                summary = viol.get_summary()
                print(f"\n{summary.get('message', 'Violations vorhanden')}")
                print(f"Gesamt: {summary.get('total', 0)}")
                
                if summary.get('by_category'):
                    print(f"\nNach Kategorie:")
                    for cat, count in summary['by_category'].items():
                        print(f"  - {cat}: {count}")
                
                if summary.get('warnings'):
                    print(f"\nWarnungen (erste 3):")
                    for w in summary['warnings'][:3]:
                        print(f"  ⚠️ {w}")
        
        conn.close()
        
        print(f"\n{'='*80}")
        print(f"✅ TEST ERFOLGREICH!")
        print(f"   Monatliche Planung ist mit Soft Constraints möglich!")
        print(f"{'='*80}")
        return True
        
    else:
        print(f"❌ STATUS: {result.get('status', 'UNKNOWN')}")
        print(f"❌ Keine Lösung gefunden")
        
        if 'error' in result:
            print(f"\nFehler: {result['error']}")
        
        print(f"\n{'='*80}")
        print(f"❌ TEST FEHLGESCHLAGEN")
        print(f"{'='*80}")
        return False

if __name__ == '__main__':
    import sys
    try:
        success = run_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ FEHLER: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
