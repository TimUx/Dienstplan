"""Unit tests for the validation module."""

import pytest
from datetime import date, timedelta
from collections import defaultdict


from entities import (
    Employee, Absence, AbsenceType, ShiftAssignment, STANDARD_SHIFT_TYPES,
    get_shift_type_by_code,
)
from validation import (
    ValidationResult,
    validate_one_shift_per_day,
    validate_no_work_when_absent,
    validate_rest_times,
    validate_staffing_requirements,
    validate_shift_plan,
)

# Shift type IDs from STANDARD_SHIFT_TYPES
F_ID = 1   # Früh  05:45-13:45
S_ID = 2   # Spät  13:45-21:45
N_ID = 3   # Nacht 21:45-05:45


def _make_emp(id=1, vorname="A", name="B", team_id=1):
    return Employee(id=id, vorname=vorname, name=name,
                    personalnummer=f"P{id:04d}", team_id=team_id)


def _make_assign(id, employee_id, shift_type_id, d):
    return ShiftAssignment(id=id, employee_id=employee_id,
                           shift_type_id=shift_type_id, date=d)


def _group_by_emp_date(assignments):
    result = defaultdict(list)
    for a in assignments:
        result[(a.employee_id, a.date)].append(a)
    return dict(result)


def _group_by_date(assignments):
    result = defaultdict(list)
    for a in assignments:
        result[a.date].append(a)
    return dict(result)


# ---------------------------------------------------------------------------
# validate_one_shift_per_day
# ---------------------------------------------------------------------------

class TestValidateOneShiftPerDay:
    def test_no_duplicates_is_valid(self):
        result = ValidationResult()
        assignments = [
            _make_assign(1, 1, F_ID, date(2025, 1, 6)),
            _make_assign(2, 2, S_ID, date(2025, 1, 6)),
        ]
        validate_one_shift_per_day(result, _group_by_emp_date(assignments))
        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_duplicate_same_day_adds_violation(self):
        result = ValidationResult()
        d = date(2025, 1, 6)
        assignments = [
            _make_assign(1, 1, F_ID, d),
            _make_assign(2, 1, S_ID, d),  # same employee, same day
        ]
        validate_one_shift_per_day(result, _group_by_emp_date(assignments))
        assert result.is_valid is False
        assert len(result.violations) == 1

    def test_same_employee_different_days_is_valid(self):
        result = ValidationResult()
        assignments = [
            _make_assign(1, 1, F_ID, date(2025, 1, 6)),
            _make_assign(2, 1, S_ID, date(2025, 1, 7)),
        ]
        validate_one_shift_per_day(result, _group_by_emp_date(assignments))
        assert result.is_valid is True

    def test_multiple_duplicates_all_detected(self):
        result = ValidationResult()
        d = date(2025, 1, 6)
        emp1_assignments = [_make_assign(1, 1, F_ID, d), _make_assign(2, 1, S_ID, d)]
        emp2_assignments = [_make_assign(3, 2, F_ID, d), _make_assign(4, 2, N_ID, d)]
        all_a = emp1_assignments + emp2_assignments
        validate_one_shift_per_day(result, _group_by_emp_date(all_a))
        assert len(result.violations) == 2

    def test_empty_assignments_is_valid(self):
        result = ValidationResult()
        validate_one_shift_per_day(result, {})
        assert result.is_valid is True


# ---------------------------------------------------------------------------
# validate_no_work_when_absent
# ---------------------------------------------------------------------------

class TestValidateNoWorkWhenAbsent:
    def test_no_absence_overlap_is_valid(self):
        result = ValidationResult()
        emp = _make_emp()
        absence = Absence(id=1, employee_id=1, absence_type=AbsenceType.U,
                          start_date=date(2025, 1, 13), end_date=date(2025, 1, 17))
        assignment = _make_assign(1, 1, F_ID, date(2025, 1, 6))
        validate_no_work_when_absent(result, [assignment], [absence], {1: emp})
        assert result.is_valid is True

    def test_assignment_during_absence_adds_violation(self):
        result = ValidationResult()
        emp = _make_emp()
        absence = Absence(id=1, employee_id=1, absence_type=AbsenceType.U,
                          start_date=date(2025, 1, 6), end_date=date(2025, 1, 10))
        assignment = _make_assign(1, 1, F_ID, date(2025, 1, 8))
        validate_no_work_when_absent(result, [assignment], [absence], {1: emp})
        assert result.is_valid is False
        assert len(result.violations) == 1

    def test_assignment_on_absence_start_adds_violation(self):
        result = ValidationResult()
        emp = _make_emp()
        d = date(2025, 1, 6)
        absence = Absence(id=1, employee_id=1, absence_type=AbsenceType.AU,
                          start_date=d, end_date=d)
        assignment = _make_assign(1, 1, F_ID, d)
        validate_no_work_when_absent(result, [assignment], [absence], {1: emp})
        assert result.is_valid is False

    def test_different_employee_absence_not_violated(self):
        result = ValidationResult()
        emp1 = _make_emp(id=1)
        emp2 = _make_emp(id=2, name="C")
        absence = Absence(id=1, employee_id=2, absence_type=AbsenceType.U,
                          start_date=date(2025, 1, 6), end_date=date(2025, 1, 10))
        assignment = _make_assign(1, 1, F_ID, date(2025, 1, 8))
        validate_no_work_when_absent(result, [assignment], [absence],
                                     {1: emp1, 2: emp2})
        assert result.is_valid is True

    def test_empty_assignments_is_valid(self):
        result = ValidationResult()
        validate_no_work_when_absent(result, [], [], {})
        assert result.is_valid is True


