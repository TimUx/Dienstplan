"""Unit tests for entity data models."""

import pytest
from datetime import date, time


from entities import (
    Employee, Team, Absence, AbsenceType, ShiftType, ShiftAssignment,
    STANDARD_SHIFT_TYPES,
    get_shift_type_by_code, get_shift_type_by_id,
)


# ---------------------------------------------------------------------------
# Employee tests
# ---------------------------------------------------------------------------

class TestEmployeeFullName:
    def test_full_name_combines_vorname_and_name(self):
        emp = Employee(id=1, vorname="Anna", name="Müller", personalnummer="P001")
        assert emp.full_name == "Anna Müller"

    def test_full_name_with_empty_vorname(self):
        emp = Employee(id=2, vorname="", name="Schmidt", personalnummer="P002")
        assert emp.full_name == " Schmidt"

    def test_full_name_with_single_names(self):
        emp = Employee(id=3, vorname="Ö", name="Ü", personalnummer="P003")
        assert emp.full_name == "Ö Ü"


class TestEmployeeCanDoTd:
    def test_td_qualified_employee_can_do_td(self):
        emp = Employee(id=1, vorname="A", name="B", personalnummer="P001",
                       is_td_qualified=True)
        assert emp.can_do_td is True

    def test_brandmeldetechniker_can_do_td(self):
        emp = Employee(id=2, vorname="A", name="B", personalnummer="P002",
                       is_brandmeldetechniker=True)
        assert emp.can_do_td is True

    def test_brandschutzbeauftragter_can_do_td(self):
        emp = Employee(id=3, vorname="A", name="B", personalnummer="P003",
                       is_brandschutzbeauftragter=True)
        assert emp.can_do_td is True

    def test_regular_employee_cannot_do_td(self):
        emp = Employee(id=4, vorname="A", name="B", personalnummer="P004")
        assert emp.can_do_td is False

    def test_multiple_qualifications_can_do_td(self):
        emp = Employee(id=5, vorname="A", name="B", personalnummer="P005",
                       is_td_qualified=True, is_brandmeldetechniker=True)
        assert emp.can_do_td is True


# ---------------------------------------------------------------------------
# ShiftType tests
# ---------------------------------------------------------------------------

class TestShiftTypeWorksOnDate:
    def test_frueh_works_on_monday(self):
        f_shift = get_shift_type_by_code("F")
        assert f_shift.works_on_date(date(2025, 1, 6)) is True  # Monday

    def test_frueh_works_on_saturday(self):
        f_shift = get_shift_type_by_code("F")
        assert f_shift.works_on_date(date(2025, 1, 11)) is True  # Saturday

    def test_frueh_works_on_sunday(self):
        f_shift = get_shift_type_by_code("F")
        assert f_shift.works_on_date(date(2025, 1, 12)) is True  # Sunday

    def test_bmt_does_not_work_on_saturday(self):
        bmt = get_shift_type_by_code("BMT")
        assert bmt.works_on_date(date(2025, 1, 11)) is False  # Saturday

    def test_bmt_does_not_work_on_sunday(self):
        bmt = get_shift_type_by_code("BMT")
        assert bmt.works_on_date(date(2025, 1, 12)) is False  # Sunday

    def test_bmt_works_on_friday(self):
        bmt = get_shift_type_by_code("BMT")
        assert bmt.works_on_date(date(2025, 1, 10)) is True  # Friday

    def test_bsb_does_not_work_on_weekend(self):
        bsb = get_shift_type_by_code("BSB")
        assert bsb.works_on_date(date(2025, 1, 11)) is False
        assert bsb.works_on_date(date(2025, 1, 12)) is False

    def test_zd_does_not_work_on_weekend(self):
        zd = get_shift_type_by_code("ZD")
        assert zd.works_on_date(date(2025, 1, 11)) is False
        assert zd.works_on_date(date(2025, 1, 12)) is False


class TestShiftTypeDurationHours:
    def test_frueh_duration(self):
        f_shift = get_shift_type_by_code("F")
        # 05:45 -> 13:45 = 8h
        assert f_shift.get_duration_hours() == pytest.approx(8.0)

    def test_spaet_duration(self):
        s_shift = get_shift_type_by_code("S")
        # 13:45 -> 21:45 = 8h
        assert s_shift.get_duration_hours() == pytest.approx(8.0)

    def test_nacht_overnight_duration(self):
        n_shift = get_shift_type_by_code("N")
        # 21:45 -> 05:45 = 8h (crosses midnight)
        assert n_shift.get_duration_hours() == pytest.approx(8.0)

    def test_bsb_duration(self):
        bsb = get_shift_type_by_code("BSB")
        # 07:00 -> 16:30 = 9.5h
        assert bsb.get_duration_hours() == pytest.approx(9.5)

    def test_bmt_duration(self):
        bmt = get_shift_type_by_code("BMT")
        # 06:00 -> 14:00 = 8h
        assert bmt.get_duration_hours() == pytest.approx(8.0)

    def test_nacht_end_time_less_than_start(self):
        # Ensure overnight calculation doesn't give negative hours
        n_shift = get_shift_type_by_code("N")
        assert n_shift.get_duration_hours() > 0


