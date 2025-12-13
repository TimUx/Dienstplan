"""
OR-Tools CP-SAT model builder for shift planning.
Creates decision variables and orchestrates constraint addition.
"""

from ortools.sat.python import cp_model
from datetime import date, timedelta
from typing import Dict, List, Tuple
from entities import Employee, Absence, ShiftType, STANDARD_SHIFT_TYPES


class ShiftPlanningModel:
    """
    Builds and manages the OR-Tools CP-SAT model for shift planning.
    """
    
    def __init__(
        self,
        employees: List[Employee],
        start_date: date,
        end_date: date,
        absences: List[Absence],
        shift_types: List[ShiftType] = None
    ):
        """
        Initialize the shift planning model.
        
        Args:
            employees: List of all employees
            start_date: Start date of planning period
            end_date: End date of planning period
            absences: List of employee absences
            shift_types: List of shift types (defaults to STANDARD_SHIFT_TYPES)
        """
        self.model = cp_model.CpModel()
        self.employees = employees
        self.start_date = start_date
        self.end_date = end_date
        self.absences = absences
        self.shift_types = shift_types or STANDARD_SHIFT_TYPES
        
        # Generate list of dates
        self.dates = []
        current = start_date
        while current <= end_date:
            self.dates.append(current)
            current += timedelta(days=1)
        
        # Get main shift codes (F, S, N)
        self.shift_codes = [st.code for st in self.shift_types if st.code in ["F", "S", "N"]]
        
        # Decision variables
        self.x = {}  # x[employee_id, date, shift_code] = 0 or 1
        self.bmt_vars = {}  # BMT assignments
        self.bsb_vars = {}  # BSB assignments
        
        # Build the model
        self._create_decision_variables()
    
    def _create_decision_variables(self):
        """
        Create all decision variables for the model.
        
        Variables:
        - x[(emp_id, date, shift)]: Boolean - employee is assigned to shift on date
        - bmt_vars[(emp_id, date)]: Boolean - employee is assigned BMT on date
        - bsb_vars[(emp_id, date)]: Boolean - employee is assigned BSB on date
        """
        
        # Main shift assignment variables x[p][d][s]
        # For each employee, date, and shift type
        for emp in self.employees:
            for d in self.dates:
                for shift_code in self.shift_codes:
                    var_name = f"x_emp{emp.id}_date{d}_shift{shift_code}"
                    self.x[(emp.id, d, shift_code)] = self.model.NewBoolVar(var_name)
        
        # BMT (Brandmeldetechniker) variables - only for qualified employees on weekdays
        bmt_qualified = [emp for emp in self.employees if emp.is_brandmeldetechniker]
        for emp in bmt_qualified:
            for d in self.dates:
                if d.weekday() < 5:  # Monday to Friday
                    var_name = f"bmt_emp{emp.id}_date{d}"
                    self.bmt_vars[(emp.id, d)] = self.model.NewBoolVar(var_name)
        
        # BSB (Brandschutzbeauftragter) variables - only for qualified employees on weekdays
        bsb_qualified = [emp for emp in self.employees if emp.is_brandschutzbeauftragter]
        for emp in bsb_qualified:
            for d in self.dates:
                if d.weekday() < 5:  # Monday to Friday
                    var_name = f"bsb_emp{emp.id}_date{d}"
                    self.bsb_vars[(emp.id, d)] = self.model.NewBoolVar(var_name)
    
    def get_model(self) -> cp_model.CpModel:
        """Get the CP-SAT model"""
        return self.model
    
    def get_variables(self) -> Tuple[
        Dict[Tuple[int, date, str], cp_model.IntVar],
        Dict[Tuple[int, date], cp_model.IntVar],
        Dict[Tuple[int, date], cp_model.IntVar]
    ]:
        """
        Get all decision variables.
        
        Returns:
            Tuple of (x, bmt_vars, bsb_vars)
        """
        return self.x, self.bmt_vars, self.bsb_vars
    
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
    
    def print_model_statistics(self):
        """Print statistics about the model"""
        print("=" * 60)
        print("MODEL STATISTICS")
        print("=" * 60)
        print(f"Planning period: {self.start_date} to {self.end_date}")
        print(f"Number of days: {len(self.dates)}")
        print(f"Number of employees: {len(self.employees)}")
        print(f"  - Regular employees: {len([e for e in self.employees if not e.is_springer])}")
        print(f"  - Springers: {len([e for e in self.employees if e.is_springer])}")
        print(f"  - BMT qualified: {len([e for e in self.employees if e.is_brandmeldetechniker])}")
        print(f"  - BSB qualified: {len([e for e in self.employees if e.is_brandschutzbeauftragter])}")
        print(f"Number of shift types: {len(self.shift_codes)}")
        print(f"Shift types: {', '.join(self.shift_codes)}")
        print(f"Number of absences: {len(self.absences)}")
        print()
        print(f"Decision variables:")
        print(f"  - Main shift variables (x): {len(self.x)}")
        print(f"  - BMT variables: {len(self.bmt_vars)}")
        print(f"  - BSB variables: {len(self.bsb_vars)}")
        print(f"  - Total variables: {len(self.x) + len(self.bmt_vars) + len(self.bsb_vars)}")
        print("=" * 60)


def create_shift_planning_model(
    employees: List[Employee],
    start_date: date,
    end_date: date,
    absences: List[Absence],
    shift_types: List[ShiftType] = None
) -> ShiftPlanningModel:
    """
    Factory function to create a shift planning model.
    
    Args:
        employees: List of all employees
        start_date: Start date of planning period
        end_date: End date of planning period
        absences: List of employee absences
        shift_types: List of shift types (defaults to STANDARD_SHIFT_TYPES)
        
    Returns:
        ShiftPlanningModel instance
    """
    return ShiftPlanningModel(employees, start_date, end_date, absences, shift_types)


if __name__ == "__main__":
    # Test model creation
    from data_loader import generate_sample_data
    
    employees, teams, absences = generate_sample_data()
    
    start = date.today()
    end = start + timedelta(days=30)
    
    planning_model = create_shift_planning_model(employees, start, end, absences)
    planning_model.print_model_statistics()
    
    print("\nModel created successfully!")
    print(f"Ready to add constraints and solve.")
