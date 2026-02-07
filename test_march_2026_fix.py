"""
Test for March 2026 planning INFEASIBLE issue.

Root cause: Existing boundary week assignments (Feb 23-28) were locked with old configuration
(N=5 workers) but current configuration limits N shift to max 3, creating conflict.

Fix: Skip locking employee assignments in boundary weeks to allow re-planning with current config.
"""

import unittest
from datetime import date, timedelta
from entities import Employee, Team, ShiftType
from model import create_shift_planning_model
from solver import solve_shift_planning


class TestMarch2026Fix(unittest.TestCase):
    """Test that March 2026 scenario is now feasible."""
    
    def test_march_2026_scenario(self):
        """
        Reproduce March 2026 INFEASIBLE scenario:
        - 3 teams with 5 members each = 15 employees
        - F: min 4, max 8
        - S: min 3, max 6
        - N: min 3, max 3  ← Problem: Team has 5 members, N max is 3
        - Planning period: March 1-31, 2026
        """
        # Create shift types matching the database
        shift_types = [
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
                min_staff_weekday=3, max_staff_weekday=3,  # ← Problem: max 3 but team has 5
                min_staff_weekend=2, max_staff_weekend=3,
                max_consecutive_days=3,
                weekly_working_hours=48.0,
                works_saturday=True, works_sunday=True
            )
        ]
        
        # Create 3 teams with 5 members each
        teams = [
            Team(id=1, name="Team Alpha", allowed_shift_type_ids=[1, 2, 3]),
            Team(id=2, name="Team Beta", allowed_shift_type_ids=[1, 2, 3]),
            Team(id=3, name="Team Gamma", allowed_shift_type_ids=[1, 2, 3])
        ]
        
        # Create 15 employees (5 per team)
        employees = []
        emp_id = 1
        for team_idx, team in enumerate(teams):
            for member in range(5):
                employees.append(Employee(
                    id=emp_id,
                    vorname=f"Employee{emp_id}",
                    name="Test",
                    personalnummer=f"PN{emp_id:03d}",
                    team_id=team.id
                ))
                emp_id += 1
        
        # Planning period: March 2026
        start_date = date(2026, 3, 1)
        end_date = date(2026, 3, 31)
        
        absences = []
        
        # Create model
        planning_model = create_shift_planning_model(
            employees, teams, start_date, end_date, absences,
            shift_types=shift_types
        )
        
        # Try to solve
        result = solve_shift_planning(planning_model, time_limit_seconds=60)
        
        # This should succeed, not return None
        self.assertIsNotNone(result, 
            "March 2026 planning should be FEASIBLE. "
            "The solver should be able to handle team size (5) > N shift max (3) "
            "by allowing fewer than all team members to be active.")
        
        if result:
            assignments, complete_schedule = result
            print(f"✓ Solution found with {len(assignments)} assignments")
            
            # Verify that N shift never has more than 3 workers
            from collections import Counter
            for d in [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]:
                n_workers = sum(1 for a in assignments if a.date == d and a.shift_code == "N")
                self.assertLessEqual(n_workers, 3, 
                    f"On {d}, N shift has {n_workers} workers but max is 3")


if __name__ == "__main__":
    unittest.main()
