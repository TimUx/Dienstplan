"""
OR-Tools CP-SAT model builder for shift planning.
Creates decision variables and orchestrates constraint addition.

Important: This model implements team-based shift planning where:
- Teams are the primary planning unit, not individual employees
- All members of a team work the same shift during a week
- Teams rotate weekly in fixed pattern: F → N → S
"""

from ortools.sat.python import cp_model
from datetime import date, timedelta
from typing import Dict, List, Tuple, Set
from entities import Employee, Absence, ShiftType, STANDARD_SHIFT_TYPES, Team


class ShiftPlanningModel:
    """
    Builds and manages the OR-Tools CP-SAT model for shift planning.
    """
    
    def __init__(
        self,
        employees: List[Employee],
        teams: List[Team],
        start_date: date,
        end_date: date,
        absences: List[Absence],
        shift_types: List[ShiftType] = None,
        locked_team_shift: Dict[Tuple[int, int], str] = None,
        locked_employee_weekend: Dict[Tuple[int, date], bool] = None,
        locked_absence: Dict[Tuple[int, date], str] = None,
        locked_employee_shift: Dict[Tuple[int, date], str] = None,
        ytd_weekend_counts: Dict[int, int] = None,
        ytd_night_counts: Dict[int, int] = None,
        ytd_holiday_counts: Dict[int, int] = None,
        previous_employee_shifts: Dict[Tuple[int, date], str] = None
    ):
        """
        Initialize the shift planning model.
        
        Args:
            employees: List of all employees
            teams: List of teams
            start_date: Start date of planning period
            end_date: End date of planning period
            absences: List of employee absences (AUTHORITATIVE - always locked)
            shift_types: List of shift types (REQUIRED - must be loaded from database)
            locked_team_shift: Dict mapping (team_id, week_idx) -> shift_code (manual overrides)
            locked_employee_weekend: Dict mapping (emp_id, date) -> bool (manual overrides)
            locked_absence: Dict mapping (emp_id, date) -> absence_code (U/AU/L) (manual overrides)
            locked_employee_shift: Dict mapping (emp_id, date) -> shift_code (existing assignments from previous planning)
            ytd_weekend_counts: Dict mapping employee_id -> count of weekend days worked this year (for fairness)
            ytd_night_counts: Dict mapping employee_id -> count of night shifts worked this year (for fairness)
            ytd_holiday_counts: Dict mapping employee_id -> count of holidays worked this year (for fairness)
            previous_employee_shifts: Dict mapping (emp_id, date) -> shift_code for dates BEFORE planning period.
                                     Used to check consecutive shifts across month boundaries.
                                     Should contain shifts from up to max_consecutive_days before start_date.
        
        Note:
            shift_types MUST be loaded from the database. STANDARD_SHIFT_TYPES should only
            be used for database initialization, not at runtime.
        
        Note on YTD statistics:
        - These should be loaded from the database for the current year
        - Used to ensure fairness across the ENTIRE YEAR, not just the current planning period
        - If not provided, defaults to empty dicts (assumes no prior history this year)
        """
        self.model = cp_model.CpModel()
        self.employees = employees
        self.teams = teams
        self.start_date = start_date
        self.end_date = end_date
        self.absences = absences
        # shift_types is REQUIRED and must be loaded from database
        # STANDARD_SHIFT_TYPES should only be used for DB initialization, not at runtime
        if not shift_types:
            raise ValueError("shift_types is required and must be loaded from database. "
                           "STANDARD_SHIFT_TYPES should only be used for database initialization.")
        self.shift_types = shift_types
        
        # Manual overrides (locked assignments)
        self.locked_team_shift = locked_team_shift or {}
        self.locked_employee_weekend = locked_employee_weekend or {}
        self.locked_absence = locked_absence or {}  # NEW: locked absence assignments
        self.locked_employee_shift = locked_employee_shift or {}  # NEW: locked employee shift assignments from previous planning
        
        # Previous shifts for cross-month consecutive days checking
        self.previous_employee_shifts = previous_employee_shifts or {}
        
        # Year-to-date statistics for fairness tracking
        self.ytd_weekend_counts = ytd_weekend_counts or {}
        self.ytd_night_counts = ytd_night_counts or {}
        self.ytd_holiday_counts = ytd_holiday_counts or {}
        
        # Store original dates for reference
        self.original_start_date = start_date
        self.original_end_date = end_date
        
        # Extend planning period to complete weeks (Sunday to Saturday)
        # This ensures team rotation constraints can be satisfied
        extended_start = start_date
        extended_end = end_date
        
        # Extend start to previous Sunday if not already Sunday
        if start_date.weekday() != 6:  # 6 = Sunday
            # Calculate days back to previous Sunday
            # Monday=0 -> go back 1 day, Tuesday=1 -> go back 2 days, ..., Saturday=5 -> go back 6 days
            days_back_to_sunday = start_date.weekday() + 1
            extended_start = start_date - timedelta(days=days_back_to_sunday)
        
        # Extend end to next Saturday if not already Saturday
        if end_date.weekday() != 5:  # 5 = Saturday
            # Calculate days forward to next Saturday
            # Sunday=6 -> go forward 6 days, Monday=0 -> go forward 5 days, ..., Friday=4 -> go forward 1 day
            days_forward_to_saturday = (5 - end_date.weekday() + 7) % 7
            extended_end = end_date + timedelta(days=days_forward_to_saturday)
        
        # Use extended dates for planning
        self.start_date = extended_start
        self.end_date = extended_end
        
        # Generate list of dates using extended range
        self.dates = []
        current = extended_start
        while current <= extended_end:
            self.dates.append(current)
            current += timedelta(days=1)
        
        # Determine which shift codes to include in the model
        # Include F, S, N for standard rotation
        # Also include any other shifts that teams are configured to work
        shift_codes_set = set()
        
        # Always include F, S, N if they exist (standard rotation)
        for st in self.shift_types:
            if st.code in ["F", "S", "N"]:
                shift_codes_set.add(st.code)
        
        # Add any shifts that teams are explicitly configured to work
        for team in self.teams:
            if team.allowed_shift_type_ids:
                for shift_type_id in team.allowed_shift_type_ids:
                    # Find the shift type code for this ID
                    for st in self.shift_types:
                        if st.id == shift_type_id:
                            shift_codes_set.add(st.code)
                            break
        
        # Convert to sorted list for consistency
        self.shift_codes = sorted(list(shift_codes_set))
        
        # Generate weeks (Monday to Sunday)
        self.weeks = self._generate_weeks()
        
        # Decision variables
        self.team_shift = {}  # team_shift[team_id, week_idx, shift_code] = 0 or 1
        self.employee_active = {}  # employee_active[employee_id, date] = 0 or 1 (derived from team shift)
        self.employee_weekend_shift = {}  # employee_weekend_shift[emp_id, date] = 0 or 1 (WEEKEND ONLY - shift type from team)
        self.employee_cross_team_shift = {}  # employee_cross_team_shift[emp_id, date, shift_code] = 0 or 1 (cross-team weekday work)
        self.employee_cross_team_weekend = {}  # employee_cross_team_weekend[emp_id, date, shift_code] = 0 or 1 (cross-team weekend work)
        
        # Build the model
        self._create_decision_variables()
        self._apply_locked_assignments()
    
    
    def _employee_has_absence_on_date(self, emp_id: int, check_date: date) -> bool:
        """
        Check if an employee has an absence on a specific date.
        
        Args:
            emp_id: Employee ID to check
            check_date: Date to check for absence
            
        Returns:
            True if employee has an absence on this date, False otherwise
        """
        return any(
            abs.employee_id == emp_id and abs.overlaps_date(check_date)
            for abs in self.absences
        )
    
    
    def _employee_has_absence_in_week(self, emp_id: int, week_dates: List[date]) -> bool:
        """
        Check if an employee has an absence on any day in a given week.
        
        Args:
            emp_id: Employee ID to check
            week_dates: List of dates in the week to check
            
        Returns:
            True if employee has an absence on any day in the week, False otherwise
        """
        return any(
            self._employee_has_absence_on_date(emp_id, d)
            for d in week_dates
        )
    
    
    def _apply_locked_assignments(self):
        """
        Apply manual overrides (locked assignments) as hard constraints.
        
        When administrators or dispatchers fix certain assignments:
        - locked_team_shift: Forces a team to a specific shift in a week
        - locked_employee_weekend: Forces employee presence/absence on weekend
        - locked_employee_shift: Forces employee to have a specific shift on a date (from previous planning periods)
        """
        # CRITICAL FIX: Don't apply locked_team_shift constraints yet!
        # We need to first collect team locks from BOTH sources (locked_team_shift AND locked_employee_shift)
        # and resolve conflicts BEFORE adding any constraints to the model.
        # Otherwise, we get INFEASIBLE when locked_employee_shift tries to add conflicting team locks.
        
        # Start with a copy of the initial locked_team_shift dictionary
        # This will be updated as we process locked_employee_shift
        consolidated_team_locks = dict(self.locked_team_shift)
        
        # Apply locked employee shift assignments (from previous planning periods)
        # This prevents double shifts when planning across months
        
        # Create employee ID mapping for efficient lookups
        emp_by_id = {emp.id: emp for emp in self.employees}
        
        for (emp_id, d), shift_code in self.locked_employee_shift.items():
            # CRITICAL FIX: Check for conflicts with absences BEFORE adding constraints
            # If employee has an absence on this date, skip the locked shift to avoid infeasibility
            if self._employee_has_absence_on_date(emp_id, d):
                # Conflict detected: employee has absence on this date
                # Absence takes precedence over locked shifts from previous planning
                print(f"WARNING: Skipping locked shift for employee {emp_id} on {d}")
                print(f"  Reason: Employee has absence on this date (absence overrides locked shift)")
                continue  # Skip this lock to avoid infeasibility
            
            # CRITICAL FIX: Skip employee locks for dates outside the original planning period
            # Reason: Dates outside the original period belong to adjacent months and already have
            # shift assignments from those months. Applying employee locks for these dates would:
            # 1. Create double shifts (employee assigned to both previous and current month shifts)
            # 2. Conflict with team rotation (team might be assigned different shift in current month)
            # The extended period is only used to complete weeks for team rotation, but employees
            # should not be locked to work on dates from adjacent months.
            if d < self.original_start_date or d > self.original_end_date:
                # This date is in an adjacent month
                # Skip this employee lock entirely (both employee-level and team-level)
                continue
            
            # CRITICAL FIX: Determine if this date is in a week that spans month boundaries
            # Find which week this date belongs to
            week_idx_for_date = None
            week_dates_for_date = None
            for idx, week_dates in enumerate(self.weeks):
                if d in week_dates:
                    week_idx_for_date = idx
                    week_dates_for_date = week_dates
                    break
            
            # Check if this week spans boundaries
            date_in_boundary_week = False
            if week_dates_for_date:
                week_spans_boundary = any(
                    wd < self.original_start_date or wd > self.original_end_date 
                    for wd in week_dates_for_date
                )
                date_in_boundary_week = week_spans_boundary
            
            # CRITICAL FIX: Skip employee locks for dates in weeks that span month boundaries
            # Reason: In team-based planning, all team members must work the same shift in a week.
            # For boundary weeks (weeks spanning month transitions), different team members may have
            # worked on different days in the previous month, creating conflicting locked shifts.
            # If we apply employee locks for boundary weeks, we risk:
            # 1. Forcing employees to work when their team has a different shift assignment
            # 2. Creating conflicts between employee locks and team rotation constraints
            # 3. Making the problem INFEASIBLE
            # Therefore, we skip ALL locks (both employee-level and team-level) for dates in boundary weeks,
            # allowing the solver to freely assign shifts for these weeks without conflicts.
            if date_in_boundary_week:
                # Date is in a week that spans month boundaries
                # Skip this lock entirely to avoid conflicts
                continue
            
            # CRITICAL FIX: Check for team lock conflicts BEFORE adding employee constraints
            # Find the employee's team to check for conflicts
            emp = emp_by_id.get(emp_id)
            has_team_lock_conflict = False
            
            if emp and emp.team_id and week_idx_for_date is not None:
                # Check if there's already a team lock for this team/week with a different shift
                if (emp.team_id, week_idx_for_date) in consolidated_team_locks:
                    existing_shift = consolidated_team_locks[(emp.team_id, week_idx_for_date)]
                    if existing_shift != shift_code:
                        # Conflict detected: different locked shifts for same team/week
                        # This can happen when multiple employees from the same team have
                        # different locked shifts within the same week, OR when locked_team_shift
                        # conflicts with locked_employee_shift
                        has_team_lock_conflict = True
                        print(f"WARNING: Skipping conflicting locked shift for team {emp.team_id}, week {week_idx_for_date}")
                        print(f"  Existing: {existing_shift}, Attempted: {shift_code} (from employee {emp_id} on {d})")
            
            # Skip this entire employee lock if there's a team lock conflict
            # This prevents adding employee constraints that would contradict team constraints.
            # Note: The conflicting team lock (if from locked_team_shift) remains in consolidated_team_locks.
            # We only skip adding the employee-level constraint and skip updating consolidated_team_locks
            # with this conflicting employee shift.
            if has_team_lock_conflict:
                continue  # Skip to next employee lock
            
            # No conflict - safe to add employee-level constraints
            # For weekdays, ensure employee is active on this date
            if d.weekday() < 5:  # Monday to Friday
                if (emp_id, d) in self.employee_active:
                    # Force employee to be active on this date
                    self.model.Add(self.employee_active[(emp_id, d)] == 1)
            else:  # Weekend
                if (emp_id, d) in self.employee_weekend_shift:
                    # Force employee to work on this weekend day
                    self.model.Add(self.employee_weekend_shift[(emp_id, d)] == 1)
            
            # Additionally, update the consolidated team lock for this employee's team/week
            if emp and emp.team_id and week_idx_for_date is not None:
                # Record team lock for this week (we already checked there's no conflict above)
                if (emp.team_id, week_idx_for_date, shift_code) in self.team_shift:
                    # Safe to record this team/week lock (no conflict)
                    consolidated_team_locks[(emp.team_id, week_idx_for_date)] = shift_code
        
        # CRITICAL FIX: Now apply all consolidated team locks as constraints
        # This ensures conflicts are resolved BEFORE adding any constraints to the model
        for (team_id, week_idx), shift_code in consolidated_team_locks.items():
            if (team_id, week_idx, shift_code) in self.team_shift:
                # Force this team to have this shift in this week
                # Note: Other shifts for this team/week are implicitly set to 0
                # by the "exactly one shift per team per week" constraint
                self.model.Add(self.team_shift[(team_id, week_idx, shift_code)] == 1)
        
        # Apply locked employee weekend work
        for (emp_id, d), is_working in self.locked_employee_weekend.items():
            # Check for conflicts with absences
            # Note: We skip both cases (working=True and working=False) when absent
            # because applying a constraint when absent is redundant and potentially confusing
            if self._employee_has_absence_on_date(emp_id, d):
                if is_working:
                    # Conflict: employee has absence but locked to work this weekend
                    print(f"WARNING: Skipping locked weekend work for employee {emp_id} on {d}")
                    print(f"  Reason: Employee has absence on this date (absence overrides locked weekend)")
                # Note: When is_working=False and employee is absent, both indicate non-working,
                # but we still skip the constraint to avoid redundancy
                continue  # Skip this lock (absence already enforces non-working)
            
            if (emp_id, d) in self.employee_weekend_shift:
                # Force employee to work (1) or not work (0) on this weekend day
                self.model.Add(self.employee_weekend_shift[(emp_id, d)] == (1 if is_working else 0))
    
    
    def _generate_weeks(self) -> List[List[date]]:
        """
        Generate list of weeks (Sunday to Saturday) from dates.
        
        Returns:
            List of weeks, where each week is a list of dates
        """
        weeks = []
        current_week = []
        
        for d in self.dates:
            if d.weekday() == 6 and current_week:  # Sunday and week has content
                weeks.append(current_week)
                current_week = []
            current_week.append(d)
        
        if current_week:
            weeks.append(current_week)
        
        return weeks
    
    def _create_decision_variables(self):
        """
        Create all decision variables for the model.
        
        Team-based model structure:
        - team_shift[team_id, week_idx, shift]: Team has this shift in this week (Mon-Fri)
        - employee_active[emp_id, date]: Employee works on this date (Mon-Fri: derived from team shift)
        - employee_weekend_shift[emp_id, date]: Employee works on weekend (Sat-Sun ONLY, shift type from team)
        
        Important: 
        - Weekday shifts (Mon-Fri) are determined by team's shift
        - Weekend shifts (Sat-Sun): PRESENCE is individually assigned, but shift TYPE matches team's weekly shift
        """
        
        # CORE VARIABLE: Team shift assignment per week (WEEKDAYS ONLY)
        # team_shift[team_id, week_idx, shift_code] ∈ {0, 1}
        for team in self.teams:
            for week_idx in range(len(self.weeks)):
                for shift_code in self.shift_codes:
                    var_name = f"team_{team.id}_week{week_idx}_shift{shift_code}"
                    self.team_shift[(team.id, week_idx, shift_code)] = self.model.NewBoolVar(var_name)
        
        # Employee active variables for WEEKDAYS (Mon-Fri: derived from team shifts)
        # employee_active[emp_id, date] ∈ {0, 1}
        for emp in self.employees:
            for d in self.dates:
                # Only create for weekdays - weekends use employee_weekend_shift
                if d.weekday() < 5:  # Monday to Friday
                    var_name = f"emp{emp.id}_active_date{d}"
                    self.employee_active[(emp.id, d)] = self.model.NewBoolVar(var_name)
        
        # WEEKEND VARIABLE: Individual weekend work indicator (WEEKENDS ONLY)
        # employee_weekend_shift[emp_id, date] ∈ {0, 1}
        # Note: Shift TYPE is determined by team's weekly shift, only PRESENCE is variable
        # 
        # Design decision: Springers are excluded from weekend variables because they
        # don't have a team (no team shift type to derive from). This is a known
        # limitation that keeps the model consistent. Springers primarily cover weekday
        # shifts. If weekend springer coverage is needed, extend the model to support
        # flexible weekend shift types for springers.
        for emp in self.employees:
            # Only for employees with a team
            if not emp.team_id:
                continue
            
            for d in self.dates:
                # Only create for weekends
                if d.weekday() >= 5:  # Saturday or Sunday
                    var_name = f"emp{emp.id}_weekend_work_{d}"
                    self.employee_weekend_shift[(emp.id, d)] = self.model.NewBoolVar(var_name)
        
        # CROSS-TEAM ASSIGNMENT VARIABLES (NEW)
        # Allow employees to work shifts from other teams when needed to meet their hours
        # employee_cross_team_shift[emp_id, date, shift_code] ∈ {0, 1}
        # employee_cross_team_weekend[emp_id, date, shift_code] ∈ {0, 1}
        #
        # IMPORTANT: These must respect ALL constraints:
        # - 11 hours minimum rest between shifts
        # - Forbidden transitions (S→F, N→F)
        # - Max consecutive shifts
        # - Working hour limits
        # - Only shifts that the employee's team is ALLOWED to work (via allowed_shift_type_ids)
        for emp in self.employees:
            # Only for employees with a team
            if not emp.team_id:
                continue
            
            # Find employee's team
            emp_team = None
            for t in self.teams:
                if t.id == emp.team_id:
                    emp_team = t
                    break
            
            if not emp_team:
                continue
            
            # Determine which shifts this employee can work cross-team
            # RULE: Employee can only work shifts that their team is allowed to work
            allowed_shift_codes = []
            if emp_team.allowed_shift_type_ids:
                # Team has specific allowed shifts
                for shift_type_id in emp_team.allowed_shift_type_ids:
                    for st in self.shift_types:
                        if st.id == shift_type_id:
                            allowed_shift_codes.append(st.code)
                            break
            else:
                # No restriction - can work all shifts (backward compatibility)
                allowed_shift_codes = self.shift_codes
            
            # Create cross-team variables for weekdays
            for d in self.dates:
                if d.weekday() < 5:  # Monday to Friday
                    for shift_code in allowed_shift_codes:
                        var_name = f"emp{emp.id}_crossteam_{d}_{shift_code}"
                        self.employee_cross_team_shift[(emp.id, d, shift_code)] = self.model.NewBoolVar(var_name)
                else:  # Saturday or Sunday
                    for shift_code in allowed_shift_codes:
                        var_name = f"emp{emp.id}_crossteam_weekend_{d}_{shift_code}"
                        self.employee_cross_team_weekend[(emp.id, d, shift_code)] = self.model.NewBoolVar(var_name)
    
    
    def get_model(self) -> cp_model.CpModel:
        """Get the CP-SAT model"""
        return self.model
    
    def get_variables(self) -> Tuple[
        Dict[Tuple[int, int, str], cp_model.IntVar],
        Dict[Tuple[int, date], cp_model.IntVar],
        Dict[Tuple[int, date], cp_model.IntVar],
        Dict[Tuple[int, date, str], cp_model.IntVar],
        Dict[Tuple[int, date, str], cp_model.IntVar]
    ]:
        """
        Get all decision variables.
        
        Returns:
            Tuple of (team_shift, employee_active, employee_weekend_shift, 
                     employee_cross_team_shift, employee_cross_team_weekend)
            where:
            - employee_weekend_shift is keyed by (emp_id, date) only
            - employee_cross_team_shift is keyed by (emp_id, date, shift_code)
            - employee_cross_team_weekend is keyed by (emp_id, date, shift_code)
        """
        return (self.team_shift, self.employee_active, self.employee_weekend_shift, 
                self.employee_cross_team_shift, self.employee_cross_team_weekend)
    
    def get_team_by_id(self, team_id: int) -> Team:
        """Get team by ID"""
        for team in self.teams:
            if team.id == team_id:
                return team
        raise ValueError(f"Team {team_id} not found")
    
    def get_employee_by_id(self, emp_id: int) -> Employee:
        """Get employee by ID"""
        for emp in self.employees:
            if emp.id == emp_id:
                return emp
        raise ValueError(f"Employee {emp_id} not found")
    
    def get_shift_type_by_code(self, code: str) -> ShiftType:
        """Get shift type by code"""
        for st in self.shift_types:
            if st.code == code:
                return st
        raise ValueError(f"Shift type {code} not found")
    
    def get_week_index(self, d: date) -> int:
        """Get the week index for a given date"""
        for week_idx, week_dates in enumerate(self.weeks):
            if d in week_dates:
                return week_idx
        raise ValueError(f"Date {d} not in any week")
    
    def print_model_statistics(self):
        """Print statistics about the model"""
        print("=" * 60)
        print("MODEL STATISTICS (TEAM-BASED)")
        print("=" * 60)
        print(f"Planning period: {self.start_date} to {self.end_date}")
        print(f"Number of days: {len(self.dates)}")
        actual_weeks = len(self.dates) / 7.0
        print(f"Number of weeks: {actual_weeks:.1f} (approx {len(self.weeks)} calendar weeks)")
        print(f"Number of teams: {len(self.teams)}")
        for team in self.teams:
            team_members = [e for e in self.employees if e.team_id == team.id]
            print(f"  - {team.name}: {len(team_members)} members")
        print(f"Number of employees: {len(self.employees)}")
        print(f"  - In teams: {len([e for e in self.employees if e.team_id])}")
        print(f"Number of shift types: {len(self.shift_codes)}")
        print(f"Shift types: {', '.join(self.shift_codes)}")
        print(f"Number of absences: {len(self.absences)}")
        print()
        print(f"Decision variables:")
        print(f"  - Team shift variables: {len(self.team_shift)}")
        print(f"  - Employee active variables (weekdays): {len(self.employee_active)}")
        print(f"  - Employee weekend shift variables: {len(self.employee_weekend_shift)}")
        print(f"  - Total variables: {len(self.team_shift) + len(self.employee_active) + len(self.employee_weekend_shift)}")
        print("=" * 60)


