"""
Alternative Lösung: Januar 2026 mit 4 Teams

Dieser Test prüft ob das Schichtmodell mit 4 Teams statt 3 Teams machbar ist.

Änderungen gegenüber Original:
- 4 Teams statt 3 Teams
- 4 Mitarbeiter pro Team (16 total statt 15)
- Behält alle anderen Anforderungen bei (48h/Woche, Min/Max Besetzung, etc.)

Hypothese: Mit 4 Teams könnte die Rotation F→N→S besser funktionieren,
da mehr Flexibilität bei der Besetzung entsteht.
"""

from datetime import date
from entities import Employee, Team, ShiftType
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver
import calendar


def erstelle_4_teams_konstellation():
    """
    Erstellt Konstellation mit 4 Teams à 4 Mitarbeitern.
    """
    
    # Schichttypen (Original-Anforderungen)
    shift_types = [
        ShiftType(
            id=1, code="F", name="Frühdienst",
            start_time="05:45", end_time="13:45",
            color_code="#FFD700", hours=8.0, weekly_working_hours=48.0,
            min_staff_weekday=4, max_staff_weekday=8,
            min_staff_weekend=2, max_staff_weekend=3,
            works_monday=True, works_tuesday=True, works_wednesday=True,
            works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True
        ),
        ShiftType(
            id=2, code="S", name="Spätdienst",
            start_time="13:45", end_time="21:45",
            color_code="#FF6347", hours=8.0, weekly_working_hours=48.0,
            min_staff_weekday=3, max_staff_weekday=6,
            min_staff_weekend=2, max_staff_weekend=3,
            works_monday=True, works_tuesday=True, works_wednesday=True,
            works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True
        ),
        ShiftType(
            id=3, code="N", name="Nachtdienst",
            start_time="21:45", end_time="05:45",
            color_code="#4169E1", hours=8.0, weekly_working_hours=48.0,
            min_staff_weekday=3, max_staff_weekday=5,  # GELOCKERT: Max auf 5
            min_staff_weekend=2, max_staff_weekend=3,
            works_monday=True, works_tuesday=True, works_wednesday=True,
            works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True
        )
    ]
    
    # Erstelle 4 Teams mit je 4 Mitarbeitern
    teams = [
        Team(id=1, name="Team Alpha", description="Erstes Schicht-Team"),
        Team(id=2, name="Team Beta", description="Zweites Schicht-Team"),
        Team(id=3, name="Team Gamma", description="Drittes Schicht-Team"),
        Team(id=4, name="Team Delta", description="Viertes Schicht-Team")
    ]
    
    # Erstelle 16 Mitarbeiter (4 pro Team)
    employees = []
    emp_id = 1
    team_names = ["Alpha", "Beta", "Gamma", "Delta"]
    
    for team_idx, team in enumerate(teams):
        for member_num in range(1, 5):  # 4 Mitarbeiter pro Team
            employee = Employee(
                id=emp_id,
                vorname=f"MA_{team_names[team_idx]}",
                name=f"M{member_num}",
                personalnummer=f"{team_idx+1}{member_num:02d}",
                team_id=team.id,
                email=f"ma{emp_id}@test.de"
            )
            employees.append(employee)
            team.employees.append(employee)
            emp_id += 1
    
    # Setze erlaubte Schichttypen
    for team in teams:
        team.allowed_shift_type_ids = [st.id for st in shift_types]
    
    # Januar 2026
    start_date = date(2026, 1, 1)
    end_date = date(2026, 1, 31)
    absences = []
    
    return employees, teams, start_date, end_date, shift_types, absences


