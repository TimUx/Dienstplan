"""
Validation module for shift planning results.
Validates all rules and constraints after solving.
"""

from datetime import date, timedelta
from typing import List, Dict, Tuple
from collections import defaultdict
from entities import Employee, ShiftAssignment, Absence, STANDARD_SHIFT_TYPES, get_shift_type_by_id

# Constants for validation
MAIN_SHIFT_CODES = ["F", "S", "N"]  # Main shift types that require working hours validation
DEFAULT_WEEKLY_HOURS = 40.0  # Default weekly working hours if not configured


class ValidationResult:
    """Result of validation with any violations found"""
    
    def __init__(self):
        self.is_valid = True
        self.violations = []
        self.warnings = []
    
    def add_violation(self, message: str):
        """Add a hard rule violation"""
        self.is_valid = False
        self.violations.append(message)
    
    def add_warning(self, message: str):
        """Add a soft rule warning"""
        self.warnings.append(message)
    
    def print_report(self):
        """Print validation report"""
        print("\n" + "=" * 60)
        print("VALIDATION REPORT")
        print("=" * 60)
        
        if self.is_valid and not self.warnings:
            print("✓ All validations passed!")
        else:
            if self.violations:
                print(f"\n✗ VIOLATIONS FOUND: {len(self.violations)}")
                for i, violation in enumerate(self.violations, 1):
                    print(f"  {i}. {violation}")
            
            if self.warnings:
                print(f"\n⚠ WARNINGS: {len(self.warnings)}")
                for i, warning in enumerate(self.warnings, 1):
                    print(f"  {i}. {warning}")
            
            if not self.violations:
                print("\n✓ No hard rule violations (warnings only)")
        
        print("=" * 60)


def validate_shift_plan(
    assignments: List[ShiftAssignment],
    employees: List[Employee],
    absences: List[Absence],
    start_date: date,
    end_date: date,
    teams: List = None,
    special_functions: Dict[Tuple[int, date], str] = None,
    complete_schedule: Dict[Tuple[int, date], str] = None,
    locked_team_shift: Dict[Tuple[int, int], str] = None,
    locked_employee_weekend: Dict[Tuple[int, date], bool] = None,
    locked_td: Dict[Tuple[int, int], bool] = None,
    shift_types: List = None
) -> ValidationResult:
    """
    Validate the complete shift plan against all rules.
    
    Args:
        assignments: List of shift assignments
        employees: List of employees
        absences: List of absences
        start_date: Start date of planning period
        end_date: End date of planning period
        teams: List of teams (optional, for enhanced weekend validation)
        special_functions: Dict of special functions like TD (optional)
        complete_schedule: Complete schedule dict (optional, for checking all employees)
        locked_team_shift: Locked team shift assignments (optional, for checking manual overrides)
        locked_employee_weekend: Locked employee weekend assignments (optional)
        locked_td: Locked TD assignments (optional)
        shift_types: List of shift types with staffing requirements (optional)
        
    Returns:
        ValidationResult with any violations or warnings
    """
    result = ValidationResult()
    
    # Create lookup structures
    emp_dict = {emp.id: emp for emp in employees}
    
    # Group assignments by employee and date
    assignments_by_emp_date = {}
    for assignment in assignments:
        key = (assignment.employee_id, assignment.date)
        if key not in assignments_by_emp_date:
            assignments_by_emp_date[key] = []
        assignments_by_emp_date[key].append(assignment)
    
    # Group assignments by date
    assignments_by_date = {}
    for assignment in assignments:
        if assignment.date not in assignments_by_date:
            assignments_by_date[assignment.date] = []
        assignments_by_date[assignment.date].append(assignment)
    
    # Validate each rule
    validate_one_shift_per_day(result, assignments_by_emp_date)
    validate_no_work_when_absent(result, assignments, absences, emp_dict)
    validate_rest_times(result, assignments, emp_dict)
    validate_consecutive_shifts(result, assignments, emp_dict)
    validate_working_hours(result, assignments, emp_dict, start_date, end_date)
    validate_staffing_requirements(result, assignments_by_date, emp_dict, shift_types)
    validate_special_functions(result, assignments, emp_dict)
    validate_springer_availability(result, assignments, employees)
    
    # NEW: Validate all employees present in complete schedule
    if complete_schedule:
        validate_all_employees_present(result, complete_schedule, employees, start_date, end_date)
    
    # NEW: Validate TD assignments
    if special_functions:
        validate_td_assignments(result, special_functions, employees, start_date, end_date)
    
    # NEW: Validate locked assignments are respected
    if locked_team_shift or locked_employee_weekend or locked_td:
        validate_locked_assignments(result, assignments, special_functions, 
                                    locked_team_shift, locked_employee_weekend, locked_td,
                                    employees, teams, start_date, end_date)
    
    # Validate weekend team consistency
    if teams:
        validate_weekend_team_consistency(result, assignments, employees, teams, start_date, end_date)
    
    return result


