"""
Springer replacement logic for automatic shift coverage.

This module handles automatic springer assignment when absences are entered
AFTER the schedule has been generated.

Requirements:
- Attempt automatic replacement when employee becomes absent
- Springer can only be assigned if:
  - Not absent (U, AU, L)
  - Not assigned to another shift
  - Legally allowed (rest times, max shifts)
- Notify springer if assigned
- Notify admins/dispatchers if no replacement possible
"""

from datetime import date, timedelta
from typing import List, Tuple, Optional, Dict
from entities import Employee, Absence, ShiftAssignment, Team
from notifications import notification_service


def can_springer_work_shift(
    springer: Employee,
    shift_date: date,
    shift_code: str,
    existing_assignments: List[ShiftAssignment],
    absences: List[Absence]
) -> Tuple[bool, str]:
    """
    Check if a springer can work a specific shift.
    
    Args:
        springer: The springer employee
        shift_date: Date of the shift
        shift_code: Shift code (F, S, N)
        existing_assignments: All existing shift assignments
        absences: All absences
        
    Returns:
        Tuple of (can_work, reason)
        - can_work: True if springer can work this shift
        - reason: Explanation if cannot work
    """
    # Check if springer is absent on this date
    for absence in absences:
        if absence.employee_id == springer.id and absence.overlaps_date(shift_date):
            return False, f"Absent ({absence.get_code()})"
    
    # Check if springer already has a shift on this date
    for assignment in existing_assignments:
        if assignment.employee_id == springer.id and assignment.date == shift_date:
            return False, "Already assigned to another shift"
    
    # Check rest time constraints (11 hours minimum)
    # Look at previous day's shift
    previous_day = shift_date - timedelta(days=1)
    for assignment in existing_assignments:
        if assignment.employee_id == springer.id and assignment.date == previous_day:
            # Get shift type from assignment
            from entities import get_shift_type_by_id
            prev_shift = get_shift_type_by_id(assignment.shift_type_id)
            if prev_shift:
                # Check forbidden transitions
                # S (ends 21:45) → F (starts 05:45) = 8 hours (FORBIDDEN)
                # N (ends 05:45) → F (starts 05:45) = 0 hours (FORBIDDEN)
                if prev_shift.code == "S" and shift_code == "F":
                    return False, "Rest time violation (S→F)"
                if prev_shift.code == "N" and shift_code == "F":
                    return False, "Rest time violation (N→F)"
    
    # Check maximum consecutive shifts (6 days)
    # Count consecutive working days including this shift
    consecutive_days = 1  # This shift
    
    # Count backwards
    check_date = shift_date - timedelta(days=1)
    for _ in range(6):  # Maximum 6 consecutive
        has_shift = any(
            a.employee_id == springer.id and a.date == check_date
            for a in existing_assignments
        )
        if not has_shift:
            break
        consecutive_days += 1
        check_date -= timedelta(days=1)
    
    # Count forwards
    check_date = shift_date + timedelta(days=1)
    for _ in range(6):
        has_shift = any(
            a.employee_id == springer.id and a.date == check_date
            for a in existing_assignments
        )
        if not has_shift:
            break
        consecutive_days += 1
        check_date += timedelta(days=1)
    
    if consecutive_days > 6:
        return False, "Maximum consecutive shifts (6 days) exceeded"
    
    # All checks passed
    return True, "Available"


def find_available_springer(
    shift_date: date,
    shift_code: str,
    springers: List[Employee],
    existing_assignments: List[ShiftAssignment],
    absences: List[Absence]
) -> Optional[Tuple[Employee, str]]:
    """
    Find an available springer for a shift.
    
    Args:
        shift_date: Date of the shift
        shift_code: Shift code (F, S, N)
        springers: List of all springer employees
        existing_assignments: All existing shift assignments
        absences: All absences
        
    Returns:
        Tuple of (springer, reason) if found, None if no springer available
        - springer: The available springer
        - reason: Why this springer was selected
    """
    available_springers = []
    
    for springer in springers:
        can_work, reason = can_springer_work_shift(
            springer, shift_date, shift_code, existing_assignments, absences
        )
        if can_work:
            available_springers.append((springer, reason))
    
    if not available_springers:
        return None
    
    # Return first available springer
    # In a more sophisticated implementation, could prioritize by:
    # - Fewest shifts this month
    # - Closest to home/facility
    # - Preferences
    return available_springers[0]


