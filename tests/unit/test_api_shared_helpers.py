"""Unit tests for small helpers in api.shared."""

from datetime import date

import pytest

from api.shared import _paginate, extend_planning_dates_to_complete_weeks, get_row_value


@pytest.mark.unit
class TestExtendPlanningDatesToCompleteWeeks:
    def test_january_2026_month_extends_to_sunday_saturday(self):
        start = date(2026, 1, 1)
        end = date(2026, 1, 31)
        ext_start, ext_end = extend_planning_dates_to_complete_weeks(start, end)
        assert ext_start.weekday() == 6  # Sunday
        assert ext_end.weekday() == 5  # Saturday
        assert ext_start <= start
        assert ext_end >= end

    def test_already_full_week_unchanged(self):
        sun = date(2025, 1, 5)
        sat = date(2025, 1, 11)
        ext_start, ext_end = extend_planning_dates_to_complete_weeks(sun, sat)
        assert ext_start == sun
        assert ext_end == sat


@pytest.mark.unit
class TestPaginate:
    def test_first_page(self):
        items = list(range(10))
        out = _paginate(items, page=1, limit=4)
        assert out["data"] == [0, 1, 2, 3]
        assert out["total"] == 10
        assert out["page"] == 1
        assert out["totalPages"] == 3

    def test_limit_zero_returns_all(self):
        items = [1, 2, 3]
        out = _paginate(items, page=1, limit=0)
        assert out["data"] == items
        assert out["totalPages"] == 1


@pytest.mark.unit
class TestGetRowValue:
    def test_missing_key_returns_default(self):
        import sqlite3

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT 1 AS a")
        row = cur.fetchone()
        assert get_row_value(row, "missing", "x") == "x"
        conn.close()
