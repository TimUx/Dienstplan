"""Shift Repository: encapsulates SQL queries for shift types and assignments."""

from typing import List, Dict, Any


class ShiftRepository:
    """Data access layer for shift types and assignments."""

    @staticmethod
    def get_all_shift_types(cursor) -> List[Dict[str, Any]]:
        """Return all shift types ordered by Id."""
        cursor.execute("SELECT * FROM ShiftTypes ORDER BY Id")
        return cursor.fetchall()

    @staticmethod
    def get_shift_type_by_id(cursor, shift_type_id: int) -> Optional[Dict[str, Any]]:
        """Return a single shift type by primary key, or None if not found."""
        cursor.execute("SELECT * FROM ShiftTypes WHERE Id = ?", (shift_type_id,))
        return cursor.fetchone()

    @staticmethod
    def get_assignments_by_date_range(cursor, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Return shift assignments (with employee, shift type, and team details) within an inclusive date range.

        Args:
            start_date: ISO-8601 date string (YYYY-MM-DD) for the range start.
            end_date: ISO-8601 date string (YYYY-MM-DD) for the range end.
        """
        cursor.execute("""
            SELECT sa.*, e.Vorname, e.Name as EmployeeName, e.TeamId,
                   st.Code as ShiftCode, st.ColorCode, st.Name as ShiftName,
                   st.StartTime, st.EndTime, st.DurationHours,
                   t.Name as TeamName
            FROM ShiftAssignments sa
            INNER JOIN Employees e ON sa.EmployeeId = e.Id
            INNER JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
            LEFT JOIN Teams t ON e.TeamId = t.Id
            WHERE sa.Date >= ? AND sa.Date <= ?
            ORDER BY sa.Date, t.Name, e.Name, e.Vorname
        """, (start_date, end_date))
        return cursor.fetchall()

    @staticmethod
    def get_assignment_by_id(cursor, assignment_id: int) -> Optional[Dict[str, Any]]:
        """Return a single shift assignment (with shift code) by primary key, or None if not found."""
        cursor.execute("""
            SELECT sa.*, st.Code as ShiftCode
            FROM ShiftAssignments sa
            INNER JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
            WHERE sa.Id = ?
        """, (assignment_id,))
        return cursor.fetchone()

    @staticmethod
    def get_teams_for_shift_type(cursor, shift_type_id: int) -> List[Dict[str, Any]]:
        """Return all teams associated with the given shift type, ordered by name."""
        cursor.execute("""
            SELECT t.* FROM Teams t
            INNER JOIN TeamShiftTypes tst ON t.Id = tst.TeamId
            WHERE tst.ShiftTypeId = ?
            ORDER BY t.Name
        """, (shift_type_id,))
        return cursor.fetchall()