def attempt_springer_replacement(
    absent_employee: Employee,
    absence: Absence,
    team: Team,
    shift_date: date,
    shift_code: str,
    springers: List[Employee],
    existing_assignments: List[ShiftAssignment],
    all_absences: List[Absence]
) -> Optional[ShiftAssignment]:
    """
    Attempt to assign a springer to replace an absent employee.
    
    This function:
    1. Finds an available springer
    2. Creates a shift assignment if found
    3. Triggers appropriate notifications
    
    Args:
        absent_employee: The employee who is absent
        absence: The absence record
        team: The team of the absent employee
        shift_date: Date of the shift
        shift_code: Shift code (F, S, N)
        springers: List of all springer employees
        existing_assignments: All existing shift assignments
        all_absences: All absences
        
    Returns:
        ShiftAssignment if replacement successful, None otherwise
    """
    # Find available springer
    result = find_available_springer(
        shift_date, shift_code, springers, existing_assignments, all_absences
    )
    
    if result is None:
        # No springer available - notify admins/dispatchers
        # Collect reasons why springers are not available
        reasons = []
        for springer in springers:
            can_work, reason = can_springer_work_shift(
                springer, shift_date, shift_code, existing_assignments, all_absences
            )
            reasons.append(f"{springer.full_name}: {reason}")
        
        reason_str = "; ".join(reasons)
        
        notification_service.trigger_no_replacement_available(
            employee=absent_employee,
            shift_date=shift_date,
            shift_code=shift_code,
            team_name=team.name,
            absence_reason=absence.get_code(),
            reason_no_replacement=reason_str,
            understaffing_impact=f"Shift {shift_code} on {shift_date}: understaffed"
        )
        
        return None
    
    springer, _ = result
    
    # Create springer assignment
    from entities import get_shift_type_by_code
    shift_type = get_shift_type_by_code(shift_code)
    
    if not shift_type:
        return None
    
    # Generate new assignment ID (in real system, use database auto-increment)
    new_id = max([a.id for a in existing_assignments], default=0) + 1
    
    assignment = ShiftAssignment(
        id=new_id,
        employee_id=springer.id,
        shift_type_id=shift_type.id,
        date=shift_date,
        is_manual=False,
        is_springer_assignment=True,
        is_fixed=True,  # Lock this assignment
        notes=f"Automatic springer replacement for {absent_employee.full_name} ({absence.get_code()})"
    )
    
    # Notify springer about assignment
    notification_service.trigger_springer_assigned(
        springer=springer,
        original_employee=absent_employee,
        shift_date=shift_date,
        shift_code=shift_code,
        absence_reason=absence.get_code()
    )
    
    return assignment


def handle_post_scheduling_absence(
    absence: Absence,
    employee: Employee,
    team: Optional[Team],
    schedule_month: str,
    affected_dates: List[date],
    affected_shifts: Dict[date, str],  # date -> shift_code
    springers: List[Employee],
    existing_assignments: List[ShiftAssignment],
    all_absences: List[Absence]
) -> Tuple[List[ShiftAssignment], List[date]]:
    """
    Handle an absence that was entered AFTER the schedule was generated.
    
    This is the main entry point for post-scheduling absence workflow.
    
    Args:
        absence: The new absence
        employee: The absent employee
        team: The employee's team (if any)
        schedule_month: Month name for notifications (e.g., "January 2026")
        affected_dates: List of dates affected by the absence
        affected_shifts: Dict mapping date to shift_code for shifts that need replacement
        springers: List of all springer employees
        existing_assignments: All existing shift assignments
        all_absences: All absences (including the new one)
        
    Returns:
        Tuple of (new_assignments, dates_without_replacement)
        - new_assignments: List of new springer assignments created
        - dates_without_replacement: List of dates where no replacement was found
    """
    # Notify admins/dispatchers about the absence
    notification_service.trigger_absence_after_scheduling(
        employee=employee,
        absence=absence,
        affected_dates=affected_dates,
        schedule_month=schedule_month,
        replacement_attempted=True
    )
    
    new_assignments = []
    dates_without_replacement = []
    
    # Try to replace each affected shift
    for shift_date, shift_code in affected_shifts.items():
        if not team:
            # Employee has no team - cannot determine shift type
            dates_without_replacement.append(shift_date)
            continue
        
        # Attempt springer replacement
        assignment = attempt_springer_replacement(
            absent_employee=employee,
            absence=absence,
            team=team,
            shift_date=shift_date,
            shift_code=shift_code,
            springers=springers,
            existing_assignments=existing_assignments + new_assignments,  # Include newly created
            all_absences=all_absences
        )
        
        if assignment:
            new_assignments.append(assignment)
        else:
            dates_without_replacement.append(shift_date)
    
    return new_assignments, dates_without_replacement


def get_affected_shifts_for_absence(
    employee: Employee,
    absence: Absence,
    existing_assignments: List[ShiftAssignment]
) -> Dict[date, str]:
    """
    Get the shifts affected by an absence.
    
    Args:
        employee: The absent employee
        absence: The absence record
        existing_assignments: All existing shift assignments
        
    Returns:
        Dict mapping date to shift_code for affected shifts
    """
    affected_shifts = {}
    
    # Find all assignments for this employee during the absence period
    for assignment in existing_assignments:
        if assignment.employee_id == employee.id:
            if absence.overlaps_date(assignment.date):
                # Get shift code
                from entities import get_shift_type_by_id
                shift_type = get_shift_type_by_id(assignment.shift_type_id)
                if shift_type:
                    affected_shifts[assignment.date] = shift_type.code
    
    return affected_shifts
