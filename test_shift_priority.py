#!/usr/bin/env python3
"""
Test script to validate shift type prioritization: Früh (F) > Spät (S) > Nacht (N).

This test verifies that when filling shifts, the solver prioritizes:
1. Early shift (F) - highest priority
2. Late shift (S) - medium priority  
3. Night shift (N) - lowest priority
"""

from datetime import date
from data_loader import generate_sample_data
from model import create_shift_planning_model
from solver import ShiftPlanningSolver
from entities import ShiftType

# Define shift types with identical limits to observe pure priority effect
# All shifts have same min/max so we can see which gets filled first
TEST_SHIFT_TYPES = [
    ShiftType(1, "F", "Frühdienst", "05:45", "13:45", "#FFD700", 8.0, 48.0, 
              min_staff_weekday=3, max_staff_weekday=6,
              min_staff_weekend=2, max_staff_weekend=3,
              works_monday=True, works_tuesday=True, works_wednesday=True, 
              works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True),
    ShiftType(2, "S", "Spätdienst", "13:45", "21:45", "#FF6347", 8.0, 48.0,
              min_staff_weekday=3, max_staff_weekday=6,
              min_staff_weekend=2, max_staff_weekend=3,
              works_monday=True, works_tuesday=True, works_wednesday=True,
              works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True),
    ShiftType(3, "N", "Nachtdienst", "21:45", "05:45", "#4169E1", 8.0, 48.0,
              min_staff_weekday=3, max_staff_weekday=6,
              min_staff_weekend=2, max_staff_weekend=3,
              works_monday=True, works_tuesday=True, works_wednesday=True,
              works_thursday=True, works_friday=True, works_saturday=True, works_sunday=True),
    ShiftType(4, "ZD", "Zwischendienst", "08:00", "16:00", "#90EE90", 8.0, 40.0, 3, 20, 2, 20, 
              True, True, True, True, True, False, False),
    ShiftType(5, "BMT", "Brandmeldetechniker", "06:00", "14:00", "#FFA500", 8.0, 40.0, 1, 20, 0, 20, 
              True, True, True, True, True, False, False),
    ShiftType(6, "BSB", "Brandschutzbeauftragter", "07:00", "16:30", "#9370DB", 9.5, 40.0, 1, 20, 0, 20, 
              True, True, True, True, True, False, False),
]

def test_shift_priority():
    """Test that shifts are filled in priority order: F > S > N"""
    
    print("=" * 80)
    print("SHIFT PRIORITY TEST (F > S > N)")
    print("=" * 80)
    print("\nGenerating sample data...")
    employees, teams, absences = generate_sample_data()
    
    # Use a short planning period
    start_date = date(2026, 1, 26)  # Monday
    end_date = date(2026, 1, 31)    # Saturday (6 days, 5 weekdays + 1 weekend)
    
    print(f"\nPlanning period: {start_date} to {end_date}")
    print(f"Days: {(end_date - start_date).days + 1}")
    print(f"Employees: {len(employees)}")
    print(f"Teams: {len(teams)}")
    
    # Print staffing configuration (all equal to isolate priority effect)
    print("\n" + "=" * 80)
    print("STAFFING CONFIGURATION (All shifts have same limits)")
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
        shift_types=TEST_SHIFT_TYPES
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
    
    # Collect weekday data only
    weekday_totals = {shift: {'count': 0, 'days': 0, 'gaps': 0} for shift in shift_codes}
    
    for d in dates:
        if d.weekday() >= 5:  # Skip weekends for this test
            continue
            
        day_name = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'][d.weekday()]
        
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
                max_staff = st.max_staff_weekday
                gap = max_staff - count
                gap_str = f" (gap: {gap})" if gap > 0 else ""
                print(f"  {shift}: {count}/{max_staff}{gap_str}")
                
                weekday_totals[shift]['count'] += count
                weekday_totals[shift]['days'] += 1
                if gap > 0:
                    weekday_totals[shift]['gaps'] += gap
    
    # Calculate fill percentages
    print("\n" + "=" * 80)
    print("WEEKDAY FILL ANALYSIS")
    print("=" * 80)
    
    fill_percentages = {}
    for shift in shift_codes:
        if weekday_totals[shift]['days'] > 0:
            st = next((s for s in TEST_SHIFT_TYPES if s.code == shift), None)
            max_possible = st.max_staff_weekday * weekday_totals[shift]['days']
            actual = weekday_totals[shift]['count']
            fill_pct = (actual / max_possible * 100) if max_possible > 0 else 0
            fill_percentages[shift] = fill_pct
            
            shift_name = {'F': 'Früh', 'S': 'Spät', 'N': 'Nacht'}[shift]
            print(f"{shift_name} ({shift}): {actual}/{max_possible} positions filled = {fill_pct:.1f}%")
            print(f"  Total gaps: {weekday_totals[shift]['gaps']}")
    
    # Validate priority order
    print("\n" + "=" * 80)
    print("PRIORITY VALIDATION")
    print("=" * 80)
    
    success = True
    
    # F should have highest fill percentage
    if fill_percentages.get('F', 0) >= fill_percentages.get('S', 0):
        print(f"✅ PASS: Früh (F) fill % ({fill_percentages['F']:.1f}%) >= Spät (S) fill % ({fill_percentages['S']:.1f}%)")
    else:
        print(f"❌ FAIL: Früh (F) fill % ({fill_percentages['F']:.1f}%) < Spät (S) fill % ({fill_percentages['S']:.1f}%)")
        success = False
    
    # S should have higher or equal fill percentage than N
    if fill_percentages.get('S', 0) >= fill_percentages.get('N', 0):
        print(f"✅ PASS: Spät (S) fill % ({fill_percentages['S']:.1f}%) >= Nacht (N) fill % ({fill_percentages['N']:.1f}%)")
    else:
        print(f"❌ FAIL: Spät (S) fill % ({fill_percentages['S']:.1f}%) < Nacht (N) fill % ({fill_percentages['N']:.1f}%)")
        success = False
    
    # Overall priority order
    if fill_percentages.get('F', 0) >= fill_percentages.get('S', 0) >= fill_percentages.get('N', 0):
        print(f"\n✅ OVERALL: Priority order F > S > N is respected!")
        print(f"   F: {fill_percentages['F']:.1f}% >= S: {fill_percentages['S']:.1f}% >= N: {fill_percentages['N']:.1f}%")
    else:
        print(f"\n❌ OVERALL: Priority order F > S > N is NOT respected!")
        print(f"   F: {fill_percentages['F']:.1f}%, S: {fill_percentages['S']:.1f}%, N: {fill_percentages['N']:.1f}%")
        success = False
    
    if success:
        print("\n" + "=" * 80)
        print("✅ TEST PASSED: Shift priority order (F > S > N) is working correctly!")
        print("=" * 80)
        return True
    else:
        print("\n" + "=" * 80)
        print("❌ TEST FAILED: Shift priority order is not being respected")
        print("=" * 80)
        return False

if __name__ == "__main__":
    success = test_shift_priority()
    exit(0 if success else 1)
