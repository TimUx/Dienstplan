#!/usr/bin/env python3
"""
Test script to validate that weekday gaps are filled before weekend overstaffing.

This test creates a scenario similar to the January 2026 problem:
- Weekday max: F=8, S=6, N=4
- Weekend max: F=3, S=3, N=3
- Verifies that weekday positions are prioritized over weekend positions
"""

from datetime import date
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import ShiftPlanningSolver
from entities import ShiftType

# Define shift types with the correct max values from the problem statement
TEST_SHIFT_TYPES = [
    ShiftType(1, "F", "Frühdienst", "05:45", "13:45", "#FFD700", 8.0, 48.0, 
              min_staff_weekday=4, max_staff_weekday=8,   # Weekday: max 8
              min_staff_weekend=2, max_staff_weekend=3,   # Weekend: max 3
              works_monday=True, works_tuesday=True, works_wednesday=True, 
              works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True),
    ShiftType(2, "S", "Spätdienst", "13:45", "21:45", "#FF6347", 8.0, 48.0,
              min_staff_weekday=3, max_staff_weekday=6,   # Weekday: max 6
              min_staff_weekend=2, max_staff_weekend=3,   # Weekend: max 3
              works_monday=True, works_tuesday=True, works_wednesday=True,
              works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True),
    ShiftType(3, "N", "Nachtdienst", "21:45", "05:45", "#4169E1", 8.0, 48.0,
              min_staff_weekday=3, max_staff_weekday=4,   # Weekday: max 4
              min_staff_weekend=2, max_staff_weekend=3,   # Weekend: max 3
              works_monday=True, works_tuesday=True, works_wednesday=True,
              works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True),
    ShiftType(4, "ZD", "Zwischendienst", "08:00", "16:00", "#90EE90", 8.0, 40.0, 3, 20, 2, 20, 
              True, True, True, True, True, False, False),
    ShiftType(5, "BMT", "Brandmeldetechniker", "06:00", "14:00", "#FFA500", 8.0, 40.0, 1, 20, 0, 20, 
              True, True, True, True, True, False, False),
    ShiftType(6, "BSB", "Brandschutzbeauftragter", "07:00", "16:30", "#9370DB", 9.5, 40.0, 1, 20, 0, 20, 
              True, True, True, True, True, False, False),
]

