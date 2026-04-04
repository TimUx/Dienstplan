"""Employee Repository: encapsulates all SQL queries for employees, teams, and related entities."""

from typing import Optional, List, Dict, Any


class EmployeeRepository:
    """Data access layer for employee-related entities."""

    @staticmethod
    def get_all_employees(cursor) -> List[Dict[str, Any]]:
        cursor.execute("""
            SELECT e.*, t.Name as TeamName,
                   GROUP_CONCAT(r.Name) as roles
            FROM Employees e
            LEFT JOIN Teams t ON e.TeamId = t.Id
            LEFT JOIN AspNetUserRoles ur ON CAST(e.Id AS TEXT) = ur.UserId
            LEFT JOIN AspNetRoles r ON ur.RoleId = r.Id
            GROUP BY e.Id
            ORDER BY e.Name, e.Vorname
        """)
        return cursor.fetchall()

    @staticmethod
    def get_employee_by_id(cursor, employee_id: int):
        cursor.execute("""
            SELECT e.*, t.Name as TeamName
            FROM Employees e
            LEFT JOIN Teams t ON e.TeamId = t.Id
            WHERE e.Id = ?
        """, (employee_id,))
        return cursor.fetchone()

    @staticmethod
    def get_all_teams(cursor) -> List[Dict[str, Any]]:
        cursor.execute("SELECT * FROM Teams ORDER BY Name")
        return cursor.fetchall()

    @staticmethod
    def get_team_by_id(cursor, team_id: int):
        cursor.execute("SELECT * FROM Teams WHERE Id = ?", (team_id,))
        return cursor.fetchone()

    @staticmethod
    def get_employees_by_team(cursor, team_id: int) -> List[Dict[str, Any]]:
        cursor.execute("""
            SELECT * FROM Employees WHERE TeamId = ? ORDER BY Name, Vorname
        """, (team_id,))
        return cursor.fetchall()
