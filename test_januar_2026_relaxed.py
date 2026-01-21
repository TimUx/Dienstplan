"""
Simplified test to verify the system works with relaxed constraints.
This will help identify which constraint is causing INFEASIBLE.
"""

from datetime import date
from entities import Employee, Team, ShiftType
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver


def test_relaxed_januar_2026():
    """Test with very relaxed constraints to ensure system works"""
    
    print("=" * 100)
    print("SIMPLIFIED TEST: Januar 2026 mit gelockerten Constraints")
    print("=" * 100)
    
    # Sehr flexible Schichttypen
    shift_types = [
        ShiftType(
            id=1, code="F", name="Frühdienst",
            start_time="05:45", end_time="13:45",
            color_code="#FFD700", hours=8.0, weekly_working_hours=40.0,  # Reduziert auf 40h
            min_staff_weekday=2, max_staff_weekday=10,  # Sehr flexibel
            min_staff_weekend=1, max_staff_weekend=10,
            works_monday=True, works_tuesday=True, works_wednesday=True,
            works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True
        ),
        ShiftType(
            id=2, code="S", name="Spätdienst",
            start_time="13:45", end_time="21:45",
            color_code="#FF6347", hours=8.0, weekly_working_hours=40.0,
            min_staff_weekday=2, max_staff_weekday=10,
            min_staff_weekend=1, max_staff_weekend=10,
            works_monday=True, works_tuesday=True, works_wednesday=True,
            works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True
        ),
        ShiftType(
            id=3, code="N", name="Nachtdienst",
            start_time="21:45", end_time="05:45",
            color_code="#4169E1", hours=8.0, weekly_working_hours=40.0,
            min_staff_weekday=2, max_staff_weekday=10,  # Sehr flexibel
            min_staff_weekend=1, max_staff_weekend=10,
            works_monday=True, works_tuesday=True, works_wednesday=True,
            works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True
        )
    ]
    
    # 3 Teams mit je 5 Mitarbeitern
    teams = [
        Team(id=1, name="Team Alpha"),
        Team(id=2, name="Team Beta"),
        Team(id=3, name="Team Gamma")
    ]
    
    employees = []
    emp_id = 1
    for team_idx, team in enumerate(teams):
        for member_num in range(1, 6):
            employee = Employee(
                id=emp_id,
                vorname=f"MA_{['Alpha','Beta','Gamma'][team_idx]}",
                name=f"M{member_num}",
                personalnummer=f"{team_idx+1}{member_num:02d}",
                team_id=team.id
            )
            employees.append(employee)
            team.employees.append(employee)
            emp_id += 1
    
    for team in teams:
        team.allowed_shift_type_ids = [st.id for st in shift_types]
    
    # Januar 2026 bis 01.02. (vollständige Wochen)
    start_date = date(2026, 1, 1)
    end_date = date(2026, 2, 1)
    absences = []
    
    print(f"\nKonfiguration:")
    print(f"  - 3 Teams à 5 Mitarbeiter = 15 total")
    print(f"  - Arbeitsstunden: 40h/Woche (reduziert)")
    print(f"  - Besetzung: Min 2, Max 10 (sehr flexibel)")
    print(f"  - Zeitraum: {start_date} bis {end_date}")
    
    # Erstelle Modell
    global_settings = {
        'max_consecutive_shifts_weeks': 6,
        'max_consecutive_night_shifts_weeks': 3,
        'min_rest_hours': 11
    }
    
    try:
        print(f"\nErstelle Model & Solver...")
        model = ShiftPlanningModel(
            employees=employees,
            teams=teams,
            start_date=start_date,
            end_date=end_date,
            absences=absences,
            shift_types=shift_types
        )
        
        solver = ShiftPlanningSolver(
            model,
            time_limit_seconds=120,
            num_workers=4,
            global_settings=global_settings
        )
        
        print(f"Füge Constraints hinzu...")
        solver.add_all_constraints()
        
        print(f"Starte Solver...")
        success = solver.solve()
        
        print(f"\n{'='*100}")
        if success:
            print("✓✓✓ LÖSUNG GEFUNDEN mit gelockerten Constraints ✓✓✓")
            print("\nDas beweist: Das System funktioniert grundsätzlich!")
            print("Die Original-Constraints sind zu restriktiv.")
            
            assignments, _, _ = solver.extract_solution()
            print(f"\nAnzahl Zuweisungen: {len(assignments)}")
            
            # Berechne Stunden pro Mitarbeiter
            emp_hours = {}
            for assignment in assignments:
                emp_id = assignment.employee_id
                shift_type = next((st for st in shift_types if st.id == assignment.shift_type_id), None)
                if shift_type:
                    emp_hours[emp_id] = emp_hours.get(emp_id, 0) + shift_type.hours
            
            print(f"\nStunden pro Mitarbeiter:")
            for emp_id, hours in sorted(emp_hours.items())[:5]:
                print(f"  Mitarbeiter {emp_id}: {hours}h")
            
            return True
        else:
            print("✗ AUCH MIT GELOCKERTEN CONSTRAINTS INFEASIBLE")
            print("\nDas deutet auf ein grundlegendes Problem hin!")
            return False
            
    except Exception as e:
        print(f"\n✗ FEHLER: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_relaxed_januar_2026()
    exit(0 if success else 1)
