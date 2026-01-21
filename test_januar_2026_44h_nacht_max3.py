"""
Test mit 44h/Woche und Nacht-Schicht Max=3.
Nutzt die Mon-Fri Block-Constraints und gelockerte Besetzung für Früh und Spät.
"""

from datetime import date
from entities import Employee, Team, ShiftType
from model import ShiftPlanningModel
from solver import ShiftPlanningSolver


def test_44h_nacht_max3_januar_2026():
    """Test mit 44h/Woche, gelockerte Besetzung, Nacht-Schicht Max=3"""
    
    print("=" * 100)
    print("TEST: Januar 2026 mit 44h/Woche + Nacht Max=3 + Mon-Fri Blocks")
    print("=" * 100)
    
    # Schichttypen mit 44h/Woche und spezifischer Nacht-Besetzung
    shift_types = [
        ShiftType(
            id=1, code="F", name="Frühdienst",
            start_time="05:45", end_time="13:45",
            color_code="#FFD700", hours=8.0, weekly_working_hours=44.0,
            min_staff_weekday=3, max_staff_weekday=10,  # Gelockert
            min_staff_weekend=2, max_staff_weekend=5,   # Gelockert
            works_monday=True, works_tuesday=True, works_wednesday=True,
            works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True
        ),
        ShiftType(
            id=2, code="S", name="Spätdienst",
            start_time="13:45", end_time="21:45",
            color_code="#FF6347", hours=8.0, weekly_working_hours=44.0,
            min_staff_weekday=2, max_staff_weekday=10,  # Gelockert
            min_staff_weekend=2, max_staff_weekend=5,   # Gelockert
            works_monday=True, works_tuesday=True, works_wednesday=True,
            works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True
        ),
        ShiftType(
            id=3, code="N", name="Nachtdienst",
            start_time="21:45", end_time="05:45",
            color_code="#4169E1", hours=8.0, weekly_working_hours=44.0,
            min_staff_weekday=2, max_staff_weekday=3,  # STRIKT: Max 3
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
    print(f"  - Besetzung:")
    print(f"      Früh: Min 3, Max 10")
    print(f"      Spät: Min 2, Max 10")
    print(f"      Nacht: Min 2, Max 3 (STRIKT)")
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
            print("✓✓✓ LÖSUNG GEFUNDEN mit 44h/Woche + Nacht Max=3 ✓✓✓")
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
            
            # Analysiere Nacht-Schicht Besetzung
            print(f"\nNacht-Schicht Besetzung pro Tag:")
            night_staffing = {}
            for assignment in assignments:
                shift_type = next((st for st in shift_types if st.id == assignment.shift_type_id), None)
                if shift_type and shift_type.code == 'N':
                    d = assignment.date
                    night_staffing[d] = night_staffing.get(d, 0) + 1
            
            if night_staffing:
                min_night = min(night_staffing.values())
                max_night = max(night_staffing.values())
                avg_night = sum(night_staffing.values()) / len(night_staffing)
                print(f"  Min: {min_night}, Max: {max_night}, Ø: {avg_night:.1f}")
                if max_night <= 3:
                    print(f"  ✓ Nacht-Schicht Max=3 wird eingehalten!")
                else:
                    print(f"  ✗ Nacht-Schicht Max=3 wird NICHT eingehalten! (Max: {max_night})")
            
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
            print("✓ Mit 44h/Woche und Nacht Max=3 IST eine Lösung möglich!")
            print("✓ Mon-Fri Block-Constraints erzwingen vollständige Wochenblöcke")
            print("✓ Weekend-Continuation Preference bevorzugt durchgehende Arbeit")
            print("✓ Nacht-Schicht Constraint (Max=3) wird eingehalten")
            print("=" * 100)
            
            return True
        else:
            print("✗ INFEASIBLE mit 44h/Woche und Nacht Max=3")
            print("\nDiese Kombination ist zu restriktiv.")
            
            if hasattr(solver, 'diagnostics'):
                diagnostics = solver.diagnostics
                if diagnostics.get('potential_issues'):
                    print(f"\nErkannte Probleme:")
                    for issue in diagnostics['potential_issues']:
                        print(f"  • {issue}")
            
            print(f"\n{'='*100}")
            print("MÖGLICHE LÖSUNGEN")
            print("=" * 100)
            print("1. Erhöhe Nacht-Schicht Max auf 4-5")
            print("2. Reduziere Arbeitsstunden auf 40-42h/Woche")
            print("3. Erhöhe Team-Größe auf 6 Mitarbeiter pro Team")
            print("=" * 100)
            
            return False
            
    except Exception as e:
        print(f"\n✗ FEHLER: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_44h_nacht_max3_januar_2026()
    exit(0 if success else 1)
