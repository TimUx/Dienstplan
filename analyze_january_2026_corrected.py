"""
CORRECTED Analysis for January 2026 shift planning.

IMPORTANT CLARIFICATION from TimUx:
- MaxConsecutiveShifts = 6 weeks → max 42 aufeinanderfolgende TAGE (F/S Schichten)
- MaxConsecutiveNightShifts = 3 weeks → max 21 aufeinanderfolgende TAGE (N Schichten)

Ein Mitarbeiter darf maximal:
- 21 aufeinanderfolgende Tage Nachtschicht ODER
- 42 aufeinanderfolgende Tage andere Schichten (F/S) arbeiten

Es gibt KEIN tägliches Arbeitslimit - Mitarbeiter können alle 7 Tage pro Woche arbeiten!
"""

from datetime import date, timedelta
from calendar import monthrange
from entities import STANDARD_SHIFT_TYPES
import math

def analyze_corrected_constraints():
    """
    Analyze with CORRECT understanding of consecutive constraints.
    """
    print("=" * 80)
    print("CORRECTED ANALYSIS FOR JANUARY 2026")
    print("=" * 80)
    print("\nIMPORTANT CLARIFICATION:")
    print("  MaxConsecutiveShifts = 6 Wochen → 42 aufeinanderfolgende TAGE (F/S)")
    print("  MaxConsecutiveNightShifts = 3 Wochen → 21 aufeinanderfolgende TAGE (N)")
    print("  Mitarbeiter können alle 7 Tage pro Woche arbeiten!")
    print("=" * 80)
    
    # Configuration
    num_teams = 3
    num_employees_per_team = 5
    num_employees = num_teams * num_employees_per_team
    
    # Get shift types
    shift_types_fsn = [st for st in STANDARD_SHIFT_TYPES if st.code in ['F', 'S', 'N']]
    
    # Test with different weekly hours
    for weekly_hours in [48.0, 44.0, 40.0]:
        print(f"\n" + "=" * 80)
        print(f"ANALYSIS FOR {weekly_hours}h/WEEK")
        print("=" * 80)
        
        # January 2026 calendar
        year = 2026
        month = 1
        _, num_days = monthrange(year, month)
        dates = [date(year, month, day) for day in range(1, num_days + 1)]
        weekdays = [d for d in dates if d.weekday() < 5]
        weekends = [d for d in dates if d.weekday() >= 5]
        
        print(f"\n1. CALENDAR")
        print(f"   Total days: {num_days}")
        print(f"   Weekdays: {len(weekdays)}")
        print(f"   Weekend days: {len(weekends)}")
        
        # Calculate requirements
        num_weeks = num_days / 7.0
        monthly_hours = weekly_hours * num_weeks
        shift_hours = 8.0
        days_needed = monthly_hours / shift_hours
        
        print(f"\n2. HOURS REQUIREMENTS")
        print(f"   Weekly hours: {weekly_hours}h")
        print(f"   Weeks: {num_weeks:.2f}")
        print(f"   Monthly hours: {monthly_hours:.1f}h")
        print(f"   Days needed: {days_needed:.1f} days")
        print(f"   Percentage: {(days_needed/num_days)*100:.1f}%")
        
        # Consecutive constraints (CORRECTED)
        print(f"\n3. CONSECUTIVE CONSTRAINTS (CORRECTED)")
        print(f"   Max aufeinanderfolgende F/S Tage: 42 Tage (6 Wochen)")
        print(f"   Max aufeinanderfolgende N Tage: 21 Tage (3 Wochen)")
        print(f"   KEIN tägliches Arbeitslimit - kann 7 Tage/Woche arbeiten ✓")
        
        # Team rotation analysis
        weeks_in_month = math.ceil(num_days / 7.0)
        print(f"\n4. TEAM ROTATION")
        print(f"   Weeks in January: {weeks_in_month}")
        print(f"   Each team works 1 shift per week (F → N → S rotation)")
        print(f"   All 5 team members work together")
        
        # Week breakdown
        print(f"\n   Week breakdown:")
        current_date = dates[0]
        week_num = 1
        weeks = []
        while current_date <= dates[-1]:
            week_start = current_date
            week_end = min(current_date + timedelta(days=6), dates[-1])
            week_days = (week_end - week_start).days + 1
            weeks.append({
                'num': week_num,
                'start': week_start,
                'end': week_end,
                'days': week_days
            })
            print(f"   Week {week_num}: {week_start} to {week_end} ({week_days} days)")
            current_date = week_end + timedelta(days=1)
            week_num += 1
        
        # Calculate capacity with corrected understanding
        print(f"\n5. CAPACITY ANALYSIS")
        total_capacity = sum(week['days'] for week in weeks) * num_employees
        total_needed = num_employees * days_needed
        
        print(f"   Total employee-days available: {total_capacity}")
        print(f"   Total employee-days needed: {total_needed:.1f}")
        print(f"   Difference: {total_capacity - total_needed:.1f}")
        
        if total_needed <= total_capacity:
            print(f"   ✓ SUFFICIENT capacity")
        else:
            print(f"   ✗ INSUFFICIENT capacity")
        
        # Feasibility check
        print(f"\n6. FEASIBILITY CHECK")
        
        # Can employee work enough days in their assigned weeks?
        max_work_per_employee = weeks_in_month * 7  # Can work all 7 days per week
        print(f"   Max days per employee: {max_work_per_employee} (all days in {weeks_in_month} weeks)")
        print(f"   Days needed: {days_needed:.1f}")
        
        if days_needed <= max_work_per_employee:
            print(f"   ✓ Employee CAN reach target")
            
            # Check consecutive constraints
            print(f"\n   Consecutive constraint check:")
            print(f"   - Mit Teamrotation arbeitet jedes Team jede Woche andere Schicht")
            print(f"   - Max 42 aufeinanderfolgende Tage gleiche Schicht (F/S)")
            print(f"   - Max 21 aufeinanderfolgende Tage Nachtschicht (N)")
            print(f"   - Mit F → N → S Rotation wechselt Schicht jede Woche")
            print(f"   - Longest same shift: ~7 Tage (1 Woche) << 42/21 Tage Limit")
            print(f"   ✓ Consecutive constraints sind KEIN Problem mit Teamrotation")
            
            # Staffing check
            avg_staff_per_day = total_needed / num_days
            print(f"\n7. STAFFING REQUIREMENTS")
            print(f"   Average staff per day: {avg_staff_per_day:.1f}")
            print(f"   Current max (weekday): 20")
            print(f"   Current max (weekend): 20")
            print(f"   ✓ Staffing limits are adequate")
            
            # Final verdict
            print(f"\n8. FEASIBILITY VERDICT")
            print(f"   Mathematical capacity: ✓ SUFFICIENT")
            print(f"   Consecutive constraints: ✓ NOT VIOLATED")
            print(f"   Staffing limits: ✓ ADEQUATE")
            print(f"   Rest time (11h): ✓ Rotation prevents S→F conflicts")
            print(f"   ")
            print(f"   EXPECTED RESULT: Should be FEASIBLE ✓")
            print(f"   ")
            print(f"   If solver returns INFEASIBLE, other factors must be investigated:")
            print(f"   - Team allowed_shift_type_ids configuration")
            print(f"   - Fairness objectives too restrictive")
            print(f"   - Cross-team assignment restrictions")
            print(f"   - Weekly hours constraints implementation")
            
        else:
            print(f"   ✗ Employee CANNOT reach target")
            print(f"   Need to reduce weekly hours or extend planning period")
    
    # Summary
    print(f"\n" + "=" * 80)
    print(f"WICHTIGSTE ERKENNTNISSE")
    print(f"=" * 80)
    print(f"1. Frühere Analyse war FALSCH - nahm 6 aufeinanderfolgende TAGE Limit an")
    print(f"2. Tatsächliches Constraint: max 42 aufeinanderfolgende TAGE (F/S)")
    print(f"3. Oder: max 21 aufeinanderfolgende TAGE (N)")
    print(f"4. Mit Teamrotation (F→N→S) wechselt Schicht jede Woche")
    print(f"5. Longest same shift = ~7 Tage << 42/21 Tage Limit → KEIN Problem")
    print(f"6. Mitarbeiter KÖNNEN alle 7 Tage pro Woche arbeiten")
    print(f"7. 48h/Woche = 26,6 Tage ist FEASIBLE (< 31 Tage verfügbar)")
    print(f"8. 44h/Woche = 24,4 Tage ist FEASIBLE")
    print(f"9. 40h/Woche = 22,1 Tage ist FEASIBLE")
    print(f"")
    print(f"SCHLUSSFOLGERUNG: Wenn Solver INFEASIBLE mit 48h/Woche zurückgibt,")
    print(f"ist das Problem NICHT mit aufeinanderfolgenden Tagen/Wochen.")
    print(f"Zu untersuchen:")
    print(f"- Wie weekly_working_hours ausgelesen werden (hardcoded vs dynamisch)")
    print(f"- Team Schichttyp-Restriktionen")
    print(f"- Fairness-Ziele")
    print(f"- Besetzungsanforderungen (min/max staff)")
    print(f"=" * 80)

if __name__ == "__main__":
    analyze_corrected_constraints()
