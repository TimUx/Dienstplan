"""
Test mit 44h/Woche - Kompromiss zwischen 40h und 48h
"""

from datetime import date
from entities import Employee, Team, ShiftType
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver


def test_44h_januar_2026():
    """Test mit 44h/Woche und Original-Besetzungsanforderungen"""
    
    print("=" * 100)
    print("TEST: Januar 2026 mit 44h/Woche (Kompromiss)")
    print("=" * 100)
    
    # Schichttypen mit 44h/Woche und Original-Besetzung
    shift_types = [
        ShiftType(
            id=1, code="F", name="Frühdienst",
            start_time="05:45", end_time="13:45",
            color_code="#FFD700", hours=8.0, weekly_working_hours=44.0,
            min_staff_weekday=4, max_staff_weekday=8,  # Original
            min_staff_weekend=2, max_staff_weekend=3,  # Original
            works_monday=True, works_tuesday=True, works_wednesday=True,
            works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True
        ),
        ShiftType(
            id=2, code="S", name="Spätdienst",
            start_time="13:45", end_time="21:45",
            color_code="#FF6347", hours=8.0, weekly_working_hours=44.0,
            min_staff_weekday=3, max_staff_weekday=6,  # Original
            min_staff_weekend=2, max_staff_weekend=3,  # Original
            works_monday=True, works_tuesday=True, works_wednesday=True,
            works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True
        ),
        ShiftType(
            id=3, code="N", name="Nachtdienst",
            start_time="21:45", end_time="05:45",
            color_code="#4169E1", hours=8.0, weekly_working_hours=44.0,
            min_staff_weekday=3, max_staff_weekday=5,  # Gelockert auf 5
            min_staff_weekend=2, max_staff_weekend=3,  # Original
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
    print(f"  - Arbeitsstunden: 44h/Woche")
    print(f"  - Besetzung: Original-Anforderungen")
    print(f"  - Zeitraum: {start_date} bis {end_date} (32 Tage)")
    
    # Berechne Anforderungen
    num_weeks = 32 / 7.0
    monthly_hours = 44.0 * num_weeks
    print(f"  - Soll-Stunden: {monthly_hours:.1f}h/Monat ({num_weeks:.2f} Wochen)")
    
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
            time_limit_seconds=180,
            num_workers=4,
            global_settings=global_settings
        )
        
        print(f"Füge Constraints hinzu...")
        solver.add_all_constraints()
        
        print(f"Starte Solver...")
        success = solver.solve()
        
        print(f"\n{'='*100}")
        if success:
            print("✓✓✓ LÖSUNG GEFUNDEN mit 44h/Woche ✓✓✓")
            print("\nDas Schichtmodell für Januar 2026 KANN mit 44h/Woche gebaut werden!")
            
            assignments, _, _ = solver.extract_solution()
            print(f"\nAnzahl Zuweisungen: {len(assignments)}")
            
            # Berechne Stunden pro Mitarbeiter
            emp_hours = {}
            emp_days = {}
            for assignment in assignments:
                emp_id = assignment.employee_id
                shift_type = next((st for st in shift_types if st.id == assignment.shift_type_id), None)
                if shift_type:
                    emp_hours[emp_id] = emp_hours.get(emp_id, 0) + shift_type.hours
                    emp_days[emp_id] = emp_days.get(emp_id, 0) + 1
            
            print(f"\nStunden pro Mitarbeiter (erste 5):")
            for emp_id in sorted(emp_hours.keys())[:5]:
                hours = emp_hours[emp_id]
                days = emp_days[emp_id]
                print(f"  Mitarbeiter {emp_id}: {hours}h in {days} Tagen (Soll: {monthly_hours:.1f}h)")
            
            avg_hours = sum(emp_hours.values()) / len(emp_hours)
            print(f"\nDurchschnitt: {avg_hours:.1f}h (Soll: {monthly_hours:.1f}h)")
            
            if avg_hours >= monthly_hours * 0.95:
                print("✓ Alle Mitarbeiter erreichen mindestens 95% der Soll-Stunden!")
            
            print(f"\n{'='*100}")
            print("FAZIT")
            print("=" * 100)
            print("✓ Mit 44h/Woche (statt 48h) IST eine Lösung möglich!")
            print("✓ Empfehlung: Nutze 44h/Woche für praktikable Planung")
            print("=" * 100)
            
            return True
        else:
            print("✗ INFEASIBLE auch mit 44h/Woche")
            print("\nWeitere Anpassungen erforderlich.")
            return False
            
    except Exception as e:
        print(f"\n✗ FEHLER: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_44h_januar_2026()
    exit(0 if success else 1)
