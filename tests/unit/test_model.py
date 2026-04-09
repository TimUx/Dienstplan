"""Unit tests for the shift planning model creation."""

import pytest
from datetime import date, timedelta


from entities import STANDARD_SHIFT_TYPES
from model import ShiftPlanningModel, create_shift_planning_model
from data_loader import generate_sample_data


def _make_model(start=None, end=None, shift_types=None, absences=None):
    """Helper: build a model using sample data."""
    employees, teams, sample_absences = generate_sample_data()
    st = shift_types if shift_types is not None else list(STANDARD_SHIFT_TYPES)
    s = start or date(2025, 1, 1)
    e = end or date(2025, 1, 31)
    abs_ = absences if absences is not None else sample_absences
    return ShiftPlanningModel(
        employees=employees,
        teams=teams,
        start_date=s,
        end_date=e,
        absences=abs_,
        shift_types=st,
    )


class TestShiftPlanningModelCreation:
    def test_raises_value_error_for_none_shift_types(self):
        employees, teams, absences = generate_sample_data()
        with pytest.raises(ValueError, match="shift_types is required"):
            ShiftPlanningModel(
                employees=employees,
                teams=teams,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
                absences=absences,
                shift_types=None,
            )

    def test_raises_value_error_for_empty_shift_types(self):
        employees, teams, absences = generate_sample_data()
        with pytest.raises(ValueError):
            ShiftPlanningModel(
                employees=employees,
                teams=teams,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
                absences=absences,
                shift_types=[],
            )

    def test_model_created_with_valid_inputs(self):
        model = _make_model()
        assert model is not None

    def test_model_contains_all_employees(self):
        employees, teams, absences = generate_sample_data()
        model = ShiftPlanningModel(
            employees=employees,
            teams=teams,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            absences=absences,
            shift_types=list(STANDARD_SHIFT_TYPES),
        )
        assert len(model.employees) == len(employees)

    def test_model_contains_all_teams(self):
        employees, teams, absences = generate_sample_data()
        model = ShiftPlanningModel(
            employees=employees,
            teams=teams,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            absences=absences,
            shift_types=list(STANDARD_SHIFT_TYPES),
        )
        assert len(model.teams) == len(teams)


class TestModelDateExtension:
    """Planning period is extended to complete Sun–Sat weeks."""

    def test_start_extended_to_sunday_when_not_sunday(self):
        # 2025-01-01 is Wednesday (weekday=2); must extend back to Sunday 2024-12-29
        model = _make_model(start=date(2025, 1, 1), end=date(2025, 1, 31))
        assert model.start_date.weekday() == 6  # Sunday

    def test_end_extended_to_saturday_when_not_saturday(self):
        # 2025-01-31 is Friday (weekday=4); must extend forward to Saturday 2025-02-01
        model = _make_model(start=date(2025, 1, 1), end=date(2025, 1, 31))
        assert model.end_date.weekday() == 5  # Saturday

    def test_original_dates_stored(self):
        s, e = date(2025, 1, 1), date(2025, 1, 31)
        model = _make_model(start=s, end=e)
        assert model.original_start_date == s
        assert model.original_end_date == e

    def test_dates_list_spans_extended_period(self):
        model = _make_model(start=date(2025, 1, 1), end=date(2025, 1, 31))
        assert model.dates[0] == model.start_date
        assert model.dates[-1] == model.end_date

    def test_dates_list_is_contiguous(self):
        model = _make_model(start=date(2025, 1, 1), end=date(2025, 1, 31))
        for i in range(len(model.dates) - 1):
            assert (model.dates[i + 1] - model.dates[i]).days == 1

    def test_already_sunday_start_not_extended_further(self):
        # 2025-01-05 is Sunday
        model = _make_model(start=date(2025, 1, 5), end=date(2025, 1, 11))
        assert model.start_date == date(2025, 1, 5)

    def test_already_saturday_end_not_extended_further(self):
        # 2025-01-11 is Saturday
        model = _make_model(start=date(2025, 1, 5), end=date(2025, 1, 11))
        assert model.end_date == date(2025, 1, 11)


class TestCreateShiftPlanningModelFunction:
    def test_function_returns_model(self):
        employees, teams, absences = generate_sample_data()
        model = create_shift_planning_model(
            employees=employees,
            teams=teams,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            absences=absences,
            shift_types=list(STANDARD_SHIFT_TYPES),
        )
        assert isinstance(model, ShiftPlanningModel)

    def test_function_raises_for_none_shift_types(self):
        employees, teams, absences = generate_sample_data()
        with pytest.raises(ValueError):
            create_shift_planning_model(
                employees=employees,
                teams=teams,
                start_date=date(2025, 1, 1),
                end_date=date(2025, 1, 31),
                absences=absences,
                shift_types=None,
            )