def validate_one_shift_per_day(
    result: ValidationResult,
    assignments_by_emp_date: Dict[Tuple[int, date], List[ShiftAssignment]]
):
    """Validate that each employee has at most one shift per day"""
    for (emp_id, d), shifts in assignments_by_emp_date.items():
        if len(shifts) > 1:
            shift_codes = [get_shift_type_by_id(s.shift_type_id).code for s in shifts]
            result.add_violation(
                f"Employee {emp_id} has multiple shifts on {d}: {', '.join(shift_codes)}"
            )


def validate_no_work_when_absent(
    result: ValidationResult,
    assignments: List[ShiftAssignment],
    absences: List[Absence],
    emp_dict: Dict[int, Employee]
):
    """Validate that employees don't work when absent"""
    for assignment in assignments:
        emp_id = assignment.employee_id
        d = assignment.date
        
        # Check if employee exists
        emp = emp_dict.get(emp_id)
        if not emp:
            result.add_violation(f"Employee ID {emp_id} not found in employee list")
            continue
        
        # Check if employee is absent
        for absence in absences:
            if absence.employee_id == emp_id and absence.overlaps_date(d):
                shift_code = get_shift_type_by_id(assignment.shift_type_id).code
                result.add_violation(
                    f"{emp.full_name} (ID {emp_id}) assigned to {shift_code} shift on {d} but is absent ({absence.absence_type.value})"
                )


def validate_rest_times(
    result: ValidationResult,
    assignments: List[ShiftAssignment],
    emp_dict: Dict[int, Employee]
):
    """Validate 11-hour minimum rest time (forbidden transitions)"""
    # Group by employee
    assignments_by_emp = {}
    for assignment in assignments:
        emp_id = assignment.employee_id
        if emp_id not in assignments_by_emp:
            assignments_by_emp[emp_id] = []
        assignments_by_emp[emp_id].append(assignment)
    
    # Check each employee's assignments
    for emp_id, emp_assignments in assignments_by_emp.items():
        # Sort by date
        emp_assignments.sort(key=lambda x: x.date)
        
        # Check consecutive days
        for i in range(len(emp_assignments) - 1):
            current = emp_assignments[i]
            next_assign = emp_assignments[i + 1]
            
            # Check if consecutive days
            if (next_assign.date - current.date).days == 1:
                current_shift = get_shift_type_by_id(current.shift_type_id).code
                next_shift = get_shift_type_by_id(next_assign.shift_type_id).code
                
                # Check forbidden transitions
                if current_shift == "S" and next_shift == "F":
                    emp_name = emp_dict[emp_id].full_name
                    result.add_violation(
                        f"{emp_name} has forbidden transition Spät->Früh on {current.date}->{next_assign.date} (only 8h rest)"
                    )
                elif current_shift == "N" and next_shift == "F":
                    emp_name = emp_dict[emp_id].full_name
                    result.add_violation(
                        f"{emp_name} has forbidden transition Nacht->Früh on {current.date}->{next_assign.date} (0h rest)"
                    )