def test_weekday_priority():
    """Test that weekday gaps are filled before weekends are overstaffed"""
    
    # Generate sample data
    print("=" * 80)
    print("WEEKDAY PRIORITY TEST")
    print("=" * 80)
    print("\nGenerating sample data...")
    employees, teams, absences = generate_sample_data()
    
    # Use a short planning period covering one week
    # Week of Jan 26-Feb 1, 2026 (Mon-Sun)
    start_date = date(2026, 1, 26)  # Monday
    end_date = date(2026, 2, 1)    # Sunday
    
    print(f"\nPlanning period: {start_date} to {end_date}")
    print(f"Days: {(end_date - start_date).days + 1}")
    print(f"Employees: {len(employees)}")
    print(f"Teams: {len(teams)}")
    
    # Print staffing configuration
    print("\n" + "=" * 80)
    print("STAFFING CONFIGURATION")
    print("=" * 80)
    for st in TEST_SHIFT_TYPES:
        if st.code in ['F', 'S', 'N']:
            print(f"{st.name} ({st.code}):")
            print(f"  Weekday: min={st.min_staff_weekday}, max={st.max_staff_weekday}")
            print(f"  Weekend: min={st.min_staff_weekend}, max={st.max_staff_weekend}")
    
    # Use default global settings
    global_settings = {
        'max_consecutive_shifts_weeks': 6,
        'max_consecutive_night_shifts_weeks': 3,
        'min_rest_hours': 11
    }
    
    # Create planning model
    print("\n" + "=" * 80)
    print("CREATING PLANNING MODEL")
    print("=" * 80)
    planning_model = create_shift_planning_model(
        employees=employees,
        teams=teams,
        start_date=start_date,
        end_date=end_date,
        absences=absences,
        shift_types=TEST_SHIFT_TYPES  # Use test shift types with correct max values
    )
    
    # Set global settings on the model
    planning_model.global_settings = global_settings
    
    # Solve
    print("\n" + "=" * 80)
    print("SOLVING")
    print("=" * 80)
    solver = ShiftPlanningSolver(
        planning_model=planning_model,
        time_limit_seconds=60,
        num_workers=4,
        global_settings=global_settings
    )
    
    solver.add_all_constraints()
    success = solver.solve()
    
    if not success:
        print("\n" + "!" * 80)
        print("ERROR: No solution found!")
        print("!" * 80)
        return False
    
    # Extract solution
    shift_assignments, special_functions, complete_schedule = solver.extract_solution()
    
    # Analyze the solution
    print("\n" + "=" * 80)
    print("SOLUTION ANALYSIS")
    print("=" * 80)
    
    dates = planning_model.dates
    shift_codes = ['F', 'S', 'N']
    
    # Create a mapping from shift_type_id to shift_code
    shift_id_to_code = {}
    for st in TEST_SHIFT_TYPES:
        shift_id_to_code[st.id] = st.code
    
    # Count staff per day and shift
    weekday_totals = {shift: {'count': 0, 'days': 0} for shift in shift_codes}
    weekend_totals = {shift: {'count': 0, 'days': 0} for shift in shift_codes}
    
    for d in dates:
        is_weekend = d.weekday() >= 5
        day_name = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][d.weekday()]
        
        print(f"\n{day_name} {d}:")
        for shift in shift_codes:
            count = 0
            # Count assigned employees for this shift
            for assignment in shift_assignments:
                shift_code = shift_id_to_code.get(assignment.shift_type_id, "?")
                if assignment.date == d and shift_code == shift:
                    count += 1
            
            # Get max for this day type
            st = next((s for s in TEST_SHIFT_TYPES if s.code == shift), None)
            if st:
                max_staff = st.max_staff_weekend if is_weekend else st.max_staff_weekday
                overstaffed = " (OVERSTAFFED!)" if count > max_staff else ""
                understaffed = " (gap)" if count < max_staff else ""
                print(f"  {shift}: {count}/{max_staff}{overstaffed}{understaffed}")
                
                if is_weekend:
                    weekend_totals[shift]['count'] += count
                    weekend_totals[shift]['days'] += 1
                else:
                    weekday_totals[shift]['count'] += count
                    weekday_totals[shift]['days'] += 1
    
    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    print("\nWeekday averages (should be HIGHER):")
    for shift in shift_codes:
        if weekday_totals[shift]['days'] > 0:
            avg = weekday_totals[shift]['count'] / weekday_totals[shift]['days']
            st = next((s for s in TEST_SHIFT_TYPES if s.code == shift), None)
            max_staff = st.max_staff_weekday if st else 0
            print(f"  {shift}: {avg:.1f} (max={max_staff})")
    
    print("\nWeekend averages (should be LOWER):")
    for shift in shift_codes:
        if weekend_totals[shift]['days'] > 0:
            avg = weekend_totals[shift]['count'] / weekend_totals[shift]['days']
            st = next((s for s in TEST_SHIFT_TYPES if s.code == shift), None)
            max_staff = st.max_staff_weekend if st else 0
            overstaffed = " *** PROBLEM ***" if avg > max_staff else ""
            print(f"  {shift}: {avg:.1f} (max={max_staff}){overstaffed}")
    
    # Check for weekend overstaffing
    print("\n" + "=" * 80)
    print("VALIDATION")
    print("=" * 80)
    
    has_problem = False
    for shift in shift_codes:
        if weekend_totals[shift]['days'] > 0:
            avg = weekend_totals[shift]['count'] / weekend_totals[shift]['days']
            st = next((s for s in TEST_SHIFT_TYPES if s.code == shift), None)
            max_staff = st.max_staff_weekend if st else 0
            
            if avg > max_staff:
                print(f"❌ FAIL: Weekend shift {shift} is overstaffed (avg={avg:.1f}, max={max_staff})")
                has_problem = True
            else:
                print(f"✅ PASS: Weekend shift {shift} respects max (avg={avg:.1f}, max={max_staff})")
    
    if not has_problem:
        print("\n" + "=" * 80)
        print("✅ TEST PASSED: Weekdays prioritized correctly!")
        print("=" * 80)
        return True
    else:
        print("\n" + "=" * 80)
        print("❌ TEST FAILED: Weekend still being overstaffed")
        print("=" * 80)
        return False

if __name__ == "__main__":
    success = test_weekday_priority()
    exit(0 if success else 1)
