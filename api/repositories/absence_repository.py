"""Absence Repository: encapsulates SQL queries for absences and vacation requests."""

from typing import Optional, List, Dict, Any


class AbsenceRepository:
    """Data access layer for absences, vacation requests, and shift exchanges."""

    @staticmethod
    def get_absences_by_date_range(cursor, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Return absences (with employee, team, and absence-type details) overlapping the given date range.

        Args:
            start_date: ISO-8601 date string (YYYY-MM-DD) for the range start.
            end_date: ISO-8601 date string (YYYY-MM-DD) for the range end.
        """
        cursor.execute("""
            SELECT a.*, e.Vorname, e.Name as EmployeeName, e.TeamId,
                   t.Name as TeamName,
                   at.Name as AbsenceTypeName, at.Code as AbsenceTypeCode,
                   at.ColorCode as AbsenceTypeColor
            FROM Absences a
            INNER JOIN Employees e ON a.EmployeeId = e.Id
            LEFT JOIN Teams t ON e.TeamId = t.Id
            LEFT JOIN AbsenceTypes at ON a.AbsenceTypeId = at.Id
            WHERE a.StartDate <= ? AND a.EndDate >= ?
            ORDER BY a.StartDate, e.Name, e.Vorname
        """, (end_date, start_date))
        return cursor.fetchall()

    @staticmethod
    def get_absence_by_id(cursor, absence_id: int) -> Optional[Dict[str, Any]]:
        """Return a single absence (with employee name) by primary key, or None if not found."""
        cursor.execute("""
            SELECT a.*, e.Vorname, e.Name as EmployeeName
            FROM Absences a
            INNER JOIN Employees e ON a.EmployeeId = e.Id
            WHERE a.Id = ?
        """, (absence_id,))
        return cursor.fetchone()

    @staticmethod
    def get_vacation_requests(cursor, status_filter: Optional[str] = None, employee_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Return vacation requests with employee and team details, optionally filtered by status and/or employee.

        Args:
            status_filter: If provided and not 'all', only requests with this Status value are returned.
            employee_id: If provided, only requests for this employee are returned.
        """
        query = """
            SELECT vr.*, e.Vorname, e.Name as EmployeeName, e.TeamId,
                   t.Name as TeamName
            FROM VacationRequests vr
            INNER JOIN Employees e ON vr.EmployeeId = e.Id
            LEFT JOIN Teams t ON e.TeamId = t.Id
            WHERE 1=1
        """
        params = []
        if status_filter and status_filter != 'all':
            query += " AND vr.Status = ?"
            params.append(status_filter)
        if employee_id is not None:
            query += " AND vr.EmployeeId = ?"
            params.append(employee_id)
        query += " ORDER BY vr.StartDate DESC"
        cursor.execute(query, params)
        return cursor.fetchall()

    @staticmethod
    def get_all_absence_types(cursor) -> List[Dict[str, Any]]:
        """Return all absence types ordered alphabetically by name."""
        cursor.execute("SELECT * FROM AbsenceTypes ORDER BY Name")
        return cursor.fetchall()
