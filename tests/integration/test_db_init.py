"""Integration tests for database initialization."""

import pytest
import sqlite3
import os


from db_init import initialize_database, create_database_schema
from entities import STANDARD_SHIFT_TYPES

REQUIRED_TABLES = [
    "Teams",
    "Employees",
    "ShiftTypes",
    "Absences",
    "ShiftAssignments",
]

ADMIN_EMAIL = "admin@fritzwinter.de"


def _get_tables(db_path):
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    return {row[0] for row in rows}


def _query(db_path, sql, params=()):
    with sqlite3.connect(db_path) as conn:
        return conn.execute(sql, params).fetchall()


# ---------------------------------------------------------------------------
# Schema creation
# ---------------------------------------------------------------------------

class TestCreateDatabaseSchema:
    def test_creates_required_tables(self, tmp_path):
        db_path = str(tmp_path / "schema_test.db")
        create_database_schema(db_path)
        tables = _get_tables(db_path)
        for table in REQUIRED_TABLES:
            assert table in tables, f"Table '{table}' not found after schema creation"

    def test_creates_db_file(self, tmp_path):
        db_path = str(tmp_path / "new.db")
        assert not os.path.exists(db_path)
        create_database_schema(db_path)
        assert os.path.exists(db_path)

    def test_schema_is_idempotent(self, tmp_path):
        db_path = str(tmp_path / "idempotent.db")
        create_database_schema(db_path)
        create_database_schema(db_path)  # Should not raise
        tables = _get_tables(db_path)
        for table in REQUIRED_TABLES:
            assert table in tables


# ---------------------------------------------------------------------------
# Full initialization without sample data
# ---------------------------------------------------------------------------

class TestInitializeDatabaseEmpty:
    def test_empty_db_has_required_tables(self, tmp_path):
        db_path = str(tmp_path / "empty.db")
        initialize_database(db_path, with_sample_data=False)
        tables = _get_tables(db_path)
        for table in REQUIRED_TABLES:
            assert table in tables

    def test_admin_user_exists_after_empty_init(self, tmp_path):
        db_path = str(tmp_path / "empty_admin.db")
        initialize_database(db_path, with_sample_data=False)
        rows = _query(db_path, "SELECT Email FROM Employees WHERE Email = ?", (ADMIN_EMAIL,))
        assert len(rows) == 1, "Default admin not found in Employees table"

    def test_shift_types_seeded(self, tmp_path):
        db_path = str(tmp_path / "empty_shifts.db")
        initialize_database(db_path, with_sample_data=False)
        rows = _query(db_path, "SELECT Code FROM ShiftTypes")
        db_codes = {row[0] for row in rows}
        # DB init seeds only the three main shifts: F, N, S
        for code in ("F", "N", "S"):
            assert code in db_codes, f"Shift type code '{code}' not in DB after init"

    def test_no_employees_without_sample_data(self, tmp_path):
        db_path = str(tmp_path / "no_sample.db")
        initialize_database(db_path, with_sample_data=False)
        # Only the admin should exist
        rows = _query(db_path, "SELECT Email FROM Employees WHERE Email != ?", (ADMIN_EMAIL,))
        assert len(rows) == 0

    def test_no_teams_without_sample_data(self, tmp_path):
        db_path = str(tmp_path / "no_teams.db")
        initialize_database(db_path, with_sample_data=False)
        rows = _query(db_path, "SELECT Id FROM Teams")
        assert len(rows) == 0


# ---------------------------------------------------------------------------
# Full initialization with sample data
# ---------------------------------------------------------------------------

class TestInitializeDatabaseWithSampleData:
    def test_teams_created_with_sample_data(self, tmp_path):
        db_path = str(tmp_path / "sample.db")
        initialize_database(db_path, with_sample_data=True)
        rows = _query(db_path, "SELECT Id FROM Teams")
        assert len(rows) >= 3, f"Expected at least 3 teams, found {len(rows)}"

    def test_employees_created_with_sample_data(self, tmp_path):
        db_path = str(tmp_path / "sample_emp.db")
        initialize_database(db_path, with_sample_data=True)
        rows = _query(db_path, "SELECT Id FROM Employees WHERE Email != ?", (ADMIN_EMAIL,))
        assert len(rows) > 0, "No sample employees found"

    def test_admin_user_exists_with_sample_data(self, tmp_path):
        db_path = str(tmp_path / "sample_admin.db")
        initialize_database(db_path, with_sample_data=True)
        rows = _query(db_path, "SELECT Email FROM Employees WHERE Email = ?", (ADMIN_EMAIL,))
        assert len(rows) == 1

    def test_all_required_tables_present(self, tmp_path):
        db_path = str(tmp_path / "full.db")
        initialize_database(db_path, with_sample_data=True)
        tables = _get_tables(db_path)
        for table in REQUIRED_TABLES:
            assert table in tables


# ---------------------------------------------------------------------------
# Idempotency – calling initialize_database twice
# ---------------------------------------------------------------------------

class TestInitializeDatabaseIdempotency:
    def test_second_call_does_not_raise(self, tmp_path):
        db_path = str(tmp_path / "idem.db")
        initialize_database(db_path, with_sample_data=True)
        # Second call should be a no-op (existing DB path)
        initialize_database(db_path, with_sample_data=True)

    def test_admin_still_present_after_second_call(self, tmp_path):
        db_path = str(tmp_path / "idem_admin.db")
        initialize_database(db_path, with_sample_data=True)
        initialize_database(db_path, with_sample_data=True)
        rows = _query(db_path, "SELECT Email FROM Employees WHERE Email = ?", (ADMIN_EMAIL,))
        assert len(rows) == 1, "Admin duplicated or removed after second init"

    def test_shift_types_not_duplicated(self, tmp_path):
        db_path = str(tmp_path / "idem_shifts.db")
        initialize_database(db_path, with_sample_data=True)
        rows_first = _query(db_path, "SELECT Code FROM ShiftTypes")
        initialize_database(db_path, with_sample_data=True)
        rows_second = _query(db_path, "SELECT Code FROM ShiftTypes")
        # Row count should not change after second call
        assert len(rows_first) == len(rows_second)