# ---------------------------------------------------------------------------
# validate_rest_times
# ---------------------------------------------------------------------------

class TestValidateRestTimes:
    def _run(self, assignments, employees, absences=None):
        result = ValidationResult()
        emp_dict = {e.id: e for e in employees}
        validate_rest_times(result, assignments, emp_dict, absences or [], employees)
        return result

    def test_spaet_to_frueh_violation(self):
        """S ends 21:45, F next day starts 05:45 = only 8h rest < 11h."""
        emp = _make_emp()
        assignments = [
            _make_assign(1, 1, S_ID, date(2025, 1, 6)),
            _make_assign(2, 1, F_ID, date(2025, 1, 7)),
        ]
        result = self._run(assignments, [emp])
        assert result.is_valid is False
        assert any("Spät" in v.message or "S" in v.message for v in result.violations)

    def test_nacht_to_frueh_violation(self):
        """N ends 05:45, F next day starts 05:45 = 0h rest."""
        emp = _make_emp()
        assignments = [
            _make_assign(1, 1, N_ID, date(2025, 1, 6)),
            _make_assign(2, 1, F_ID, date(2025, 1, 7)),
        ]
        result = self._run(assignments, [emp])
        assert result.is_valid is False
        assert any("Nacht" in v.message or "N" in v.message for v in result.violations)

    def test_frueh_to_spaet_is_valid(self):
        """F ends 13:45, S next day starts 13:45 = 24h rest > 11h."""
        emp = _make_emp()
        assignments = [
            _make_assign(1, 1, F_ID, date(2025, 1, 6)),
            _make_assign(2, 1, S_ID, date(2025, 1, 7)),
        ]
        result = self._run(assignments, [emp])
        assert result.is_valid is True

    def test_nacht_to_spaet_violation(self):
        """N ends 05:45 next day, S next day starts 13:45 = only 8h rest < 11h."""
        emp = _make_emp()
        assignments = [
            _make_assign(1, 1, N_ID, date(2025, 1, 6)),
            _make_assign(2, 1, S_ID, date(2025, 1, 7)),
        ]
        result = self._run(assignments, [emp])
        assert result.is_valid is False
        assert any("Nacht" in v.message or "N" in v.message for v in result.violations)

    def test_spaet_to_spaet_is_valid(self):
        emp = _make_emp()
        assignments = [
            _make_assign(1, 1, S_ID, date(2025, 1, 6)),
            _make_assign(2, 1, S_ID, date(2025, 1, 7)),
        ]
        result = self._run(assignments, [emp])
        assert result.is_valid is True

    def test_empty_assignments_is_valid(self):
        result = self._run([], [])
        assert result.is_valid is True


# ---------------------------------------------------------------------------
# validate_staffing_requirements
# ---------------------------------------------------------------------------

