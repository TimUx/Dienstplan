"""
Integration smoke: constraints package exports the full solver surface.

Prevents accidental removal when refactoring the constraints/ package.
"""

import pytest


@pytest.mark.integration
def test_constraints_package_exports_solver_symbols():
    from constraints import (
        add_consecutive_shifts_constraints,
        add_cross_shift_capacity_enforcement,
        add_daily_shift_ratio_constraints,
        add_employee_team_linkage_constraints,
        add_employee_weekly_rotation_order_constraints,
        add_fairness_objectives,
        add_minimum_consecutive_weekday_shifts_constraints,
        add_no_gap_constraints,
        add_rest_time_constraints,
        add_shift_sequence_grouping_constraints,
        add_shift_stability_constraints,
        add_staffing_constraints,
        add_team_member_block_constraints,
        add_team_night_shift_consistency_constraints,
        add_team_rotation_constraints,
        add_team_shift_assignment_constraints,
        add_total_weekend_staffing_limit,
        add_weekend_shift_consistency_constraints,
        add_weekly_available_employee_constraint,
        add_weekly_block_constraints,
        add_weekly_shift_type_limit_constraints,
        add_working_hours_constraints,
    )

    for fn in (
        add_team_shift_assignment_constraints,
        add_team_rotation_constraints,
        add_employee_weekly_rotation_order_constraints,
        add_employee_team_linkage_constraints,
        add_staffing_constraints,
        add_total_weekend_staffing_limit,
        add_cross_shift_capacity_enforcement,
        add_daily_shift_ratio_constraints,
        add_rest_time_constraints,
        add_shift_stability_constraints,
        add_shift_sequence_grouping_constraints,
        add_minimum_consecutive_weekday_shifts_constraints,
        add_weekly_shift_type_limit_constraints,
        add_weekend_shift_consistency_constraints,
        add_team_night_shift_consistency_constraints,
        add_consecutive_shifts_constraints,
        add_working_hours_constraints,
        add_no_gap_constraints,
        add_weekly_available_employee_constraint,
        add_weekly_block_constraints,
        add_team_member_block_constraints,
        add_fairness_objectives,
    ):
        assert callable(fn)
