"""Dashboard statistics: DB queries and aggregation (no HTTP layer)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from .statistics_constants import DEFAULT_WEEKLY_HOURS_FALLBACK, MAX_ABSENCE_DAYS_PER_WEEK


def default_month_date_range() -> tuple[date, date]:
    """First and last day of the current calendar month."""
    today = date.today()
    start = date(today.year, today.month, 1)
    if today.month == 12:
        end = date(today.year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(today.year, today.month + 1, 1) - timedelta(days=1)
    return start, end


def build_dashboard_payload(cursor, start_date: date, end_date: date) -> dict[str, Any]:
    """
    Build the JSON-serializable dict for GET /api/statistics/dashboard.

    Caller owns the DB connection and cursor lifecycle.
    """
    cursor.execute(
        """
        SELECT e.Id, e.Vorname, e.Name, e.TeamId,
               COUNT(sa.Id) as ShiftCount,
               COALESCE(SUM(st.DurationHours), 0) as ShiftHours
        FROM Employees e
        LEFT JOIN ShiftAssignments sa ON e.Id = sa.EmployeeId
            AND sa.Date >= ? AND sa.Date <= ?
        LEFT JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
        GROUP BY e.Id, e.Vorname, e.Name, e.TeamId
    """,
        (start_date.isoformat(), end_date.isoformat()),
    )

    employee_hours_map: dict[int, dict[str, Any]] = {}
    for row in cursor.fetchall():
        employee_hours_map[row["Id"]] = {
            "id": row["Id"],
            "name": f"{row['Vorname']} {row['Name']}",
            "teamId": row["TeamId"],
            "shiftCount": row["ShiftCount"],
            "shiftHours": float(row["ShiftHours"] or 0),
            "absenceHours": 0.0,
            "weeklyHours": 0.0,
        }

    cursor.execute(
        """
        SELECT e.Id,
               MAX(st.WeeklyWorkingHours) as WeeklyHours
        FROM Employees e
        LEFT JOIN ShiftAssignments sa ON e.Id = sa.EmployeeId
            AND sa.Date >= ? AND sa.Date <= ?
        LEFT JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
        GROUP BY e.Id
    """,
        (start_date.isoformat(), end_date.isoformat()),
    )
    assigned_weekly_hours = {row["Id"]: float(row["WeeklyHours"] or 0) for row in cursor.fetchall()}

    cursor.execute(
        """
        SELECT e.Id,
               MAX(st.WeeklyWorkingHours) as WeeklyHours
        FROM Employees e
        LEFT JOIN TeamShiftAssignments tsa ON e.TeamId = tsa.TeamId
        LEFT JOIN ShiftTypes st ON tsa.ShiftTypeId = st.Id
        GROUP BY e.Id
    """
    )
    team_weekly_hours = {row["Id"]: float(row["WeeklyHours"] or 0) for row in cursor.fetchall()}

    cursor.execute(
        """
        SELECT COALESCE(MAX(WeeklyWorkingHours), ?) as DefaultWeeklyHours
        FROM ShiftTypes
        WHERE IsActive = 1
    """,
        (DEFAULT_WEEKLY_HOURS_FALLBACK,),
    )
    weekly_hours_default = float(
        cursor.fetchone()["DefaultWeeklyHours"] or DEFAULT_WEEKLY_HOURS_FALLBACK
    )

    for emp_id, emp_data in employee_hours_map.items():
        weekly_hours = assigned_weekly_hours.get(emp_id, 0.0)
        if weekly_hours <= 0:
            weekly_hours = team_weekly_hours.get(emp_id, 0.0)
        if weekly_hours <= 0:
            weekly_hours = weekly_hours_default
        emp_data["weeklyHours"] = weekly_hours

    cursor.execute(
        """
        SELECT e.Id, e.Vorname, e.Name, a.Type, a.StartDate, a.EndDate,
               at.Code as TypeCode
        FROM Absences a
        JOIN Employees e ON e.Id = a.EmployeeId
        LEFT JOIN AbsenceTypes at ON a.AbsenceTypeId = at.Id
        WHERE (a.StartDate <= ? AND a.EndDate >= ?)
           OR (a.StartDate >= ? AND a.StartDate <= ?)
        ORDER BY e.Vorname, e.Name, a.StartDate
    """,
        (
            end_date.isoformat(),
            start_date.isoformat(),
            start_date.isoformat(),
            end_date.isoformat(),
        ),
    )

    type_id_to_code = {1: "AU", 2: "U", 3: "L"}
    employee_absence_sets: dict[int, dict[str, Any]] = {}
    employee_absence_credit_sets: dict[int, set] = {}

    for row in cursor.fetchall():
        emp_id = row["Id"]
        if emp_id not in employee_absence_sets:
            employee_absence_sets[emp_id] = {
                "employeeId": emp_id,
                "employeeName": f"{row['Vorname']} {row['Name']}",
                "allDays": set(),
                "byType": {},
            }
            employee_absence_credit_sets[emp_id] = set()

        absence_start = date.fromisoformat(row["StartDate"])
        absence_end = date.fromisoformat(row["EndDate"])
        overlap_start = max(absence_start, start_date)
        overlap_end = min(absence_end, end_date)
        if overlap_start > overlap_end:
            continue

        absence_type_code = row["TypeCode"] or type_id_to_code.get(row["Type"], str(row["Type"]))
        if absence_type_code not in employee_absence_sets[emp_id]["byType"]:
            employee_absence_sets[emp_id]["byType"][absence_type_code] = set()

        current_day = overlap_start
        while current_day <= overlap_end:
            employee_absence_sets[emp_id]["allDays"].add(current_day)
            employee_absence_sets[emp_id]["byType"][absence_type_code].add(current_day)
            if absence_type_code in {"AU", "U", "L"}:
                employee_absence_credit_sets[emp_id].add(current_day)
            current_day += timedelta(days=1)

    employee_absence_days = []
    for emp_absence in employee_absence_sets.values():
        by_type_counts = {
            code: len(day_set) for code, day_set in emp_absence["byType"].items() if day_set
        }
        total_days = len(emp_absence["allDays"])
        if total_days > 0:
            employee_absence_days.append(
                {
                    "employeeId": emp_absence["employeeId"],
                    "employeeName": emp_absence["employeeName"],
                    "totalDays": total_days,
                    "byType": by_type_counts,
                }
            )

    employee_absence_days.sort(key=lambda x: x["employeeName"])

    for emp_id, absence_days in employee_absence_credit_sets.items():
        if not absence_days:
            continue
        if emp_id not in employee_hours_map:
            employee_name = employee_absence_sets.get(emp_id, {}).get(
                "employeeName", f"Mitarbeiter {emp_id}"
            )
            employee_hours_map[emp_id] = {
                "id": emp_id,
                "name": employee_name,
                "teamId": None,
                "shiftCount": 0,
                "shiftHours": 0.0,
                "absenceHours": 0.0,
                "weeklyHours": weekly_hours_default,
            }

        weekly_day_count: dict[date, int] = {}
        for d in absence_days:
            week_start = d - timedelta(days=d.weekday())
            weekly_day_count[week_start] = weekly_day_count.get(week_start, 0) + 1

        credited_days = sum(
            min(days_in_week, MAX_ABSENCE_DAYS_PER_WEEK)
            for days_in_week in weekly_day_count.values()
        )
        weekly_hours = employee_hours_map[emp_id]["weeklyHours"]
        daily_hours = (weekly_hours / MAX_ABSENCE_DAYS_PER_WEEK) if weekly_hours > 0 else 0.0
        employee_hours_map[emp_id]["absenceHours"] = credited_days * daily_hours

    employee_work_hours = []
    for emp_data in employee_hours_map.values():
        total_hours = emp_data["shiftHours"] + emp_data["absenceHours"]
        if total_hours > 0:
            employee_work_hours.append(
                {
                    "employeeId": emp_data["id"],
                    "employeeName": emp_data["name"],
                    "teamId": emp_data["teamId"],
                    "shiftCount": emp_data["shiftCount"],
                    "totalHours": total_hours,
                }
            )

    employee_work_hours.sort(key=lambda x: x["employeeName"])

    cursor.execute(
        """
        SELECT t.Id, t.Name,
               st.Code,
               COUNT(sa.Id) as ShiftCount
        FROM Teams t
        LEFT JOIN Employees e ON t.Id = e.TeamId
        LEFT JOIN ShiftAssignments sa ON e.Id = sa.EmployeeId
            AND sa.Date >= ? AND sa.Date <= ?
        LEFT JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
        WHERE st.Code IS NOT NULL
        GROUP BY t.Id, t.Name, st.Code
        ORDER BY t.Name, st.Code
    """,
        (start_date.isoformat(), end_date.isoformat()),
    )

    team_shift_data: dict[int, dict[str, Any]] = {}
    for row in cursor.fetchall():
        team_id = row["Id"]
        if team_id not in team_shift_data:
            team_shift_data[team_id] = {
                "teamId": team_id,
                "teamName": row["Name"],
                "shiftCounts": {},
            }
        team_shift_data[team_id]["shiftCounts"][row["Code"]] = row["ShiftCount"]

    team_shift_distribution = list(team_shift_data.values())

    cursor.execute(
        """
        SELECT t.Id, t.Name,
               COUNT(DISTINCT e.Id) as EmployeeCount,
               COUNT(sa.Id) as TotalShifts,
               CASE WHEN COUNT(DISTINCT e.Id) > 0
                    THEN CAST(COUNT(sa.Id) AS REAL) / COUNT(DISTINCT e.Id)
                    ELSE 0 END as AvgShiftsPerEmployee
        FROM Teams t
        LEFT JOIN Employees e ON t.Id = e.TeamId
        LEFT JOIN ShiftAssignments sa ON e.Id = sa.EmployeeId
            AND sa.Date >= ? AND sa.Date <= ?
        GROUP BY t.Id, t.Name
        HAVING EmployeeCount > 0
        ORDER BY t.Name
    """,
        (start_date.isoformat(), end_date.isoformat()),
    )

    team_workload = []
    for row in cursor.fetchall():
        team_workload.append(
            {
                "teamId": row["Id"],
                "teamName": row["Name"],
                "employeeCount": row["EmployeeCount"],
                "totalShifts": row["TotalShifts"],
                "averageShiftsPerEmployee": row["AvgShiftsPerEmployee"],
            }
        )

    cursor.execute(
        """
        SELECT e.Id, e.Vorname, e.Name,
               st.Code as ShiftCode,
               st.Name as ShiftName,
               COUNT(sa.Id) as DaysWorked
        FROM Employees e
        LEFT JOIN ShiftAssignments sa ON e.Id = sa.EmployeeId
            AND sa.Date >= ? AND sa.Date <= ?
        LEFT JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
        WHERE st.Code IS NOT NULL
        GROUP BY e.Id, e.Vorname, e.Name, st.Code, st.Name
        ORDER BY e.Vorname, e.Name, st.Code
    """,
        (start_date.isoformat(), end_date.isoformat()),
    )

    employee_shift_details: dict[int, dict[str, Any]] = {}
    for row in cursor.fetchall():
        emp_id = row["Id"]
        if emp_id not in employee_shift_details:
            employee_shift_details[emp_id] = {
                "employeeId": emp_id,
                "employeeName": f"{row['Vorname']} {row['Name']}",
                "shiftTypes": {},
                "totalSaturdays": 0,
                "totalSundays": 0,
            }

        shift_code = row["ShiftCode"]
        employee_shift_details[emp_id]["shiftTypes"][shift_code] = {
            "name": row["ShiftName"],
            "days": row["DaysWorked"],
        }

    cursor.execute(
        """
        SELECT e.Id,
               COUNT(DISTINCT CASE WHEN strftime('%w', sa.Date) = '6' THEN sa.Date END) as Saturdays,
               COUNT(DISTINCT CASE WHEN strftime('%w', sa.Date) = '0' THEN sa.Date END) as Sundays
        FROM Employees e
        LEFT JOIN ShiftAssignments sa ON e.Id = sa.EmployeeId
            AND sa.Date >= ? AND sa.Date <= ?
        WHERE sa.Id IS NOT NULL
        GROUP BY e.Id
    """,
        (start_date.isoformat(), end_date.isoformat()),
    )

    for row in cursor.fetchall():
        emp_id = row["Id"]
        if emp_id in employee_shift_details:
            employee_shift_details[emp_id]["totalSaturdays"] = row["Saturdays"]
            employee_shift_details[emp_id]["totalSundays"] = row["Sundays"]

    employee_shift_details_list = sorted(
        employee_shift_details.values(),
        key=lambda x: x["employeeName"],
    )

    return {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "employeeWorkHours": employee_work_hours,
        "teamShiftDistribution": team_shift_distribution,
        "employeeAbsenceDays": employee_absence_days,
        "teamWorkload": team_workload,
        "employeeShiftDetails": employee_shift_details_list,
    }