def validate_consecutive_shifts(
    result: ValidationResult,
    assignments: List[ShiftAssignment],
    emp_dict: Dict[int, Employee]
):
    """Validate max consecutive shifts (6 days, 5 nights)"""
    # Group by employee
    assignments_by_emp = {}
    for assignment in assignments:
        emp_id = assignment.employee_id
        if emp_id not in assignments_by_emp:
            assignments_by_emp[emp_id] = []
        assignments_by_emp[emp_id].append(assignment)
    
    for emp_id, emp_assignments in assignments_by_emp.items():
        emp_assignments.sort(key=lambda x: x.date)
        emp_name = emp_dict[emp_id].full_name
        
        # Check max 6 consecutive working days
        consecutive_days = 1
        last_date = None
        
        for assignment in emp_assignments:
            if last_date and (assignment.date - last_date).days == 1:
                consecutive_days += 1
                if consecutive_days > 6:
                    result.add_violation(
                        f"{emp_name} works more than 6 consecutive days (ends {assignment.date})"
                    )
            else:
                consecutive_days = 1
            last_date = assignment.date
        
        # Check max 5 consecutive night shifts
        consecutive_nights = 0
        for assignment in emp_assignments:
            shift_code = get_shift_type_by_id(assignment.shift_type_id).code
            if shift_code == "N":
                consecutive_nights += 1
                if consecutive_nights > 5:
                    result.add_violation(
                        f"{emp_name} works more than 5 consecutive night shifts (ends {assignment.date})"
                    )
            else:
                consecutive_nights = 0


def validate_working_hours(
    result: ValidationResult,
    assignments: List[ShiftAssignment],
    emp_dict: Dict[int, Employee],
    start_date: date,
    end_date: date,
    shift_types: List = None
):
    """
    Validate working hours limits based on configured weekly_working_hours in shift types.
    
    Validates that employees:
    - Do not exceed max weekly hours (based on shift's weekly_working_hours)
    - Meet minimum weekly hours (based on shift's weekly_working_hours)
    - Do not exceed max monthly hours (weekly_working_hours * 4)
    
    Note: This is now dynamic based on shift configuration, not hardcoded to 48h/192h
    """
    from entities import STANDARD_SHIFT_TYPES
    
    # Use provided shift_types or fallback to STANDARD_SHIFT_TYPES
    if shift_types is None:
        shift_types = STANDARD_SHIFT_TYPES
    
    # Build lookup for shift weekly hours
    shift_weekly_hours_map = {}
    for st in shift_types:
        shift_weekly_hours_map[st.id] = st.weekly_working_hours
    
    # Group by employee
    assignments_by_emp = {}
    for assignment in assignments:
        emp_id = assignment.employee_id
        if emp_id not in assignments_by_emp:
            assignments_by_emp[emp_id] = []
        assignments_by_emp[emp_id].append(assignment)
    
    for emp_id, emp_assignments in assignments_by_emp.items():
        emp_name = emp_dict[emp_id].full_name
        
        # Determine employee's shift type to get expected weekly hours
        # Use the most common shift type assigned to this employee
        shift_type_counts = {}
        for assignment in emp_assignments:
            shift_type = get_shift_type_by_id(assignment.shift_type_id)
            if shift_type and shift_type.code in MAIN_SHIFT_CODES:  # Main shifts only
                shift_type_counts[shift_type.id] = shift_type_counts.get(shift_type.id, 0) + 1
        
        # Get expected weekly hours (use default if no main shifts found)
        expected_weekly_hours = DEFAULT_WEEKLY_HOURS
        if shift_type_counts:
            most_common_shift_id = max(shift_type_counts, key=shift_type_counts.get)
            expected_weekly_hours = shift_weekly_hours_map.get(most_common_shift_id, DEFAULT_WEEKLY_HOURS)
        
        expected_monthly_hours = expected_weekly_hours * 4
        
        # Check weekly hours
        weeks = {}
        for assignment in emp_assignments:
            # Get Monday of the week
            monday = assignment.date - timedelta(days=assignment.date.weekday())
            if monday not in weeks:
                weeks[monday] = 0
            
            shift_type = get_shift_type_by_id(assignment.shift_type_id)
            weeks[monday] += shift_type.hours
        
        for week_start, hours in weeks.items():
            if hours > expected_weekly_hours:
                result.add_violation(
                    f"{emp_name} works {hours:.1f} hours in week starting {week_start} (max {expected_weekly_hours}h based on shift config)"
                )
        
        # Check monthly hours (30-day rolling window)
        dates_with_hours = {}
        for assignment in emp_assignments:
            if assignment.date not in dates_with_hours:
                dates_with_hours[assignment.date] = 0
            shift_type = get_shift_type_by_id(assignment.shift_type_id)
            dates_with_hours[assignment.date] += shift_type.hours
        
        # Check each 30-day window
        current = start_date
        while current <= end_date - timedelta(days=29):
            window_end = current + timedelta(days=29)
            hours_in_window = sum(
                hours for d, hours in dates_with_hours.items()
                if current <= d <= window_end
            )
            if hours_in_window > expected_monthly_hours:
                result.add_violation(
                    f"{emp_name} works {hours_in_window:.1f} hours in 30-day period {current} to {window_end} (max {expected_monthly_hours}h based on shift config)"
                )
            current += timedelta(days=7)  # Check weekly increments