def create_shift_planning_model(
    employees: List[Employee],
    teams: List[Team],
    start_date: date,
    end_date: date,
    absences: List[Absence],
    shift_types: List[ShiftType],
    locked_team_shift: Dict[Tuple[int, int], str] = None,
    locked_employee_weekend: Dict[Tuple[int, date], bool] = None,
    locked_absence: Dict[Tuple[int, date], str] = None,
    locked_employee_shift: Dict[Tuple[int, date], str] = None,
    previous_employee_shifts: Dict[Tuple[int, date], str] = None
) -> ShiftPlanningModel:
    """
    Factory function to create a shift planning model.
    
    Args:
        employees: List of all employees
        teams: List of teams
        start_date: Start date of planning period
        end_date: End date of planning period
        absences: List of employee absences (AUTHORITATIVE - always preserved)
        shift_types: List of shift types (REQUIRED - must be loaded from database)
        locked_team_shift: Dict mapping (team_id, week_idx) -> shift_code (manual overrides)
        locked_employee_weekend: Dict mapping (emp_id, date) -> bool (manual overrides)
        locked_absence: Dict mapping (emp_id, date) -> absence_code (U/AU/L) (manual overrides)
        locked_employee_shift: Dict mapping (emp_id, date) -> shift_code (existing assignments from previous planning)
        previous_employee_shifts: Dict mapping (emp_id, date) -> shift_code for dates BEFORE planning period
        
    Returns:
        ShiftPlanningModel instance
    
    Note:
        shift_types MUST be loaded from the database. STANDARD_SHIFT_TYPES should only
        be used for database initialization, not at runtime.
    """
    return ShiftPlanningModel(
        employees, teams, start_date, end_date, absences, shift_types,
        locked_team_shift, locked_employee_weekend, locked_absence, locked_employee_shift,
        None, None, None, previous_employee_shifts
    )


if __name__ == "__main__":
    # Test model creation
    from data_loader import generate_sample_data
    
    employees, teams, absences = generate_sample_data()
    
    start = date.today()
    end = start + timedelta(days=30)
    
    planning_model = create_shift_planning_model(employees, teams, start, end, absences)
    planning_model.print_model_statistics()
    
    print("\nModel created successfully!")
    print(f"Ready to add constraints and solve.")