# ---------------------------------------------------------------------------
# Absence tests
# ---------------------------------------------------------------------------

class TestAbsenceOverlapsDate:
    def setup_method(self):
        self.absence = Absence(
            id=1,
            employee_id=1,
            absence_type=AbsenceType.U,
            start_date=date(2025, 1, 6),
            end_date=date(2025, 1, 10),
        )

    def test_date_within_absence(self):
        assert self.absence.overlaps_date(date(2025, 1, 8)) is True

    def test_start_date_overlaps(self):
        assert self.absence.overlaps_date(date(2025, 1, 6)) is True

    def test_end_date_overlaps(self):
        assert self.absence.overlaps_date(date(2025, 1, 10)) is True

    def test_before_absence_does_not_overlap(self):
        assert self.absence.overlaps_date(date(2025, 1, 5)) is False

    def test_after_absence_does_not_overlap(self):
        assert self.absence.overlaps_date(date(2025, 1, 11)) is False


class TestAbsenceGetCode:
    def test_urlaub_code(self):
        absence = Absence(id=1, employee_id=1, absence_type=AbsenceType.U,
                          start_date=date(2025, 1, 6), end_date=date(2025, 1, 10))
        assert absence.get_code() == "U"

    def test_au_code(self):
        absence = Absence(id=2, employee_id=1, absence_type=AbsenceType.AU,
                          start_date=date(2025, 1, 6), end_date=date(2025, 1, 7))
        assert absence.get_code() == "AU"

    def test_lehrgang_code(self):
        absence = Absence(id=3, employee_id=1, absence_type=AbsenceType.L,
                          start_date=date(2025, 1, 6), end_date=date(2025, 1, 8))
        assert absence.get_code() == "L"


class TestAbsenceGetName:
    def test_urlaub_name(self):
        absence = Absence(id=1, employee_id=1, absence_type=AbsenceType.U,
                          start_date=date(2025, 1, 6), end_date=date(2025, 1, 10))
        assert "Urlaub" in absence.get_name()

    def test_au_name(self):
        absence = Absence(id=2, employee_id=1, absence_type=AbsenceType.AU,
                          start_date=date(2025, 1, 6), end_date=date(2025, 1, 7))
        name = absence.get_name()
        assert "Krank" in name or "AU" in name

    def test_lehrgang_name(self):
        absence = Absence(id=3, employee_id=1, absence_type=AbsenceType.L,
                          start_date=date(2025, 1, 6), end_date=date(2025, 1, 8))
        assert "Lehrgang" in absence.get_name()


# ---------------------------------------------------------------------------
# AbsenceType enum tests
# ---------------------------------------------------------------------------

class TestAbsenceTypeEnum:
    def test_au_value(self):
        assert AbsenceType.AU.value == "AU"

    def test_u_value(self):
        assert AbsenceType.U.value == "U"

    def test_l_value(self):
        assert AbsenceType.L.value == "L"

    def test_enum_has_three_members(self):
        assert len(AbsenceType) == 3

    def test_v_not_in_enum(self):
        values = [e.value for e in AbsenceType]
        assert "V" not in values

    def test_k_not_in_enum(self):
        values = [e.value for e in AbsenceType]
        assert "K" not in values


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestGetShiftTypeByCode:
    def test_get_frueh(self):
        st = get_shift_type_by_code("F")
        assert st is not None
        assert st.code == "F"

    def test_get_nacht(self):
        st = get_shift_type_by_code("N")
        assert st is not None
        assert st.start_time == "21:45"

    def test_get_unknown_returns_none(self):
        assert get_shift_type_by_code("INVALID") is None

    def test_case_sensitive(self):
        assert get_shift_type_by_code("f") is None


class TestGetShiftTypeById:
    def test_get_by_id_1(self):
        st = get_shift_type_by_id(1)
        assert st is not None
        assert st.id == 1

    def test_get_by_id_returns_none_for_unknown(self):
        assert get_shift_type_by_id(9999) is None


# ---------------------------------------------------------------------------
# STANDARD_SHIFT_TYPES tests
# ---------------------------------------------------------------------------

class TestStandardShiftTypes:
    def test_has_six_shift_types(self):
        assert len(STANDARD_SHIFT_TYPES) == 6

    def test_contains_expected_codes(self):
        codes = {st.code for st in STANDARD_SHIFT_TYPES}
        assert codes == {"F", "S", "N", "ZD", "BMT", "BSB"}

    def test_all_have_unique_ids(self):
        ids = [st.id for st in STANDARD_SHIFT_TYPES]
        assert len(ids) == len(set(ids))

    def test_all_have_valid_times(self):
        for st in STANDARD_SHIFT_TYPES:
            parts_start = st.start_time.split(":")
            parts_end = st.end_time.split(":")
            assert len(parts_start) == 2
            assert len(parts_end) == 2

    def test_nacht_is_overnight(self):
        n = get_shift_type_by_code("N")
        start_h = int(n.start_time.split(":")[0])
        end_h = int(n.end_time.split(":")[0])
        assert end_h < start_h  # end_time < start_time implies overnight