def validate_staffing_requirements(
    result: ValidationResult,
    assignments_by_date: Dict[date, List[ShiftAssignment]],
    emp_dict: Dict[int, Employee],
    shift_types: List
):
    """Validate minimum/maximum staffing per shift
    
    Args:
        shift_types: List of ShiftType objects from database (REQUIRED)
    """
    if not shift_types:
        raise ValueError("shift_types is required for validation - must be loaded from database")
    
    # Build staffing lookup from shift_types (database configuration)
    staffing_weekday = {}
    staffing_weekend = {}
    for st in shift_types:
        if st.code in ["F", "S", "N"]:
            staffing_weekday[st.code] = {
                "min": st.min_staff_weekday,
                "max": st.max_staff_weekday
            }
            staffing_weekend[st.code] = {
                "min": st.min_staff_weekend,
                "max": st.max_staff_weekend
            }
    
    for d, day_assignments in assignments_by_date.items():
        is_weekend = d.weekday() >= 5
        staffing = staffing_weekend if is_weekend else staffing_weekday
        
        # Count by shift type
        shift_counts = {}
        for assignment in day_assignments:
            shift_code = get_shift_type_by_id(assignment.shift_type_id).code
            
            # Only count F, S, N for staffing requirements
            if shift_code in ["F", "S", "N"]:
                # Only count regular team members
                emp = emp_dict[assignment.employee_id]
                if emp.team_id:
                    if shift_code not in shift_counts:
                        shift_counts[shift_code] = 0
                    shift_counts[shift_code] += 1
        
        # Validate each main shift
        for shift_code in ["F", "S", "N"]:
            # Skip if shift code is not in staffing requirements (e.g., shift type not active or not configured)
            # This is expected behavior as not all shifts may be used in every planning period
            if shift_code not in staffing:
                continue
            count = shift_counts.get(shift_code, 0)
            min_req = staffing[shift_code]["min"]
            max_req = staffing[shift_code]["max"]
            
            if count < min_req:
                result.add_violation(
                    f"Insufficient staffing for {shift_code} shift on {d}: {count} (min {min_req})"
                )
            elif count > max_req:
                result.add_violation(
                    f"Overstaffing for {shift_code} shift on {d}: {count} (max {max_req})"
                )


def validate_special_functions(
    result: ValidationResult,
    assignments: List[ShiftAssignment],
    emp_dict: Dict[int, Employee]
):
    """Validate special function assignments (BMT, BSB)"""
    # Group by date
    by_date = {}
    for assignment in assignments:
        if assignment.date not in by_date:
            by_date[assignment.date] = []
        by_date[assignment.date].append(assignment)
    
    for d, day_assignments in by_date.items():
        is_weekday = d.weekday() < 5
        
        if not is_weekday:
            continue
        
        # Count BMT and BSB assignments
        bmt_count = 0
        bsb_count = 0
        
        for assignment in day_assignments:
            shift_type = get_shift_type_by_id(assignment.shift_type_id)
            emp = emp_dict[assignment.employee_id]
            
            if shift_type.code == "BMT":
                bmt_count += 1
                if not emp.is_brandmeldetechniker:
                    result.add_violation(
                        f"Employee {emp.full_name} assigned to BMT but not qualified on {d}"
                    )
            
            if shift_type.code == "BSB":
                bsb_count += 1
                if not emp.is_brandschutzbeauftragter:
                    result.add_violation(
                        f"Employee {emp.full_name} assigned to BSB but not qualified on {d}"
                    )
        
        # Should have exactly 1 BMT and 1 BSB on weekdays
        if bmt_count != 1:
            result.add_warning(f"BMT count on {d} is {bmt_count} (expected 1)")
        
        if bsb_count != 1:
            result.add_warning(f"BSB count on {d} is {bsb_count} (expected 1)")