class TestValidateStaffingRequirements:
    def _run(self, assignments, employees, absences=None):
        result = ValidationResult()
        emp_dict = {e.id: e for e in employees}
        by_date = _group_by_date(assignments)
        validate_staffing_requirements(
            result, by_date, emp_dict,
            list(STANDARD_SHIFT_TYPES), absences or [], employees
        )
        return result

    def test_no_staffing_raises_without_shift_types(self):
        result = ValidationResult()
        with pytest.raises(ValueError):
            validate_staffing_requirements(result, {}, {}, None, [], [])

    def test_understaffed_f_shift_on_weekday(self):
        """F requires min 4 on weekday; 0 assigned = violation."""
        # Monday 2025-01-06 with no F-shift workers
        d = date(2025, 1, 6)  # Monday
        employees = [_make_emp(id=i, team_id=1) for i in range(1, 5)]
        assignments = [_make_assign(i, i, S_ID, d) for i in range(1, 5)]
        result = self._run(assignments, employees)
        # F is understaffed (0 < 4 minimum)
        assert result.is_valid is False
        f_violations = [v for v in result.violations if "F" in v.message]
        assert len(f_violations) >= 1

    def test_adequate_staffing_no_violation(self):
        """Each shift gets exactly min_staff workers -> no violation for those shifts."""
        d = date(2025, 1, 6)  # Monday; F min=4, S min=3, N min=3
        employees = [_make_emp(id=i, team_id=1) for i in range(1, 11)]
        assignments = (
            [_make_assign(i, i, F_ID, d) for i in range(1, 5)] +    # 4 F workers
            [_make_assign(i, i, S_ID, d) for i in range(5, 8)] +    # 3 S workers
            [_make_assign(i, i, N_ID, d) for i in range(8, 11)]     # 3 N workers
        )
        result = self._run(assignments, employees)
        assert result.is_valid is True


# ---------------------------------------------------------------------------
# validate_shift_plan (integration)
# ---------------------------------------------------------------------------

class TestValidateShiftPlan:
    def test_empty_plan_is_valid(self):
        """Empty assignments with no employees passes all checks."""
        result = validate_shift_plan(
            assignments=[],
            employees=[],
            absences=[],
            start_date=date(2025, 1, 6),
            end_date=date(2025, 1, 12),
            shift_types=list(STANDARD_SHIFT_TYPES),
        )
        assert isinstance(result, ValidationResult)
        assert result.is_valid is True

    def test_duplicate_shift_detected_by_full_validation(self):
        emp = _make_emp()
        d = date(2025, 1, 6)
        assignments = [
            _make_assign(1, 1, F_ID, d),
            _make_assign(2, 1, S_ID, d),
        ]
        result = validate_shift_plan(
            assignments=assignments,
            employees=[emp],
            absences=[],
            start_date=d,
            end_date=d,
            shift_types=list(STANDARD_SHIFT_TYPES),
        )
        assert result.is_valid is False

    def test_work_during_absence_detected(self):
        emp = _make_emp()
        d = date(2025, 1, 8)
        absence = Absence(id=1, employee_id=1, absence_type=AbsenceType.U,
                          start_date=date(2025, 1, 6), end_date=date(2025, 1, 10))
        assignment = _make_assign(1, 1, F_ID, d)
        result = validate_shift_plan(
            assignments=[assignment],
            employees=[emp],
            absences=[absence],
            start_date=date(2025, 1, 6),
            end_date=date(2025, 1, 10),
            shift_types=list(STANDARD_SHIFT_TYPES),
        )
        assert result.is_valid is False

    def test_forbidden_spaet_frueh_transition_detected(self):
        emp = _make_emp()
        assignments = [
            _make_assign(1, 1, S_ID, date(2025, 1, 6)),
            _make_assign(2, 1, F_ID, date(2025, 1, 7)),
        ]
        result = validate_shift_plan(
            assignments=assignments,
            employees=[emp],
            absences=[],
            start_date=date(2025, 1, 6),
            end_date=date(2025, 1, 7),
            shift_types=list(STANDARD_SHIFT_TYPES),
        )
        assert result.is_valid is False

    def test_valid_plan_returns_valid_result(self):
        """Single employee, single F-shift, no absences – should pass hard checks."""
        emp = _make_emp()
        d = date(2025, 1, 6)
        assignment = _make_assign(1, 1, F_ID, d)
        result = validate_shift_plan(
            assignments=[assignment],
            employees=[emp],
            absences=[],
            start_date=d,
            end_date=d,
            shift_types=list(STANDARD_SHIFT_TYPES),
        )
        # No duplicate / absence / rest-time violations for a single day
        dup_violations = [v for v in result.violations
                          if "mehrfachzuweisung" in v.message.lower() or "mehrere schichten" in v.message.lower()]
        absence_violations = [v for v in result.violations
                               if "abwesend" in v.message.lower()]
        rest_violations = [v for v in result.violations
                           if "unzulässiger schichtwechsel" in v.message.lower()]
        assert len(dup_violations) == 0
        assert len(absence_violations) == 0
        assert len(rest_violations) == 0

    def test_returns_validation_result_instance(self):
        result = validate_shift_plan(
            assignments=[],
            employees=[],
            absences=[],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            shift_types=list(STANDARD_SHIFT_TYPES),
        )
        assert isinstance(result, ValidationResult)
        assert hasattr(result, 'is_valid')
        assert hasattr(result, 'violations')
        assert hasattr(result, 'warnings')
