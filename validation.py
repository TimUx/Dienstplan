"""
Validation module for shift planning results.
Validates all rules and constraints after solving.
"""

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from entities import Employee, ShiftAssignment, Absence, STANDARD_SHIFT_TYPES, get_shift_type_by_id

# Constants for validation
MAIN_SHIFT_CODES = ["F", "S", "N"]  # Main shift types that require working hours validation
DEFAULT_WEEKLY_HOURS = 40.0  # Default weekly working hours if not configured


@dataclass
class ViolationEntry:
    """A single validation violation or warning with optional cause analysis."""
    message: str
    cause_type: str = "UNKNOWN"  # "ABSENCE", "UNDERSTAFFING", "ROTATION_CONFLICT", "UNKNOWN"
    cause: str = ""


def _analyze_absence_cause(
    check_date: Optional[date],
    absences: List[Absence],
    employees: List[Employee],
    shift_code: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Determine cause_type and a human-readable cause text for a violation.

    Checks whether absences on *check_date* can explain the violation and
    calculates the fraction of absent employees.

    Returns:
        (cause_type, cause_text) where cause_type is one of
        "ABSENCE", "UNDERSTAFFING", or "UNKNOWN".
    """
    if check_date is None:
        return "UNKNOWN", ""

    # Readable shift names for the cause text
    _SHIFT_NAMES: Dict[str, str] = {
        "F": "Frühschicht",
        "S": "Spätschicht",
        "N": "Nachtschicht",
        "ZD": "Zwischendienst",
        "BMT": "BMT-Dienst",
        "BSB": "BSB-Dienst",
    }
    shift_label = _SHIFT_NAMES.get(shift_code, f"{shift_code}schicht") if shift_code else None

    # Find employees absent on check_date
    absent_pairs: List[Tuple[Employee, Absence]] = []
    seen_emp_ids: set = set()
    for emp in employees:
        if emp.id in seen_emp_ids:
            continue
        for absence in absences:
            if absence.employee_id == emp.id and absence.overlaps_date(check_date):
                absent_pairs.append((emp, absence))
                seen_emp_ids.add(emp.id)
                break

    total = len(employees)
    n = len(absent_pairs)

    date_str = check_date.strftime("%d.%m.")
    shift_part = f"{shift_label} am {date_str}" if shift_label else f"am {date_str}"

    if n == 0:
        return "UNDERSTAFFING", (
            f"Ursache: Personalunterbesetzung {shift_part} – keine Abwesenheiten erfasst"
        )

    # Format up to 3 abbreviated names with their absence code
    name_parts = []
    for emp, absence in absent_pairs[:3]:
        abbrev = f"{emp.vorname[0]}. {emp.name}" if emp.vorname else emp.name
        name_parts.append(f"{abbrev} ({absence.get_code()})")
    names_str = ", ".join(name_parts)
    if n > 3:
        names_str += f" (+{n - 3} weitere)"

    cause_text = (
        f"Ursache: {shift_part} – {n} von {total} Mitarbeitern abwesend ({names_str})"
    )
    return "ABSENCE", cause_text


class ValidationResult:
    """Result of validation with any violations found"""
    
    def __init__(self):
        self.is_valid = True
        self.violations: List[ViolationEntry] = []
        self.warnings: List[ViolationEntry] = []
    
    def add_violation(self, message: str, cause_type: str = "UNKNOWN", cause: str = ""):
        """Add a hard rule violation with optional cause analysis"""
        self.is_valid = False
        self.violations.append(ViolationEntry(message=message, cause_type=cause_type, cause=cause))
    
    def add_warning(self, message: str, cause_type: str = "UNKNOWN", cause: str = ""):
        """Add a soft rule warning with optional cause analysis"""
        self.warnings.append(ViolationEntry(message=message, cause_type=cause_type, cause=cause))
    
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
                for i, v in enumerate(self.violations, 1):
                    print(f"  {i}. {v.message}")
                    if v.cause:
                        print(f"     {v.cause}")
            
            if self.warnings:
                print(f"\n⚠ WARNINGS: {len(self.warnings)}")
                for i, v in enumerate(self.warnings, 1):
                    print(f"  {i}. {v.message}")
                    if v.cause:
                        print(f"     {v.cause}")
            
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
    complete_schedule: Dict[Tuple[int, date], str] = None,
    locked_team_shift: Dict[Tuple[int, int], str] = None,
    locked_employee_weekend: Dict[Tuple[int, date], bool] = None,
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
        complete_schedule: Complete schedule dict (optional, for checking all employees)
        locked_team_shift: Locked team shift assignments (optional, for checking manual overrides)
        locked_employee_weekend: Locked employee weekend assignments (optional)
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
    validate_rest_times(result, assignments, emp_dict, absences, employees)
    validate_consecutive_shifts(result, assignments, emp_dict, absences, employees, shift_types)
    validate_minimum_consecutive_weekday_shifts(result, assignments, emp_dict)
    validate_working_hours(result, assignments, emp_dict, start_date, end_date, shift_types, absences, employees)
    validate_staffing_requirements(result, assignments_by_date, emp_dict, shift_types, absences, employees)
    validate_special_functions(result, assignments, emp_dict, absences, employees)
    validate_coverage_availability(result, assignments, employees, absences)
    
    # NEW: Validate all employees present in complete schedule
    if complete_schedule:
        validate_all_employees_present(result, complete_schedule, employees, start_date, end_date)
    
    # NEW: Validate locked assignments are respected
    if locked_team_shift or locked_employee_weekend:
        validate_locked_assignments(result, assignments, 
                                    locked_team_shift, locked_employee_weekend,
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
                f"Employee {emp_id} has multiple shifts on {d}: {', '.join(shift_codes)}",
                cause_type="ROTATION_CONFLICT",
                cause=(
                    f"Ursache: Mehrfachzuweisung am {d.strftime('%d.%m.')} – "
                    f"widersprüchliche Schichten {', '.join(shift_codes)} durch Rotationszwänge"
                ),
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
            result.add_violation(
                f"Employee ID {emp_id} not found in employee list",
                cause_type="UNKNOWN",
                cause="Ursache: Mitarbeiter-ID nicht in der Mitarbeiterliste gefunden",
            )
            continue
        
        # Check if employee is absent
        for absence in absences:
            if absence.employee_id == emp_id and absence.overlaps_date(d):
                shift_code = get_shift_type_by_id(assignment.shift_type_id).code
                result.add_violation(
                    f"{emp.full_name} (ID {emp_id}) assigned to {shift_code} shift on {d} but is absent ({absence.absence_type.value})",
                    cause_type="ABSENCE",
                    cause=(
                        f"Ursache: {emp.full_name} ist am {d.strftime('%d.%m.')} "
                        f"abwesend ({absence.get_code()}: {absence.start_date.strftime('%d.%m.')}–{absence.end_date.strftime('%d.%m.')})"
                    ),
                )


def validate_rest_times(
    result: ValidationResult,
    assignments: List[ShiftAssignment],
    emp_dict: Dict[int, Employee],
    absences: List[Absence],
    employees: List[Employee],
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
                    cause_type, cause = _analyze_absence_cause(
                        next_assign.date, absences, employees, shift_code=next_shift
                    )
                    # If no absences explain it, the cause is a rotation conflict
                    if cause_type != "ABSENCE":
                        cause_type = "ROTATION_CONFLICT"
                        cause = (
                            f"Ursache: Verbotene Schichtfolge Spät→Früh am "
                            f"{current.date.strftime('%d.%m.')}→{next_assign.date.strftime('%d.%m.')} "
                            f"durch Rotationszwänge (nur 8h Ruhezeit)"
                        )
                    result.add_violation(
                        f"{emp_name} has forbidden transition Spät->Früh on {current.date}->{next_assign.date} (only 8h rest)",
                        cause_type=cause_type,
                        cause=cause,
                    )
                elif current_shift == "N" and next_shift == "F":
                    emp_name = emp_dict[emp_id].full_name
                    cause_type, cause = _analyze_absence_cause(
                        next_assign.date, absences, employees, shift_code=next_shift
                    )
                    # If no absences explain it, the cause is a rotation conflict
                    if cause_type != "ABSENCE":
                        cause_type = "ROTATION_CONFLICT"
                        cause = (
                            f"Ursache: Verbotene Schichtfolge Nacht→Früh am "
                            f"{current.date.strftime('%d.%m.')}→{next_assign.date.strftime('%d.%m.')} "
                            f"durch Rotationszwänge (0h Ruhezeit)"
                        )
                    result.add_violation(
                        f"{emp_name} has forbidden transition Nacht->Früh on {current.date}->{next_assign.date} (0h rest)",
                        cause_type=cause_type,
                        cause=cause,
                    )
                elif current_shift == "N" and next_shift == "S":
                    emp_name = emp_dict[emp_id].full_name
                    cause_type, cause = _analyze_absence_cause(
                        next_assign.date, absences, employees, shift_code=next_shift
                    )
                    if cause_type != "ABSENCE":
                        cause_type = "ROTATION_CONFLICT"
                        cause = (
                            f"Ursache: Verbotene Schichtfolge Nacht→Spät am "
                            f"{current.date.strftime('%d.%m.')}→{next_assign.date.strftime('%d.%m.')} "
                            f"durch Rotationszwänge (nur 8h Ruhezeit)"
                        )
                    result.add_violation(
                        f"{emp_name} has forbidden transition Nacht->Spät on {current.date}->{next_assign.date} (only 8h rest)",
                        cause_type=cause_type,
                        cause=cause,
                    )


def validate_consecutive_shifts(
    result: ValidationResult,
    assignments: List[ShiftAssignment],
    emp_dict: Dict[int, Employee],
    absences: List[Absence],
    employees: List[Employee],
    shift_types: List = None,
):
    """Validate max consecutive shifts using shift type configuration from DB.
    
    Limits are read from shift_types (max_consecutive_days per shift type).
    Falls back to defaults if shift_types is not provided:
      - Any shift type: max 6 consecutive days
      - Night shift (N): max 3 consecutive nights (per STANDARD_SHIFT_TYPES configuration)
    """
    # Derive limits from shift type config
    max_consecutive_any = 6  # Default total consecutive days limit
    max_consecutive_by_code: dict = {}  # shift_code -> max consecutive days
    if shift_types:
        max_consecutive_any = max(
            (st.max_consecutive_days for st in shift_types), default=6
        ) or 6  # Guard against all-zero config
        for st in shift_types:
            max_consecutive_by_code[st.code] = st.max_consecutive_days
    
    # Fallback for night shifts: use configured value or the known default of 3
    n_max_consec = max_consecutive_by_code.get("N", 3)
    
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
        
        # Check max consecutive working days (any shift type)
        consecutive_days = 1
        last_date = None
        
        for assignment in emp_assignments:
            if last_date and (assignment.date - last_date).days == 1:
                consecutive_days += 1
                if consecutive_days > max_consecutive_any:
                    cause_type, cause = _analyze_absence_cause(
                        assignment.date, absences, employees
                    )
                    result.add_violation(
                        f"{emp_name} works more than {max_consecutive_any} consecutive days (ends {assignment.date})",
                        cause_type=cause_type,
                        cause=cause,
                    )
            else:
                consecutive_days = 1
            last_date = assignment.date
        
        # Check max consecutive night shifts (per configured limit, default 3)
        # Track last_night_date to detect free days between night blocks (which reset the counter).
        consecutive_nights = 0
        last_night_date = None
        for assignment in emp_assignments:
            shift_code = get_shift_type_by_id(assignment.shift_type_id).code
            if shift_code == "N":
                # Reset counter when there is a gap (free day) before this night shift
                if last_night_date and (assignment.date - last_night_date).days > 1:
                    consecutive_nights = 0
                consecutive_nights += 1
                last_night_date = assignment.date
                if consecutive_nights > n_max_consec:
                    cause_type, cause = _analyze_absence_cause(
                        assignment.date, absences, employees, shift_code="N"
                    )
                    result.add_violation(
                        f"{emp_name} works more than {n_max_consec} consecutive night shifts (ends {assignment.date})",
                        cause_type=cause_type,
                        cause=cause,
                    )
            else:
                consecutive_nights = 0
                last_night_date = None


def validate_minimum_consecutive_weekday_shifts(
    result: ValidationResult,
    assignments: List[ShiftAssignment],
    emp_dict: Dict[int, Employee]
):
    """
    Validate that employees work at least 2 consecutive days with the same shift type during weekdays.
    
    During weekdays (Mon-Fri), employees should not have single isolated shift days.
    Weekends (Sat-Sun) are exempt from this rule.
    """
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
        
        # Check for single isolated shift days during weekdays
        # Look at 3-day windows
        for i in range(len(emp_assignments) - 2):
            assign1 = emp_assignments[i]
            assign2 = emp_assignments[i + 1]
            assign3 = emp_assignments[i + 2]
            
            # Check if all three days are consecutive
            if (assign2.date - assign1.date).days == 1 and (assign3.date - assign2.date).days == 1:
                # Skip if any day is weekend
                if assign1.date.weekday() >= 5 or assign2.date.weekday() >= 5 or assign3.date.weekday() >= 5:
                    continue
                
                shift1 = get_shift_type_by_id(assign1.shift_type_id).code
                shift2 = get_shift_type_by_id(assign2.shift_type_id).code
                shift3 = get_shift_type_by_id(assign3.shift_type_id).code
                
                # Check for A-B-A pattern (single B isolated)
                if shift1 == shift3 and shift1 != shift2:
                    result.add_warning(
                        f"{emp_name}: Single isolated {shift2} shift on {assign2.date.strftime('%a %d.%m')} "
                        f"between {shift1} shifts (violates minimum 2 consecutive days rule)",
                        cause_type="ROTATION_CONFLICT",
                        cause=(
                            f"Ursache: Einzelne {shift2}-Schicht am {assign2.date.strftime('%d.%m.')} "
                            f"zwischen {shift1}-Schichten – Rotationszwänge verhindern 2-Tage-Minimum"
                        ),
                    )
                
                # Check for B-A-C pattern (single A isolated in middle)
                if shift1 != shift2 and shift2 != shift3 and shift1 != shift3:
                    result.add_warning(
                        f"{emp_name}: Single isolated {shift2} shift on {assign2.date.strftime('%a %d.%m')} "
                        f"between different shifts {shift1} and {shift3} (violates minimum 2 consecutive days rule)",
                        cause_type="ROTATION_CONFLICT",
                        cause=(
                            f"Ursache: Einzelne {shift2}-Schicht am {assign2.date.strftime('%d.%m.')} "
                            f"zwischen {shift1} und {shift3} – Rotationszwänge verhindern 2-Tage-Minimum"
                        ),
                    )
        
        # Also check for shift changes on consecutive weekdays
        for i in range(len(emp_assignments) - 1):
            assign1 = emp_assignments[i]
            assign2 = emp_assignments[i + 1]
            
            # Check if consecutive days
            if (assign2.date - assign1.date).days == 1:
                # Skip if either day is weekend
                if assign1.date.weekday() >= 5 or assign2.date.weekday() >= 5:
                    continue
                
                shift1 = get_shift_type_by_id(assign1.shift_type_id).code
                shift2 = get_shift_type_by_id(assign2.shift_type_id).code
                
                # Check for shift type change on consecutive weekdays
                if shift1 != shift2:
                    # Determine if either day appears as a single-day occurrence of its shift type
                    # (not part of a longer sequence of the same shift)
                    # We warn if either day1 or day2 is an isolated single-day shift
                    is_isolated_day1 = True
                    is_isolated_day2 = True
                    
                    # Check if day1 has same shift on previous WEEKDAY
                    if i > 0:
                        prev_assign = emp_assignments[i - 1]
                        # Only consider if previous day is also a weekday and consecutive
                        if (assign1.date - prev_assign.date).days == 1 and prev_assign.date.weekday() < 5:
                            prev_shift = get_shift_type_by_id(prev_assign.shift_type_id).code
                            if prev_shift == shift1:
                                is_isolated_day1 = False
                    
                    # Check if day2 has same shift on next WEEKDAY
                    if i + 2 < len(emp_assignments):
                        next_assign = emp_assignments[i + 2]
                        # Only consider if next day is also a weekday and consecutive
                        if (next_assign.date - assign2.date).days == 1 and next_assign.date.weekday() < 5:
                            next_shift = get_shift_type_by_id(next_assign.shift_type_id).code
                            if next_shift == shift2:
                                is_isolated_day2 = False
                    
                    # Only warn if either day appears to be isolated (single day of that shift)
                    if is_isolated_day1 or is_isolated_day2:
                        result.add_warning(
                            f"{emp_name}: Shift change from {shift1} to {shift2} on consecutive weekdays "
                            f"({assign1.date.strftime('%a %d.%m')} → {assign2.date.strftime('%a %d.%m')}), "
                            f"violates minimum 2 consecutive days rule",
                            cause_type="ROTATION_CONFLICT",
                            cause=(
                                f"Ursache: Schichtwechsel {shift1}→{shift2} an aufeinanderfolgenden Werktagen "
                                f"({assign1.date.strftime('%d.%m.')}→{assign2.date.strftime('%d.%m.')}) "
                                f"durch Rotationszwänge"
                            ),
                        )


def validate_working_hours(
    result: ValidationResult,
    assignments: List[ShiftAssignment],
    emp_dict: Dict[int, Employee],
    start_date: date,
    end_date: date,
    shift_types: List,
    absences: List[Absence],
    employees: List[Employee],
):
    """
    Validate working hours limits based on configured weekly_working_hours in shift types.
    
    Validates that employees:
    - Do not exceed max weekly hours (based on shift's weekly_working_hours)
    - Meet minimum weekly hours (based on shift's weekly_working_hours)
    - Do not exceed max monthly hours (weekly_working_hours * 4)
    
    Note: This is now dynamic based on shift configuration, not hardcoded to 48h/192h
    
    Args:
        shift_types: List of ShiftType objects from database (REQUIRED)
    """
    if not shift_types:
        raise ValueError("shift_types is required for validation - must be loaded from database")
    
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
        
        # A 30-day rolling window spans at most ceil(30/7) ≈ 4.3 calendar weeks.
        # With a 6-day/week rotation the true maximum is ceil(weekly_hours * 30 / 7),
        # rounded up to the next full 8-hour shift (to avoid spurious violations).
        shift_hours = 8  # standard shift duration; all main shifts use 8h
        expected_monthly_hours = math.ceil(expected_weekly_hours * 30 / 7 / shift_hours) * shift_hours
        
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
                cause_type, cause = _analyze_absence_cause(
                    week_start, absences, employees
                )
                result.add_violation(
                    f"{emp_name} works {hours:.1f} hours in week starting {week_start} (max {expected_weekly_hours}h based on shift config)",
                    cause_type=cause_type,
                    cause=cause,
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
                cause_type, cause = _analyze_absence_cause(
                    current, absences, employees
                )
                result.add_violation(
                    f"{emp_name} works {hours_in_window:.1f} hours in 30-day period {current} to {window_end} (max {expected_monthly_hours}h based on shift config)",
                    cause_type=cause_type,
                    cause=cause,
                )
            current += timedelta(days=7)  # Check weekly increments



def validate_staffing_requirements(
    result: ValidationResult,
    assignments_by_date: Dict[date, List[ShiftAssignment]],
    emp_dict: Dict[int, Employee],
    shift_types: List,
    absences: List[Absence],
    employees: List[Employee],
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
                cause_type, cause = _analyze_absence_cause(d, absences, employees, shift_code=shift_code)
                result.add_violation(
                    f"Insufficient staffing for {shift_code} shift on {d}: {count} (min {min_req})",
                    cause_type=cause_type,
                    cause=cause,
                )
            elif count > max_req:
                result.add_violation(
                    f"Overstaffing for {shift_code} shift on {d}: {count} (max {max_req})",
                    cause_type="UNKNOWN",
                    cause=(
                        f"Ursache: Überbesetzung in {shift_code}schicht am {d.strftime('%d.%m.')} "
                        f"– {count} von max. {max_req} Mitarbeitern eingeplant"
                    ),
                )


def validate_special_functions(
    result: ValidationResult,
    assignments: List[ShiftAssignment],
    emp_dict: Dict[int, Employee],
    absences: List[Absence],
    employees: List[Employee],
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
                        f"Employee {emp.full_name} assigned to BMT but not qualified on {d}",
                        cause_type="UNKNOWN",
                        cause=(
                            f"Ursache: {emp.full_name} ist am {d.strftime('%d.%m.')} "
                            f"für BMT eingeplant, besitzt aber keine BMT-Qualifikation"
                        ),
                    )
            
            if shift_type.code == "BSB":
                bsb_count += 1
                if not emp.is_brandschutzbeauftragter:
                    result.add_violation(
                        f"Employee {emp.full_name} assigned to BSB but not qualified on {d}",
                        cause_type="UNKNOWN",
                        cause=(
                            f"Ursache: {emp.full_name} ist am {d.strftime('%d.%m.')} "
                            f"für BSB eingeplant, besitzt aber keine BSB-Qualifikation"
                        ),
                    )
        
        # Should have exactly 1 BMT and 1 BSB on weekdays
        if bmt_count != 1:
            cause_type, cause = _analyze_absence_cause(d, absences, employees, shift_code="BMT")
            result.add_warning(
                f"BMT count on {d} is {bmt_count} (expected 1)",
                cause_type=cause_type,
                cause=cause,
            )
        
        if bsb_count != 1:
            cause_type, cause = _analyze_absence_cause(d, absences, employees, shift_code="BSB")
            result.add_warning(
                f"BSB count on {d} is {bsb_count} (expected 1)",
                cause_type=cause_type,
                cause=cause,
            )


def validate_coverage_availability(
    result: ValidationResult,
    assignments: List[ShiftAssignment],
    employees: List[Employee],
    absences: List[Absence],
):
    """Validate coverage availability.

    Note: The previously-used check "at least 1 employee must be free each week"
    is not enforced here.  With a 3-team F/N/S rotation every employee works
    6-7 days per week, so the check would always fire and produce false
    positives.  The corresponding solver constraint
    (add_weekly_available_employee_constraint) is also disabled.
    """
    pass


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
        if d.weekday() == 6 and current_week:  # Sunday
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
                    f"{emp.full_name} works weekend in week {week_idx} but no weekdays",
                    cause_type="ROTATION_CONFLICT",
                    cause=(
                        f"Ursache: {emp.full_name} arbeitet am Wochenende in Woche {week_idx}, "
                        f"hat aber keine Wochentags-Schichten – Rotationsfehler"
                    ),
                )
                continue
            
            # CRITICAL CHECK: Weekend shifts MUST be subset of weekday shifts
            # (should be exactly same shift type, but subset handles partial week work)
            if not weekend_shifts.issubset(weekday_shifts):
                result.add_violation(
                    f"WEEKEND VIOLATION: {emp.full_name} week {week_idx}: "
                    f"weekday shifts={sorted(weekday_shifts)}, "
                    f"weekend shifts={sorted(weekend_shifts)}. "
                    f"Weekend must match team's weekly shift!",
                    cause_type="ROTATION_CONFLICT",
                    cause=(
                        f"Ursache: {emp.full_name} in Woche {week_idx} – Wochenendschichten "
                        f"{sorted(weekend_shifts)} stimmen nicht mit Wochentags-Schichten "
                        f"{sorted(weekday_shifts)} überein (Rotationskonflikt)"
                    ),
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
                    f"MISSING EMPLOYEE: {emp.full_name} (ID {emp.id}) is missing from schedule on {d}",
                    cause_type="UNKNOWN",
                    cause=(
                        f"Ursache: {emp.full_name} fehlt im Dienstplan am {d.strftime('%d.%m.')} "
                        f"– kein Eintrag im vollständigen Plan"
                    ),
                )


def validate_locked_assignments(
    result: ValidationResult,
    assignments: List[ShiftAssignment],
    locked_team_shift: Dict[Tuple[int, int], str],
    locked_employee_weekend: Dict[Tuple[int, date], bool],
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
        if d.weekday() == 6 and current_week:  # Sunday
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
                    f"LOCKED TEAM SHIFT VIOLATED: {team.name} week {week_idx} should be '{expected_shift}' but has {actual_shifts}",
                    cause_type="ROTATION_CONFLICT",
                    cause=(
                        f"Ursache: Team {team.name} in Woche {week_idx} – gesperrte Schicht "
                        f"'{expected_shift}' nicht eingehalten (tatsächlich: {sorted(actual_shifts)})"
                    ),
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
                    f"LOCKED WEEKEND VIOLATED: {emp.full_name} should work on {d} but doesn't",
                    cause_type="ROTATION_CONFLICT",
                    cause=(
                        f"Ursache: {emp.full_name} ist für {d.strftime('%d.%m.')} als arbeitend gesperrt, "
                        f"wurde aber nicht eingeplant"
                    ),
                )
            elif not expected_working and is_working:
                result.add_violation(
                    f"LOCKED WEEKEND VIOLATED: {emp.full_name} should NOT work on {d} but does",
                    cause_type="ROTATION_CONFLICT",
                    cause=(
                        f"Ursache: {emp.full_name} ist für {d.strftime('%d.%m.')} als frei gesperrt, "
                        f"wurde aber trotzdem eingeplant"
                    ),
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
        assignments, complete_schedule = result
        print(f"\nValidating {len(assignments)} assignments...")
        
        validation_result = validate_shift_plan(
            assignments, employees, absences, start, end, teams,
            complete_schedule
        )
        validation_result.print_report()
    else:
        print("\nNo solution to validate!")