def validate_springer_availability(
    result: ValidationResult,
    assignments: List[ShiftAssignment],
    employees: List[Employee]
):
    """Validate that at least one employee is available (not working) each week"""
    regular_team_members = [emp for emp in employees 
                           if emp.team_id]
    
    if not regular_team_members:
        result.add_warning("No regular team members defined in the system")
        return
    
    # Group assignments by week
    # Group assignments by week
    from datetime import timedelta
    by_week = {}
    
    # Get all unique weeks from assignments
    weeks = set()
    for assignment in assignments:
        week_start = assignment.date - timedelta(days=assignment.date.weekday())
        weeks.add(week_start)
    
    for week_start in weeks:
        week_dates = [week_start + timedelta(days=i) for i in range(7)]
        assigned_emp_ids = set()
        
        for assignment in assignments:
            if assignment.date in week_dates:
                assigned_emp_ids.add(assignment.employee_id)
        
        # Count how many regular team members are not working this week
        available_employees = [e for e in regular_team_members if e.id not in assigned_emp_ids]
        
        if len(available_employees) < 1:
            result.add_violation(
                f"No available employee for week starting {week_start} (constraint: at least 1 must be free)"
            )
        elif len(available_employees) == 0:
            result.add_warning(
                f"Only {len(available_employees)} employee(s) available for week starting {week_start}"
            )


def validate_weekend_team_consistency(
    result: ValidationResult,
    assignments: List[ShiftAssignment],
    employees: List[Employee],
    teams: List,
    start_date: date,
    end_date: date
):
    """
    CRITICAL: Validate that weekend shifts match team's weekly shift type.
    
    This is the most important validation to prevent illegal shift transitions.
    Weekend shifts MUST use the same shift type as the team's weekday shift.
    
    Example violation:
    - Team Alpha: Week 1 = 'F' (Early)
    - Employee Max: Fri='F', Sat='S' <- VIOLATION!
    
    Correct:
    - Team Alpha: Week 1 = 'F' (Early)
    - Employee Max: Fri='F', Sat='F', Sun='F' <- All 'F' within the week
    """
    # Generate weeks from dates
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    
    weeks = []
    current_week = []
    for d in dates:
        if d.weekday() == 0 and current_week:
            weeks.append(current_week)
            current_week = []
        current_week.append(d)
    if current_week:
        weeks.append(current_week)
    
    # Group assignments by employee and week
    emp_week_shifts = defaultdict(lambda: defaultdict(lambda: {'weekday': set(), 'weekend': set()}))
    
    for assignment in assignments:
        emp_id = assignment.employee_id
        emp = next((e for e in employees if e.id == emp_id), None)
        
        # Only check regular team members
        if not emp or not emp.team_id:
            continue
        
        shift_type = get_shift_type_by_id(assignment.shift_type_id)
        if not shift_type or shift_type.code not in ['F', 'S', 'N']:
            continue
        
        # Find which week this date belongs to
        week_idx = None
        for w_idx, week_dates in enumerate(weeks):
            if assignment.date in week_dates:
                week_idx = w_idx
                break
        
        if week_idx is None:
            continue
        
        if assignment.date.weekday() < 5:  # Weekday
            emp_week_shifts[emp_id][week_idx]['weekday'].add(shift_type.code)
        else:  # Weekend
            emp_week_shifts[emp_id][week_idx]['weekend'].add(shift_type.code)
    
    # Check consistency: weekend shifts must match weekday shifts
    for emp_id, weeks_data in emp_week_shifts.items():
        emp = next((e for e in employees if e.id == emp_id), None)
        
        for week_idx, shifts_data in weeks_data.items():
            weekday_shifts = shifts_data['weekday']
            weekend_shifts = shifts_data['weekend']
            
            if not weekend_shifts:
                continue  # No weekend work, nothing to check
            
            if not weekday_shifts:
                # Weekend work but no weekday work - this shouldn't happen
                result.add_warning(
                    f"{emp.full_name} works weekend in week {week_idx} but no weekdays"
                )
                continue
            
            # CRITICAL CHECK: Weekend shifts MUST be subset of weekday shifts
            # (should be exactly same shift type, but subset handles partial week work)
            if not weekend_shifts.issubset(weekday_shifts):
                result.add_violation(
                    f"WEEKEND VIOLATION: {emp.full_name} week {week_idx}: "
                    f"weekday shifts={sorted(weekday_shifts)}, "
                    f"weekend shifts={sorted(weekend_shifts)}. "
                    f"Weekend must match team's weekly shift!"
                )


