"""
Systematischer Test für 44h/Woche mit aufsteigenden Nacht-Max-Werten.
Ziel: Minimale Max-Werte finden, die funktionieren.
"""

from datetime import date
from entities import Employee, Team, ShiftType
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver


def test_44h_with_night_max(night_max, frueh_max=10, spaet_max=10):
    """Test 44h/Woche mit spezifischen Max-Werten"""
    
    print(f"\n{'='*100}")
    print(f"TEST: 44h/Woche mit F:Max{frueh_max}, S:Max{spaet_max}, N:Max{night_max}")
    print(f"{'='*100}")
    
    # Schichttypen
    shift_types = [
        ShiftType(
            id=1, code="F", name="Frühdienst",
            start_time="05:45", end_time="13:45",
            color_code="#FFD700", hours=8.0, weekly_working_hours=44.0,
            min_staff_weekday=3, max_staff_weekday=frueh_max,
            min_staff_weekend=2, max_staff_weekend=3,
            works_monday=True, works_tuesday=True, works_wednesday=True,
            works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True
        ),
        ShiftType(
            id=2, code="S", name="Spätdienst",
            start_time="13:45", end_time="21:45",
            color_code="#FF6347", hours=8.0, weekly_working_hours=44.0,
            min_staff_weekday=2, max_staff_weekday=spaet_max,
            min_staff_weekend=2, max_staff_weekend=3,
            works_monday=True, works_tuesday=True, works_wednesday=True,
            works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True
        ),
        ShiftType(
            id=3, code="N", name="Nachtdienst",
            start_time="21:45", end_time="05:45",
            color_code="#4169E1", hours=8.0, weekly_working_hours=44.0,
            min_staff_weekday=2, max_staff_weekday=night_max,
            min_staff_weekend=2, max_staff_weekend=3,
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
    
    start_date = date(2026, 1, 1)
    end_date = date(2026, 2, 1)
    absences = []
    
    global_settings = {
        'max_consecutive_shifts_weeks': 6,
        'max_consecutive_night_shifts_weeks': 3,
        'min_rest_hours': 11
    }
    
    try:
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
            time_limit_seconds=240,
            num_workers=4,
            global_settings=global_settings
        )
        
        solver.add_all_constraints()
        success = solver.solve()
        
        if success:
            print(f"✓✓✓ FEASIBLE mit F:{frueh_max}, S:{spaet_max}, N:{night_max} ✓✓✓")
            
            assignments, _, _ = solver.extract_solution()
            
            # Berechne Stunden
            emp_hours = {}
            for assignment in assignments:
                emp_id = assignment.employee_id
                shift_type = next((st for st in shift_types if st.id == assignment.shift_type_id), None)
                if shift_type:
                    emp_hours[emp_id] = emp_hours.get(emp_id, 0) + shift_type.hours
            
            monthly_hours = 44.0 * (32 / 7.0)
            avg_hours = sum(emp_hours.values()) / len(emp_hours) if emp_hours else 0
            
            print(f"Durchschnitt: {avg_hours:.1f}h (Soll: {monthly_hours:.1f}h)")
            print(f"Anzahl Zuweisungen: {len(assignments)}")
            
            return True, frueh_max, spaet_max, night_max
        else:
            print(f"✗ INFEASIBLE mit F:{frueh_max}, S:{spaet_max}, N:{night_max}")
            return False, frueh_max, spaet_max, night_max
            
    except Exception as e:
        print(f"✗ FEHLER: {e}")
        return False, frueh_max, spaet_max, night_max


def find_minimal_44h_solution():
    """Finde minimale Max-Werte für 44h/Woche"""
    
    print("=" * 100)
    print("SYSTEMATISCHE SUCHE: Minimale Max-Werte für 44h/Woche")
    print("=" * 100)
    
    results = []
    
    # Test mit aufsteigenden Nacht-Max-Werten
    # Früh und Spät bleiben bei 10 (bereits als zu niedrig getestet mit 12)
    for night_max in [6, 7, 8, 9, 10]:
        print(f"\n--- Teste Nacht Max={night_max} ---")
        success, f, s, n = test_44h_with_night_max(night_max, frueh_max=10, spaet_max=10)
        results.append((success, f, s, n))
        
        if success:
            print(f"\n{'='*100}")
            print(f"✓ LÖSUNG GEFUNDEN!")
            print(f"{'='*100}")
            print(f"Minimale funktionierende Konfiguration für 44h/Woche:")
            print(f"  - Früh: Max {f}")
            print(f"  - Spät: Max {s}")
            print(f"  - Nacht: Max {n}")
            print(f"  - Wochenende: Max 3 (alle Schichten)")
            print(f"{'='*100}")
            break
    
    # Zusammenfassung
    print(f"\n{'='*100}")
    print("ERGEBNISSE ÜBERSICHT")
    print("=" * 100)
    print(f"{'Früh Max':<10} {'Spät Max':<10} {'Nacht Max':<12} {'Ergebnis':<15}")
    print("-" * 100)
    for success, f, s, n in results:
        status = "✓ FEASIBLE" if success else "✗ INFEASIBLE"
        print(f"{f:<10} {s:<10} {n:<12} {status:<15}")
    
    # Finde minimale Lösung
    working_solutions = [(f, s, n) for success, f, s, n in results if success]
    if working_solutions:
        min_solution = min(working_solutions, key=lambda x: x[2])  # Sortiere nach Nacht
        print(f"\n{'='*100}")
        print("EMPFEHLUNG")
        print("=" * 100)
        print(f"Für 44h/Woche mit Mon-Fri Blocks und F→N→S Rotation:")
        print(f"  - Früh: Max {min_solution[0]}")
        print(f"  - Spät: Max {min_solution[1]}")
        print(f"  - Nacht: Max {min_solution[2]}")
        print(f"  - Wochenende: Max 3")
        print("=" * 100)
        return min_solution
    else:
        print("\n✗ Keine funktionierende Lösung gefunden im getesteten Bereich!")
        print("Empfehlung: 40h/Woche oder 48h/Woche nutzen.")
        return None


if __name__ == "__main__":
    solution = find_minimal_44h_solution()
    exit(0 if solution else 1)
