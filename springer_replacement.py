"""
Automatic shift replacement logic for absences.

This module handles automatic replacement when absences are entered
AFTER the schedule has been generated.

Requirements:
- Attempt automatic replacement when employee becomes absent
- Available employee can only be assigned if:
  - Not absent (U, AU, L)
  - Not assigned to another shift
  - Legally allowed (rest times, max shifts)
  - Is from a regular shift team (not special role)
- Notify assigned employee if replacement made
- Notify admins/dispatchers if no replacement possible
"""

from datetime import date, timedelta
from typing import List, Tuple, Optional, Dict
from entities import Employee, Absence, ShiftAssignment, Team, get_shift_type_by_id, get_shift_type_by_code
from notifications import notification_service


def can_employee_work_shift(
    employee: Employee,
    shift_date: date,
    shift_code: str,
    existing_assignments: List[ShiftAssignment],
    absences: List[Absence]
) -> Tuple[bool, str]:
    """
    Check if an employee can work a specific shift.
    
    Args:
        employee: The employee to check
        shift_date: Date of the shift
        shift_code: Shift code (F, S, N)
        existing_assignments: All existing shift assignments
        absences: All absences
        
    Returns:
        Tuple of (can_work, reason)
        - can_work: True if employee can work this shift
        - reason: Explanation if cannot work
    """
    # Check if employee is absent on this date
    for absence in absences:
        if absence.employee_id == employee.id and absence.overlaps_date(shift_date):
            return False, f"Absent ({absence.get_code()})"
    
    # Check if employee already has a shift on this date
    for assignment in existing_assignments:
        if assignment.employee_id == employee.id and assignment.date == shift_date:
            return False, "Already assigned to another shift"
    
    # Check rest time constraints (11 hours minimum)
    # Look at previous day's shift
    previous_day = shift_date - timedelta(days=1)
    for assignment in existing_assignments:
        if assignment.employee_id == employee.id and assignment.date == previous_day:
            # Get shift type from assignment
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
            a.employee_id == employee.id and a.date == check_date
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
            a.employee_id == employee.id and a.date == check_date
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


def find_available_employee(
    shift_date: date,
    shift_code: str,
    available_employees: List[Employee],
    existing_assignments: List[ShiftAssignment],
    absences: List[Absence]
) -> Optional[Tuple[Employee, str]]:
    """
    Find an available employee for a shift replacement.
    
    Args:
        shift_date: Date of the shift
        shift_code: Shift code (F, S, N)
        available_employees: List of employees who could potentially fill in
        existing_assignments: All existing shift assignments
        absences: All absences
        
    Returns:
        Tuple of (employee, reason) if found, None if no one available
        - employee: The available employee
        - reason: Why this employee was selected
    """
    available = []
    
    for emp in available_employees:
        can_work, reason = can_employee_work_shift(
            emp, shift_date, shift_code, existing_assignments, absences
        )
        if can_work:
            available.append((emp, reason))
    
    if not available:
        return None
    
    # Return first available employee
    # In a more sophisticated implementation, could prioritize by:
    # - Fewest shifts this month
    # - Closest to home/facility
    # - Preferences
    return available[0]


def attempt_replacement(
    absent_employee: Employee,
    absence: Absence,
    team: Team,
    shift_date: date,
    shift_code: str,
    available_employees: List[Employee],
    existing_assignments: List[ShiftAssignment],
    all_absences: List[Absence]
) -> Optional[ShiftAssignment]:
    """
    Attempt to assign an available employee to replace an absent employee.
    
    This function:
    1. Finds an available employee from shift teams
    2. Creates a shift assignment if found
    3. Triggers appropriate notifications
    
    Args:
        absent_employee: The employee who is absent
        absence: The absence record
        team: The team of the absent employee
        shift_date: Date of the shift
        shift_code: Shift code (F, S, N)
        available_employees: List of employees who could potentially fill in (from shift teams)
        existing_assignments: All existing shift assignments
        all_absences: All absences
        
    Returns:
        ShiftAssignment if replacement successful, None otherwise
    """
    # Find available employee
    result = find_available_employee(
        shift_date, shift_code, available_employees, existing_assignments, all_absences
    )
    
    if result is None:
        # No employee available - notify admins/dispatchers
        # Collect reasons why employees are not available
        reasons = []
        for emp in available_employees:
            can_work, reason = can_employee_work_shift(
                emp, shift_date, shift_code, existing_assignments, all_absences
            )
            reasons.append(f"{emp.full_name}: {reason}")
        
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
    
    replacement_employee, _ = result
    
    # Create replacement assignment
    shift_type = get_shift_type_by_code(shift_code)
    
    if not shift_type:
        return None
    
    # Generate new assignment ID (in real system, use database auto-increment)
    new_id = max([a.id for a in existing_assignments], default=0) + 1
    
    assignment = ShiftAssignment(
        id=new_id,
        employee_id=replacement_employee.id,
        shift_type_id=shift_type.id,
        date=shift_date,
        is_manual=False,
        is_fixed=True,  # Lock this assignment
        notes=f"Automatic replacement for {absent_employee.full_name} ({absence.get_code()})"
    )
    
    # Notify replacement employee about assignment
    notification_service.trigger_springer_assigned(
        springer=replacement_employee,
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
    all_employees: List[Employee],
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
        all_employees: List of all employees (will filter for eligible replacements)
        existing_assignments: All existing shift assignments
        all_absences: All absences (including the new one)
        
    Returns:
        Tuple of (new_assignments, dates_without_replacement)
        - new_assignments: List of new replacement assignments created
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
    
    # Get eligible employees for replacement (from regular shift teams)
    # Exclude: Ferienjobber, employees without teams, virtual team members
    VIRTUAL_TEAM_ID = 99  # Fire Alarm System
    available_employees = [
        emp for emp in all_employees
        if emp.team_id and emp.team_id != VIRTUAL_TEAM_ID and not emp.is_ferienjobber
    ]
    
    new_assignments = []
    dates_without_replacement = []
    
    # Try to replace each affected shift
    for shift_date, shift_code in affected_shifts.items():
        if not team:
            # Employee has no team - cannot determine shift type
            dates_without_replacement.append(shift_date)
            continue
        
        # Attempt replacement
        assignment = attempt_replacement(
            absent_employee=employee,
            absence=absence,
            team=team,
            shift_date=shift_date,
            shift_code=shift_code,
            available_employees=available_employees,
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
                shift_type = get_shift_type_by_id(assignment.shift_type_id)
                if shift_type:
                    affected_shifts[assignment.date] = shift_type.code
    
    return affected_shifts