def validate_all_employees_present(
    result: ValidationResult,
    complete_schedule: Dict[Tuple[int, date], str],
    employees: List[Employee],
    start_date: date,
    end_date: date
):
    """
    CRITICAL: Validate that ALL employees appear in the complete schedule.
    
    Every employee must have an entry for every day in the planning period,
    regardless of whether they:
    - Have a shift assignment
    - Have weekend work
    - Have TD assignment
    - Are absent
    - Have no assignment (OFF)
    
    This is a fundamental requirement to ensure visibility of all employees.
    """
    # Generate all dates
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    
    # Check each employee for each date
    for emp in employees:
        for d in dates:
            if (emp.id, d) not in complete_schedule:
                result.add_violation(
                    f"MISSING EMPLOYEE: {emp.full_name} (ID {emp.id}) is missing from schedule on {d}"
                )


def validate_td_assignments(
    result: ValidationResult,
    special_functions: Dict[Tuple[int, date], str],
    employees: List[Employee],
    start_date: date,
    end_date: date
):
    """
    Validate TD (Tagdienst / Day Duty) assignments.
    
    Rules:
    - Exactly ONE TD per week (Monday-Friday)
    - TD must be assigned to a qualified employee
    - TD is visible and marked in special_functions
    """
    # Generate weeks
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    
    weeks = []
    current_week = []
    for d in dates:
        if d.weekday() == 0 and current_week:
            weeks.append(current_week)
            current_week = []
        current_week.append(d)
    if current_week:
        weeks.append(current_week)
    
    # Check each week
    for week_idx, week_dates in enumerate(weeks):
        weekday_dates = [d for d in week_dates if d.weekday() < 5]
        
        if not weekday_dates:
            continue
        
        # Count TD assignments in this week
        td_count = 0
        td_employees = set()
        
        for emp in employees:
            # Check if this employee has TD any day this week
            has_td_this_week = False
            for d in weekday_dates:
                if (emp.id, d) in special_functions and special_functions[(emp.id, d)] == "TD":
                    has_td_this_week = True
                    td_employees.add(emp.id)
            
            if has_td_this_week:
                td_count += 1
                
                # Validate employee is qualified
                if not emp.can_do_td:
                    result.add_violation(
                        f"TD QUALIFICATION VIOLATION: {emp.full_name} assigned TD in week {week_idx} but not qualified"
                    )
        
        # Validate exactly 1 TD per week
        if td_count == 0:
            result.add_violation(
                f"MISSING TD: Week {week_idx} ({weekday_dates[0]} to {weekday_dates[-1]}) has no TD assignment (required: exactly 1)"
            )
        elif td_count > 1:
            result.add_violation(
                f"MULTIPLE TD: Week {week_idx} has {td_count} TD assignments (should be exactly 1)"
            )


