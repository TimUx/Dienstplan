#!/usr/bin/env python3
"""
Test January 2026 shift planning with soft constraint system.
Configuration:
- 3 teams × 5 employees (15 total)
- 48h/week target
- January 2026: 31 days (Thu Jan 1 - Sat Jan 31)
- Extended to 5 complete weeks (Mon Dec 29, 2025 - Sun Feb 1, 2026 = 35 days)

Expected: FEASIBLE with soft constraints and violation tracking
"""

import sys
import os
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project directory to path
sys.path.insert(0, '/home/runner/work/Dienstplan/Dienstplan')

from database import Base, ShiftType, Team, Employee, Absence, ShiftAssignment, GlobalSettings
from solver import solve_shifts
from constraints import add_all_constraints
from ortools.sat.python import cp_model

def setup_test_database():
    """Create in-memory database with test data."""
    engine = create_engine('sqlite:///:memory:', echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # Create shift types with updated max staffing
    shift_f = ShiftType(Name='F', StartTime='06:00', EndTime='14:00', 
                       MinWorkers=4, MaxWorkers=10, WeeklyWorkingHours=48)
    shift_s = ShiftType(Name='S', StartTime='14:00', EndTime='22:00',
                       MinWorkers=3, MaxWorkers=10, WeeklyWorkingHours=48)
    shift_n = ShiftType(Name='N', StartTime='22:00', EndTime='06:00',
                       MinWorkers=3, MaxWorkers=10, WeeklyWorkingHours=48)
    
    session.add_all([shift_f, shift_s, shift_n])
    session.flush()
    
    # Create 3 teams with 5 employees each
    teams = []
    employees = []
    for team_num in range(1, 4):
        team = Team(Name=f'Team{team_num}')
        session.add(team)
        session.flush()
        teams.append(team)
        
        for emp_num in range(1, 6):
            emp = Employee(
                Vorname=f'Employee{team_num}{emp_num}',
                Nachname=f'Test',
                Personalnummer=f'E{team_num}{emp_num:02d}',
                TeamID=team.TeamID
            )
            session.add(emp)
            employees.append(emp)
    
    session.flush()
    
    # Create global settings
    settings = GlobalSettings(
        SettingName='MAXIMUM_CONSECUTIVE_SHIFTS_WEEKS',
        SettingValue='4'
    )
    session.add(settings)
    
    session.commit()
    return session, teams, employees, [shift_f, shift_s, shift_n]

def extend_to_complete_weeks(start_date, end_date):
    """Extend dates to complete weeks (Monday to Sunday)."""
    # Extend start backwards to Monday
    start_weekday = start_date.weekday()
    if start_weekday != 0:  # Not Monday
        extended_start = start_date - timedelta(days=start_weekday)
    else:
        extended_start = start_date
    
    # Extend end forward to Sunday
    end_weekday = end_date.weekday()
    if end_weekday != 6:  # Not Sunday
        extended_end = end_date + timedelta(days=(6 - end_weekday))
    else:
        extended_end = end_date
    
    return extended_start, extended_end

def test_january_2026():
    """Test January 2026 planning with soft constraints."""
    print("=" * 80)
    print("TEST: Januar 2026 Schichtplanung mit Soft Constraints")
    print("=" * 80)
    
    # Setup database
    session, teams, employees, shift_types = setup_test_database()
    
    # January 2026 dates
    start_date = date(2026, 1, 1)  # Thursday
    end_date = date(2026, 1, 31)   # Saturday
    
    # Extend to complete weeks
    extended_start, extended_end = extend_to_complete_weeks(start_date, end_date)
    
    print(f"\n📅 Planungszeitraum:")
    print(f"  Monat:      {start_date} bis {end_date} ({(end_date - start_date).days + 1} Tage)")
    print(f"  Erweitert:  {extended_start} bis {extended_end} ({(extended_end - extended_start).days + 1} Tage)")
    print(f"  Wochen:     {(extended_end - extended_start).days / 7:.1f} Wochen")
    
    print(f"\n👥 Konfiguration:")
    print(f"  Teams:      {len(teams)}")
    print(f"  Mitarbeiter: {len(employees)} (je Team: {len(employees) // len(teams)})")
    print(f"  Schichttypen: {len(shift_types)}")
    
    print(f"\n⚙️ Schicht-Parameter:")
    for st in shift_types:
        print(f"  {st.Name}: Min={st.MinWorkers}, Max={st.MaxWorkers}, Zeit={st.StartTime}-{st.EndTime}")
    
    print(f"\n🎯 Arbeitsstunden-Ziel:")
    target_hours = 48 / 7 * (extended_end - extended_start).days
    print(f"  Berechnung: 48h/7 × {(extended_end - extended_start).days} Tage = {target_hours:.1f}h")
    print(f"  SOFT: Ziel {target_hours:.0f}h pro Mitarbeiter")
    print(f"  ENTFERNT: Keine harte 192h Untergrenze mehr")
    print(f"  ENTFERNT: Keine harte Wochenstunden-Obergrenze mehr")
    
    print(f"\n🔧 Aktive Constraints:")
    print(f"  HART:")
    print(f"    - Team-Rotation F→N→S (3-Wochen-Zyklus)")
    print(f"    - Mindestbesetzung (F≥4, S≥3, N≥3)")
    print(f"    - 11h Ruhezeit (AUSSER Sonntag→Montag)")
    print(f"    - Aufeinanderfolgende Schichten-Limits")
    print(f"  WEICH:")
    print(f"    - Zielstunden {target_hours:.0f}h (Gewicht 1x)")
    print(f"    - Max-Besetzung kann überschritten werden (Gewicht 5x)")
    print(f"    - Block-Scheduling (Bonus-Maximierung)")
    print(f"    - Faire Verteilung (Gewicht 1x)")
    
    # Run solver
    print(f"\n🔍 Starte CP-SAT Solver...")
    print(f"  Timeout: 180 Sekunden")
    
    try:
        result = solve_shifts(
            session=session,
            start_date=extended_start,
            end_date=extended_end,
            solver_timeout=180
        )
        
        print(f"\n{'='*80}")
        print(f"ERGEBNIS")
        print(f"{'='*80}")
        
        if result['status'] == 'FEASIBLE' or result['status'] == 'OPTIMAL':
            print(f"✅ STATUS: {result['status']}")
            print(f"✅ Lösung gefunden!")
            
            # Analyze assignments
            assignments = session.query(ShiftAssignment).filter(
                ShiftAssignment.Date >= extended_start,
                ShiftAssignment.Date <= extended_end
            ).all()
            
            print(f"\n📊 Zuweisungen:")
            print(f"  Gesamt: {len(assignments)} Schichtzuweisungen")
            
            # Analyze hours per employee
            employee_hours = {}
            for emp in employees:
                emp_assignments = [a for a in assignments if a.EmployeeID == emp.EmployeeID]
                hours = len(emp_assignments) * 8  # 8h per shift
                employee_hours[emp.EmployeeID] = hours
            
            print(f"\n👤 Arbeitsstunden pro Mitarbeiter:")
            min_hours = min(employee_hours.values())
            max_hours = max(employee_hours.values())
            avg_hours = sum(employee_hours.values()) / len(employee_hours)
            
            print(f"  Minimum:     {min_hours}h")
            print(f"  Maximum:     {max_hours}h")
            print(f"  Durchschnitt: {avg_hours:.1f}h")
            print(f"  Ziel:        {target_hours:.0f}h")
            print(f"  Abweichung:  {avg_hours - target_hours:+.1f}h ({(avg_hours - target_hours) / target_hours * 100:+.1f}%)")
            
            # Check if anyone is below old hard minimum
            below_192 = [emp_id for emp_id, h in employee_hours.items() if h < 192]
            if below_192:
                print(f"\n  ℹ️ {len(below_192)} Mitarbeiter unter 192h (alte harte Grenze)")
                print(f"     Dies ist jetzt erlaubt durch Soft-Constraint-System!")
            
            # Distribution
            print(f"\n📈 Stundenverteilung:")
            for emp_id, hours in sorted(employee_hours.items()):
                emp = session.query(Employee).filter_by(EmployeeID=emp_id).first()
                shortage = max(0, target_hours - hours)
                print(f"  {emp.Vorname}: {hours}h (Unterschreitung: {shortage:.0f}h)")
            
            # Check violations if present
            if 'violations' in result and result['violations']:
                print(f"\n⚠️ Violations erkannt:")
                violations = result['violations']
                if hasattr(violations, 'get_summary'):
                    summary = violations.get_summary()
                    print(f"  {summary['message']}")
                    print(f"  Gesamt: {summary['total']}")
                    if summary.get('warnings'):
                        print(f"\n  Warnungen:")
                        for w in summary['warnings'][:5]:
                            print(f"    - {w}")
                    if summary.get('info'):
                        print(f"\n  Informationen:")
                        for i in summary['info'][:5]:
                            print(f"    - {i}")
            else:
                print(f"\n✅ Keine Violations - Alle Regeln eingehalten!")
            
            print(f"\n{'='*80}")
            print(f"✅ TEST ERFOLGREICH - MONATLICHE PLANUNG IST MÖGLICH!")
            print(f"{'='*80}")
            return True
            
        else:
            print(f"❌ STATUS: {result['status']}")
            print(f"❌ Keine Lösung gefunden")
            
            if 'error' in result:
                print(f"\nFehler: {result['error']}")
            
            print(f"\n{'='*80}")
            print(f"❌ TEST FEHLGESCHLAGEN - System noch immer INFEASIBLE")
            print(f"{'='*80}")
            return False
            
    except Exception as e:
        print(f"\n❌ FEHLER während der Planung:")
        print(f"  {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_january_2026()
    sys.exit(0 if success else 1)
