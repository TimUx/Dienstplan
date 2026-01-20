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
        locked_td: Dict[Tuple[int, int], bool] = None,
        locked_absence: Dict[Tuple[int, date], str] = None,
        ytd_weekend_counts: Dict[int, int] = None,
        ytd_night_counts: Dict[int, int] = None,
        ytd_holiday_counts: Dict[int, int] = None
    ):
        """
        Initialize the shift planning model.
        
        Args:
            employees: List of all employees
            teams: List of teams
            start_date: Start date of planning period
            end_date: End date of planning period
            absences: List of employee absences (AUTHORITATIVE - always locked)
            shift_types: List of shift types (defaults to STANDARD_SHIFT_TYPES)
            locked_team_shift: Dict mapping (team_id, week_idx) -> shift_code (manual overrides)
            locked_employee_weekend: Dict mapping (emp_id, date) -> bool (manual overrides)
            locked_td: Dict mapping (emp_id, week_idx) -> bool (manual overrides)
            locked_absence: Dict mapping (emp_id, date) -> absence_code (U/AU/L) (manual overrides)
            ytd_weekend_counts: Dict mapping employee_id -> count of weekend days worked this year (for fairness)
            ytd_night_counts: Dict mapping employee_id -> count of night shifts worked this year (for fairness)
            ytd_holiday_counts: Dict mapping employee_id -> count of holidays worked this year (for fairness)
        
        Note on key structures:
        - locked_td uses week_idx because TD is a weekly assignment (Mon-Fri)
        - locked_absence uses date because absences are daily (can span partial weeks)
        - This difference reflects the granularity of the underlying business logic
        
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
        self.shift_types = shift_types or STANDARD_SHIFT_TYPES
        
        # Manual overrides (locked assignments)
        self.locked_team_shift = locked_team_shift or {}
        self.locked_employee_weekend = locked_employee_weekend or {}
        self.locked_td = locked_td or {}
        self.locked_absence = locked_absence or {}  # NEW: locked absence assignments
        
        # Year-to-date statistics for fairness tracking
        self.ytd_weekend_counts = ytd_weekend_counts or {}
        self.ytd_night_counts = ytd_night_counts or {}
        self.ytd_holiday_counts = ytd_holiday_counts or {}
        self.locked_td = locked_td or {}
        self.locked_absence = locked_absence or {}  # NEW: locked absence assignments
        
        # Generate list of dates
        self.dates = []
        current = start_date
        while current <= end_date:
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
        self.td_vars = {}  # td[employee_id, week_idx] = 0 or 1 (Tagdienst assignment)
        
        # Build the model
        self._create_decision_variables()
        self._apply_locked_assignments()
    
    
    def _apply_locked_assignments(self):
        """
        Apply manual overrides (locked assignments) as hard constraints.
        
        When administrators or dispatchers fix certain assignments:
        - locked_team_shift: Forces a team to a specific shift in a week
        - locked_employee_weekend: Forces employee presence/absence on weekend
        - locked_td: Forces TD assignment to specific employee in a week
        """
        # Apply locked team shift assignments
        for (team_id, week_idx), shift_code in self.locked_team_shift.items():
            if (team_id, week_idx, shift_code) in self.team_shift:
                # Force this team to have this shift in this week
                # Note: Other shifts for this team/week are implicitly set to 0
                # by the "exactly one shift per team per week" constraint
                self.model.Add(self.team_shift[(team_id, week_idx, shift_code)] == 1)
        
        # Apply locked employee weekend work
        for (emp_id, d), is_working in self.locked_employee_weekend.items():
            if (emp_id, d) in self.employee_weekend_shift:
                # Force employee to work (1) or not work (0) on this weekend day
                self.model.Add(self.employee_weekend_shift[(emp_id, d)] == (1 if is_working else 0))
        
        # Apply locked TD assignments
        for (emp_id, week_idx), has_td in self.locked_td.items():
            if (emp_id, week_idx) in self.td_vars:
                # Force TD assignment (1) or no TD (0) for this employee in this week
                self.model.Add(self.td_vars[(emp_id, week_idx)] == (1 if has_td else 0))
    
    
    def _generate_weeks(self) -> List[List[date]]:
        """
        Generate list of weeks (Monday to Sunday) from dates.
        
        Returns:
            List of weeks, where each week is a list of dates
        """
        weeks = []
        current_week = []
        
        for d in self.dates:
            if d.weekday() == 0 and current_week:  # Monday and week has content
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
        - td_vars[emp_id, week_idx]: Employee has TD (Tagdienst) duty in this week
        
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
        
        # TD (Tagdienst) variables - weekly assignment on Monday-Friday
        # td_vars[emp_id, week_idx] ∈ {0, 1}
        td_qualified = [emp for emp in self.employees if emp.can_do_td]
        for emp in td_qualified:
            for week_idx in range(len(self.weeks)):
                # Only create TD variable if week has weekdays
                week_dates = self.weeks[week_idx]
                has_weekdays = any(d.weekday() < 5 for d in week_dates)
                if has_weekdays:
                    var_name = f"td_emp{emp.id}_week{week_idx}"
                    self.td_vars[(emp.id, week_idx)] = self.model.NewBoolVar(var_name)
    
    
    def get_model(self) -> cp_model.CpModel:
        """Get the CP-SAT model"""
        return self.model
    
    def get_variables(self) -> Tuple[
        Dict[Tuple[int, int, str], cp_model.IntVar],
        Dict[Tuple[int, date], cp_model.IntVar],
        Dict[Tuple[int, date], cp_model.IntVar],
        Dict[Tuple[int, date, str], cp_model.IntVar],
        Dict[Tuple[int, date, str], cp_model.IntVar],
        Dict[Tuple[int, int], cp_model.IntVar]
    ]:
        """
        Get all decision variables.
        
        Returns:
            Tuple of (team_shift, employee_active, employee_weekend_shift, 
                     employee_cross_team_shift, employee_cross_team_weekend, td_vars)
            where:
            - employee_weekend_shift is keyed by (emp_id, date) only
            - employee_cross_team_shift is keyed by (emp_id, date, shift_code)
            - employee_cross_team_weekend is keyed by (emp_id, date, shift_code)
        """
        return (self.team_shift, self.employee_active, self.employee_weekend_shift, 
                self.employee_cross_team_shift, self.employee_cross_team_weekend, self.td_vars)
    
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
        print(f"  - TD qualified: {len([e for e in self.employees if e.can_do_td])}")
        print(f"Number of shift types: {len(self.shift_codes)}")
        print(f"Shift types: {', '.join(self.shift_codes)}")
        print(f"Number of absences: {len(self.absences)}")
        print()
        print(f"Decision variables:")
        print(f"  - Team shift variables: {len(self.team_shift)}")
        print(f"  - Employee active variables (weekdays): {len(self.employee_active)}")
        print(f"  - Employee weekend shift variables: {len(self.employee_weekend_shift)}")
        print(f"  - TD variables: {len(self.td_vars)}")
        print(f"  - Total variables: {len(self.team_shift) + len(self.employee_active) + len(self.employee_weekend_shift) + len(self.td_vars)}")
        print("=" * 60)


def create_shift_planning_model(
    employees: List[Employee],
    teams: List[Team],
    start_date: date,
    end_date: date,
    absences: List[Absence],
    shift_types: List[ShiftType] = None,
    locked_team_shift: Dict[Tuple[int, int], str] = None,
    locked_employee_weekend: Dict[Tuple[int, date], bool] = None,
    locked_td: Dict[Tuple[int, int], bool] = None,
    locked_absence: Dict[Tuple[int, date], str] = None
) -> ShiftPlanningModel:
    """
    Factory function to create a shift planning model.
    
    Args:
        employees: List of all employees
        teams: List of teams
        start_date: Start date of planning period
        end_date: End date of planning period
        absences: List of employee absences (AUTHORITATIVE - always preserved)
        shift_types: List of shift types (defaults to STANDARD_SHIFT_TYPES)
        locked_team_shift: Dict mapping (team_id, week_idx) -> shift_code (manual overrides)
        locked_employee_weekend: Dict mapping (emp_id, date) -> bool (manual overrides)
        locked_td: Dict mapping (emp_id, week_idx) -> bool (manual overrides)
        locked_absence: Dict mapping (emp_id, date) -> absence_code (U/AU/L) (manual overrides)
        
    Returns:
        ShiftPlanningModel instance
    """
    return ShiftPlanningModel(
        employees, teams, start_date, end_date, absences, shift_types,
        locked_team_shift, locked_employee_weekend, locked_td, locked_absence
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