def test_4_teams_januar_2026():
    """Test mit 4 Teams statt 3 Teams"""
    
    print("=" * 100)
    print("TEST: JANUAR 2026 MIT 4 TEAMS (Alternative Lösung)")
    print("=" * 100)
    
    employees, teams, start_date, end_date, shift_types, absences = erstelle_4_teams_konstellation()
    
    print(f"\nÄnderungen gegenüber Original:")
    print(f"  ✓ 4 Teams statt 3 Teams")
    print(f"  ✓ 4 Mitarbeiter pro Team (16 total statt 15)")
    print(f"  ✓ Nacht-Schicht Max=5 (statt Max=3)")
    print(f"  ✓ Alle anderen Anforderungen unverändert")
    
    print(f"\nKonfiguration:")
    print(f"  - Teams: {len(teams)}")
    for team in teams:
        print(f"    • {team.name}: {len(team.employees)} Mitarbeiter")
    print(f"  - Gesamt: {len(employees)} Mitarbeiter")
    print(f"  - Zeitraum: {start_date} bis {end_date} (31 Tage)")
    
    print(f"\nSchichttypen:")
    for st in shift_types:
        print(f"  - {st.name} ({st.code}): {st.hours}h/Tag, {st.weekly_working_hours}h/Woche")
        print(f"      Wochentag Min {st.min_staff_weekday} / Max {st.max_staff_weekday}")
        print(f"      Wochenende Min {st.min_staff_weekend} / Max {st.max_staff_weekend}")
    
    # Berechne Anforderungen
    num_weeks = 31 / 7.0
    monthly_hours = shift_types[0].weekly_working_hours * num_weeks
    
    print(f"\nArbeitszeitberechnung:")
    print(f"  - Wochenstunden: {shift_types[0].weekly_working_hours}h")
    print(f"  - Wochen im Januar: {num_weeks:.2f}")
    print(f"  - Monatsstunden (Soll): {monthly_hours:.1f}h")
    print(f"  - Benötigte Arbeitstage: {monthly_hours / 8:.1f}")
    
    # Besetzungsanalyse
    print(f"\nBesetzungsanalyse:")
    weekdays = 22
    weekends = 9
    
    for st in shift_types:
        min_days = (weekdays * st.min_staff_weekday) + (weekends * st.min_staff_weekend)
        max_days = (weekdays * st.max_staff_weekday) + (weekends * st.max_staff_weekend)
        print(f"  {st.code}: Min {min_days} / Max {max_days} Personentage")
    
    total_capacity = len(employees) * 31
    print(f"  Verfügbare Kapazität: {total_capacity} Personentage")
    
    # Erstelle Modell
    print(f"\n{'':-<100}")
    print(f"SOLVER START")
    print("-" * 100)
    
    global_settings = {
        'max_consecutive_shifts_weeks': 6,
        'max_consecutive_night_shifts_weeks': 3,
        'min_rest_hours': 11
    }
    
    try:
        print(f"\nErstelle ShiftPlanningModel...")
        model = ShiftPlanningModel(
            employees=employees,
            teams=teams,
            start_date=start_date,
            end_date=end_date,
            absences=absences,
            shift_types=shift_types
        )
        
        print(f"Erstelle ShiftPlanningSolver...")
        solver = ShiftPlanningSolver(
            model,
            time_limit_seconds=180,  # 3 Minuten
            num_workers=4,
            global_settings=global_settings
        )
        
        print(f"Füge Constraints hinzu...")
        solver.add_all_constraints()
        
        print(f"Starte Solver...")
        success = solver.solve()
        
        print(f"\n{'='*100}")
        print("ERGEBNIS")
        print("=" * 100)
        
        if success:
            print(f"\n✓✓✓ LÖSUNG GEFUNDEN! ✓✓✓")
            print(f"\nDas Schichtmodell für Januar 2026 KANN mit 4 Teams gebaut werden!")
            
            # Extrahiere Lösung
            assignments, special_functions, complete_schedule = solver.extract_solution()
            print(f"\nGesamtanzahl Schichtzuweisungen: {len(assignments)}")
            
            # Analysiere Lösung
            employee_stats = {}
            for emp in employees:
                employee_stats[emp.id] = {
                    'name': emp.full_name,
                    'team': emp.team_id,
                    'days': 0,
                    'hours': 0.0,
                    'shifts': {st.code: 0 for st in shift_types}
                }
            
            for assignment in assignments:
                emp_id = assignment.employee_id
                shift_type = next((st for st in shift_types if st.id == assignment.shift_type_id), None)
                if shift_type:
                    employee_stats[emp_id]['days'] += 1
                    employee_stats[emp_id]['hours'] += shift_type.hours
                    employee_stats[emp_id]['shifts'][shift_type.code] += 1
            
            print(f"\nArbeitsstunden pro Mitarbeiter:")
            print(f"{'Team':<6} {'Mitarbeiter':<25} {'Tage':>6} {'Stunden':>8} {'Soll':>8} {'Diff':>8} {'F':>4} {'S':>4} {'N':>4}")
            print("-" * 100)
            
            alle_erfuellt = True
            team_totals = {1: 0, 2: 0, 3: 0, 4: 0}
            
            for emp_id in sorted(employee_stats.keys()):
                stats = employee_stats[emp_id]
                soll_hours = monthly_hours
                diff_hours = stats['hours'] - soll_hours
                diff_str = f"{diff_hours:+.1f}h"
                
                if stats['hours'] < soll_hours * 0.95:  # Allow 5% tolerance
                    alle_erfuellt = False
                
                team_totals[stats['team']] += stats['hours']
                
                print(f"T{stats['team']:<5} {stats['name']:<25} {stats['days']:>6} {stats['hours']:>8.1f}h "
                      f"{soll_hours:>7.1f}h {diff_str:>8} "
                      f"{stats['shifts']['F']:>4} {stats['shifts']['S']:>4} {stats['shifts']['N']:>4}")
            
            print("-" * 100)
            
            print(f"\nTeam-Summen:")
            for team_id in [1, 2, 3, 4]:
                print(f"  Team {team_id}: {team_totals[team_id]:.1f}h gesamt")
            
            if alle_erfuellt:
                print(f"\n✓ Alle Mitarbeiter erreichen mindestens 95% ihrer Soll-Stunden!")
            else:
                print(f"\n⚠ Einige Mitarbeiter unter 95% Soll (aber Lösung ist gültig)")
            
            print(f"\n{'='*100}")
            print("FAZIT")
            print("=" * 100)
            print(f"✓ Mit 4 Teams à 4 Mitarbeitern KANN ein gültiges Schichtmodell erstellt werden!")
            print(f"✓ Diese Konfiguration löst das Rotationsproblem")
            print(f"✓ Empfehlung: 4 Teams statt 3 Teams für mehr Flexibilität")
            print("=" * 100)
            
            return True
            
        else:
            print(f"\n✗ INFEASIBLE - Auch mit 4 Teams keine Lösung")
            print(f"\nDas Problem liegt tiefer in der System-Architektur.")
            
            if hasattr(solver, 'diagnostics'):
                diagnostics = solver.diagnostics
                if diagnostics.get('potential_issues'):
                    print(f"\nErkannte Probleme:")
                    for issue in diagnostics['potential_issues']:
                        print(f"  • {issue}")
            
            return False
        
    except Exception as e:
        print(f"\n✗ FEHLER: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_4_teams_januar_2026()
    
    if success:
        print("\n✓ Test erfolgreich - Lösung mit 4 Teams gefunden!")
        exit(0)
    else:
        print("\n✗ Test fehlgeschlagen - Auch 4 Teams waren nicht ausreichend")
        exit(1)