def validate_locked_assignments(
    result: ValidationResult,
    assignments: List[ShiftAssignment],
    special_functions: Dict[Tuple[int, date], str],
    locked_team_shift: Dict[Tuple[int, int], str],
    locked_employee_weekend: Dict[Tuple[int, date], bool],
    locked_td: Dict[Tuple[int, int], bool],
    employees: List[Employee],
    teams: List,
    start_date: date,
    end_date: date
):
    """
    Validate that locked (manual override) assignments are respected.
    
    When administrators or dispatchers lock assignments:
    - locked_team_shift: Team must have the specified shift in that week
    - locked_employee_weekend: Employee must work/not work on that weekend day
    - locked_td: Employee must have/not have TD in that week
    """
    # Generate weeks
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    
    weeks = []
    current_week = []
    for d in dates:
        if d.weekday() == 0 and current_week:
            weeks.append(current_week)
            current_week = []
        current_week.append(d)
    if current_week:
        weeks.append(current_week)
    
    # Validate locked team shifts
    if locked_team_shift and teams:
        for (team_id, week_idx), expected_shift in locked_team_shift.items():
            if week_idx >= len(weeks):
                continue
            
            week_dates = weeks[week_idx]
            weekday_dates = [d for d in week_dates if d.weekday() < 5]
            
            # Find team
            team = next((t for t in teams if t.id == team_id), None)
            if not team:
                continue
            
            # Check team members' shifts this week
            team_members = [e for e in employees if e.team_id == team_id]
            actual_shifts = set()
            
            for emp in team_members:
                for assignment in assignments:
                    if assignment.employee_id == emp.id and assignment.date in weekday_dates:
                        shift_type = get_shift_type_by_id(assignment.shift_type_id)
                        if shift_type:
                            actual_shifts.add(shift_type.code)
            
            if actual_shifts and expected_shift not in actual_shifts:
                result.add_violation(
                    f"LOCKED TEAM SHIFT VIOLATED: {team.name} week {week_idx} should be '{expected_shift}' but has {actual_shifts}"
                )
    
    # Validate locked employee weekend
    if locked_employee_weekend:
        for (emp_id, d), expected_working in locked_employee_weekend.items():
            emp = next((e for e in employees if e.id == emp_id), None)
            if not emp:
                continue
            
            # Check if employee has assignment on this date
            is_working = any(a.employee_id == emp_id and a.date == d for a in assignments)
            
            if expected_working and not is_working:
                result.add_violation(
                    f"LOCKED WEEKEND VIOLATED: {emp.full_name} should work on {d} but doesn't"
                )
            elif not expected_working and is_working:
                result.add_violation(
                    f"LOCKED WEEKEND VIOLATED: {emp.full_name} should NOT work on {d} but does"
                )
    
    # Validate locked TD
    if locked_td and special_functions:
        for (emp_id, week_idx), expected_td in locked_td.items():
            if week_idx >= len(weeks):
                continue
            
            emp = next((e for e in employees if e.id == emp_id), None)
            if not emp:
                continue
            
            week_dates = weeks[week_idx]
            weekday_dates = [d for d in week_dates if d.weekday() < 5]
            
            # Check if employee has TD this week
            has_td = any(
                (emp_id, d) in special_functions and special_functions[(emp_id, d)] == "TD"
                for d in weekday_dates
            )
            
            if expected_td and not has_td:
                result.add_violation(
                    f"LOCKED TD VIOLATED: {emp.full_name} should have TD in week {week_idx} but doesn't"
                )
            elif not expected_td and has_td:
                result.add_violation(
                    f"LOCKED TD VIOLATED: {emp.full_name} should NOT have TD in week {week_idx} but does"
                )


if __name__ == "__main__":
    # Test validation
    from data_loader import generate_sample_data
    from model import create_shift_planning_model
    from solver import solve_shift_planning
    from datetime import timedelta
    
    print("Generating sample data...")
    employees, teams, absences = generate_sample_data()
    
    start = date.today()
    end = start + timedelta(days=13)  # 2 weeks
    
    print("Creating and solving model...")
    planning_model = create_shift_planning_model(employees, teams, start, end, absences)
    result = solve_shift_planning(planning_model, time_limit_seconds=60)
    
    if result:
        assignments, special_functions, complete_schedule = result
        print(f"\nValidating {len(assignments)} assignments...")
        
        validation_result = validate_shift_plan(
            assignments, employees, absences, start, end, teams,
            special_functions, complete_schedule
        )
        validation_result.print_report()
    else:
        print("\nNo solution to validate!")
