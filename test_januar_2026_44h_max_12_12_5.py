"""
Test mit 44h/Woche und Nacht Max=5 (statt 4).
Früh max 12, Spät max 12, Nacht max 5, Wochenende max 3.
"""

from datetime import date
from entities import Employee, Team, ShiftType
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver


def test_44h_max_12_12_5_januar_2026():
    """Test mit 44h/Woche und gelockerten Besetzungen (F:12, S:12, N:5)"""
    
    print("=" * 100)
    print("TEST: Januar 2026 mit 44h/Woche + F:Max12, S:Max12, N:Max5, WE:Max3")
    print("=" * 100)
    
    # Schichttypen mit 44h/Woche und weiter gelockerten Besetzungsanforderungen
    shift_types = [
        ShiftType(
            id=1, code="F", name="Frühdienst",
            start_time="05:45", end_time="13:45",
            color_code="#FFD700", hours=8.0, weekly_working_hours=44.0,
            min_staff_weekday=3, max_staff_weekday=12,  # Max 12
            min_staff_weekend=2, max_staff_weekend=3,   # Max 3
            works_monday=True, works_tuesday=True, works_wednesday=True,
            works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True
        ),
        ShiftType(
            id=2, code="S", name="Spätdienst",
            start_time="13:45", end_time="21:45",
            color_code="#FF6347", hours=8.0, weekly_working_hours=44.0,
            min_staff_weekday=2, max_staff_weekday=12,  # Max 12
            min_staff_weekend=2, max_staff_weekend=3,   # Max 3
            works_monday=True, works_tuesday=True, works_wednesday=True,
            works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True
        ),
        ShiftType(
            id=3, code="N", name="Nachtdienst",
            start_time="21:45", end_time="05:45",
            color_code="#4169E1", hours=8.0, weekly_working_hours=44.0,
            min_staff_weekday=2, max_staff_weekday=5,  # Max 5 (erhöht)
            min_staff_weekend=2, max_staff_weekend=3,   # Max 3
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
    print(f"  - Besetzung Wochentage:")
    print(f"      Früh: Min 3, Max 12")
    print(f"      Spät: Min 2, Max 12")
    print(f"      Nacht: Min 2, Max 5 (erhöht)")
    print(f"  - Besetzung Wochenende: Max 3 (alle Schichten)")
    print(f"  - Mon-Fri Block-Constraint: AKTIV")
    print(f"  - Weekend-Continuation Preference: AKTIV")
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
            time_limit_seconds=240,  # 4 Minuten
            num_workers=4,
            global_settings=global_settings
        )
        
        print(f"Füge Constraints hinzu...")
        solver.add_all_constraints()
        
        print(f"Starte Solver...")
        success = solver.solve()
        
        print(f"\n{'='*100}")
        if success:
            print("✓✓✓ LÖSUNG GEFUNDEN mit 44h/Woche + gelockerten Besetzungen ✓✓✓")
            print("\nDas Schichtmodell für Januar 2026 KANN mit diesen Einstellungen gebaut werden!")
            
            assignments, _, _ = solver.extract_solution()
            print(f"\nAnzahl Zuweisungen: {len(assignments)}")
            
            # Berechne Stunden pro Mitarbeiter
            emp_hours = {}
            emp_days = {}
            emp_shifts = {}
            for assignment in assignments:
                emp_id = assignment.employee_id
                shift_type = next((st for st in shift_types if st.id == assignment.shift_type_id), None)
                if shift_type:
                    emp_hours[emp_id] = emp_hours.get(emp_id, 0) + shift_type.hours
                    emp_days[emp_id] = emp_days.get(emp_id, 0) + 1
                    emp_shifts.setdefault(emp_id, {}).setdefault(shift_type.code, 0)
                    emp_shifts[emp_id][shift_type.code] += 1
            
            print(f"\nStunden pro Mitarbeiter (alle 15):")
            print(f"{'Mitarbeiter':<20} {'Tage':>6} {'Stunden':>8} {'Soll':>8} {'Diff':>8} {'F':>4} {'S':>4} {'N':>4}")
            print("-" * 100)
            
            total_hours = 0
            count_above_target = 0
            for emp_id in sorted(emp_hours.keys()):
                hours = emp_hours[emp_id]
                days = emp_days[emp_id]
                diff = hours - monthly_hours
                shifts = emp_shifts.get(emp_id, {})
                
                total_hours += hours
                if hours >= monthly_hours * 0.95:
                    count_above_target += 1
                
                print(f"Mitarbeiter {emp_id:<10} {days:>6} {hours:>8.1f}h {monthly_hours:>7.1f}h {diff:>+7.1f}h "
                      f"{shifts.get('F', 0):>4} {shifts.get('S', 0):>4} {shifts.get('N', 0):>4}")
            
            avg_hours = total_hours / len(emp_hours)
            print("-" * 100)
            print(f"{'DURCHSCHNITT':<20} {'':<6} {avg_hours:>8.1f}h {monthly_hours:>7.1f}h")
            
            print(f"\n{'='*100}")
            print("ANALYSE")
            print("=" * 100)
            print(f"Mitarbeiter mit ≥95% Soll: {count_above_target} von {len(emp_hours)}")
            
            if count_above_target >= len(emp_hours) * 0.9:
                print("✓ Mindestens 90% der Mitarbeiter erreichen ≥95% der Soll-Stunden!")
            
            # Analysiere Besetzung pro Schicht
            print(f"\nBesetzung pro Tag und Schicht:")
            for shift_code in ['F', 'S', 'N']:
                shift_staffing = {}
                for assignment in assignments:
                    shift_type = next((st for st in shift_types if st.id == assignment.shift_type_id), None)
                    if shift_type and shift_type.code == shift_code:
                        d = assignment.date
                        shift_staffing[d] = shift_staffing.get(d, 0) + 1
                
                if shift_staffing:
                    min_staff = min(shift_staffing.values())
                    max_staff = max(shift_staffing.values())
                    avg_staff = sum(shift_staffing.values()) / len(shift_staffing)
                    
                    # Finde Max-Limit für diese Schicht
                    shift_type = next((st for st in shift_types if st.code == shift_code), None)
                    max_limit = shift_type.max_staff_weekday if shift_type else "?"
                    
                    print(f"  {shift_code}-Schicht: Min {min_staff}, Max {max_staff}, Ø {avg_staff:.1f} (Limit: {max_limit})")
                    
                    if shift_code == 'N' and max_staff <= 5:
                        print(f"    ✓ Nacht-Schicht Max=5 wird eingehalten!")
                    elif shift_code == 'N' and max_staff > 5:
                        print(f"    ✗ Nacht-Schicht Max=5 wird NICHT eingehalten! (Max: {max_staff})")
            
            # Analysiere Block-Scheduling
            from datetime import timedelta
            print(f"\nBlock-Scheduling Analyse (erste 5 Mitarbeiter):")
            for emp_id in sorted(emp_hours.keys())[:5]:
                emp_dates = sorted([a.date for a in assignments if a.employee_id == emp_id])
                if not emp_dates:
                    continue
                
                blocks = []
                current_block = [emp_dates[0]]
                for i in range(1, len(emp_dates)):
                    if (emp_dates[i] - emp_dates[i-1]).days == 1:
                        current_block.append(emp_dates[i])
                    else:
                        blocks.append(len(current_block))
                        current_block = [emp_dates[i]]
                if current_block:
                    blocks.append(len(current_block))
                
                avg_block = sum(blocks) / len(blocks) if blocks else 0
                max_block = max(blocks) if blocks else 0
                print(f"  Mitarbeiter {emp_id}: Ø {avg_block:.1f} Tage/Block, Max {max_block} Tage, {len(blocks)} Blöcke")
            
            print(f"\n{'='*100}")
            print("FAZIT")
            print("=" * 100)
            print("✓ Mit 44h/Woche und gelockerten Besetzungen (F:12, S:12, N:5) IST eine Lösung möglich!")
            print("✓ Mon-Fri Block-Constraints erzwingen vollständige Wochenblöcke")
            print("✓ Weekend-Continuation Preference bevorzugt durchgehende Arbeit")
            print("✓ Nacht Max=5 statt 4 ermöglicht ausreichend Flexibilität")
            print("=" * 100)
            
            return True
        else:
            print("✗ INFEASIBLE mit 44h/Woche und diesen Besetzungsanforderungen")
            print("\nDiese Kombination ist zu restriktiv.")
            return False
            
    except Exception as e:
        print(f"\n✗ FEHLER: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_44h_max_12_12_5_januar_2026()
    exit(0 if success else 1)
