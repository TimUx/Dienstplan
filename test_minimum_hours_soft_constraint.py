"""
Test that minimum hours (192h) constraint is SOFT, not HARD.

Root cause of March 2026 INFEASIBLE:
- Team size: 5 members
- N shift max: 3 staff (only 3 of 5 can be active per day)
- Minimum hours: 192h HARD constraint
- Weekly consistency: employees must work same shift all week

When a team is on N shift for a week:
- Only 3 of 5 members can be active
- The 2 inactive members lose hours that week
- To meet 192h, they MUST do cross-team work
- But cross-team capacity + weekly consistency can create conflicts

Solution: Make 192h SOFT with very high penalty (100x) so it's enforced
unless physically impossible due to capacity constraints.
"""

import unittest
from datetime import date
from entities import Employee, Team, ShiftType
from model import create_shift_planning_model
from solver import solve_shift_planning


class TestMinimumHoursSoftConstraint(unittest.TestCase):
    """Test that 192h minimum is soft, allowing feasibility when capacity-limited."""
    
    def setUp(self):
        """Create standard test configuration."""
        self.shift_types = [
            ShiftType(
                id=1, code="F", name="Frühschicht",
                start_time="05:45", end_time="13:45",
                hours=8.0,
                min_staff_weekday=4, max_staff_weekday=8,
                min_staff_weekend=2, max_staff_weekend=3,
                max_consecutive_days=6,
                weekly_working_hours=48.0,
                works_saturday=True, works_sunday=True
            ),
            ShiftType(
                id=2, code="S", name="Spätschicht",
                start_time="13:45", end_time="21:45",
                hours=8.0,
                min_staff_weekday=3, max_staff_weekday=6,
                min_staff_weekend=2, max_staff_weekend=3,
                max_consecutive_days=6,
                weekly_working_hours=48.0,
                works_saturday=True, works_sunday=True
            ),
            ShiftType(
                id=3, code="N", name="Nachtschicht",
                start_time="21:45", end_time="05:45",
                hours=8.0,
                min_staff_weekday=3, max_staff_weekday=3,  # ← KEY: max 3, team has 5
                min_staff_weekend=2, max_staff_weekend=3,
                max_consecutive_days=3,
                weekly_working_hours=48.0,
                works_saturday=True, works_sunday=True
            )
        ]
        
        self.teams = [
            Team(id=1, name="Team Alpha", allowed_shift_type_ids=[1, 2, 3]),
            Team(id=2, name="Team Beta", allowed_shift_type_ids=[1, 2, 3]),
            Team(id=3, name="Team Gamma", allowed_shift_type_ids=[1, 2, 3])
        ]
        
        # 15 employees: 5 per team
        self.employees = []
        emp_id = 1
        for team in self.teams:
            for member in range(5):
                self.employees.append(Employee(
                    id=emp_id,
                    vorname=f"Employee{emp_id}",
                    name="Test",
                    personalnummer=f"PN{emp_id:03d}",
                    team_id=team.id
                ))
                emp_id += 1
    
    def test_march_2026_is_feasible(self):
        """
        March 2026 should now be FEASIBLE with soft 192h constraint.
        
        Configuration:
        - 42 days (Feb 23 - Apr 5), 6 weeks
        - 3 teams × 5 members = 15 employees
        - N shift: min 3, max 3 (team has 5 members)
        - Rotation: F → N → S (each team works N for 2 weeks)
        
        Previously INFEASIBLE because 192h was HARD.
        Now FEASIBLE because 192h is SOFT (very high penalty but not blocking).
        """
        start_date = date(2026, 3, 1)
        end_date = date(2026, 3, 31)
        
        planning_model = create_shift_planning_model(
            self.employees, self.teams, start_date, end_date, [],
            shift_types=self.shift_types
        )
        
        # This should succeed (not None)
        result = solve_shift_planning(planning_model, time_limit_seconds=60)
        
        self.assertIsNotNone(result, 
            "March 2026 planning should be FEASIBLE with soft 192h constraint")
        
        if result:
            assignments, complete_schedule = result
            print(f"\n✓ March 2026 solution found with {len(assignments)} assignments")
            
            # Verify N shift never exceeds max
            from collections import defaultdict
            from datetime import timedelta
            
            dates = [start_date + timedelta(days=i) 
                    for i in range((end_date - start_date).days + 1)]
            
            for d in dates:
                n_workers = sum(1 for a in assignments 
                               if a.date == d and a.shift_code == "N")
                self.assertLessEqual(n_workers, 3, 
                    f"N shift on {d} has {n_workers} workers but max is 3")
            
            # Check employee hours (some may be below 192h due to N constraint)
            emp_hours = defaultdict(float)
            for a in assignments:
                emp_hours[a.employee_id] += 8.0
            
            below_min = [emp_id for emp_id, hours in emp_hours.items() 
                        if hours < 192]
            
            if below_min:
                print(f"  Note: {len(below_min)} employees below 192h due to N max=3")
                print(f"  This is acceptable since 192h is now soft")
    
    def test_february_2026_still_works(self):
        """
        Verify February 2026 still works after making 192h soft.
        
        Configuration:
        - 35 days (Jan 26 - Mar 1), 5 weeks
        - Should still be feasible
        """
        start_date = date(2026, 2, 1)
        end_date = date(2026, 2, 28)
        
        planning_model = create_shift_planning_model(
            self.employees, self.teams, start_date, end_date, [],
            shift_types=self.shift_types
        )
        
        # This should succeed
        result = solve_shift_planning(planning_model, time_limit_seconds=60)
        
        self.assertIsNotNone(result, 
            "February 2026 planning should still be FEASIBLE")
        
        if result:
            assignments, _ = result
            print(f"\n✓ February 2026 solution found with {len(assignments)} assignments")
    
    def test_constraint_is_soft_not_hard(self):
        """
        Verify that 192h minimum is actually soft.
        
        Create a scenario where 192h is impossible to achieve,
        and verify that:
        1. The model is still FEASIBLE
        2. Some employees are below 192h
        3. The solver tried hard to meet 192h (high penalty)
        """
        # Create extreme scenario: very short planning period
        # Only 3 weeks = 21 days
        # Maximum possible: 21 days × 8h = 168h (if working every day)
        # But with N weeks (only 3/5 active), even less
        
        start_date = date(2026, 3, 1)
        end_date = date(2026, 3, 21)  # Only 21 days
        
        planning_model = create_shift_planning_model(
            self.employees, self.teams, start_date, end_date, [],
            shift_types=self.shift_types
        )
        
        # Should be FEASIBLE even though 192h is impossible
        result = solve_shift_planning(planning_model, time_limit_seconds=60)
        
        self.assertIsNotNone(result, 
            "Short period should be FEASIBLE even if 192h impossible")
        
        if result:
            assignments, _ = result
            
            # Calculate hours
            from collections import defaultdict
            emp_hours = defaultdict(float)
            for a in assignments:
                emp_hours[a.employee_id] += 8.0
            
            # At least some employees should be below 192h
            below_min = [h for h in emp_hours.values() if h < 192]
            self.assertTrue(len(below_min) > 0, 
                "Some employees should be below 192h in short period")
            
            print(f"\n✓ Short period (21 days) is FEASIBLE")
            print(f"  {len(below_min)}/{len(emp_hours)} employees below 192h")
            print(f"  Confirms 192h is SOFT, not HARD")


if __name__ == "__main__":
    unittest.main(verbosity=2)
