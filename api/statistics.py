"""
Statistics APIRouter: dashboard stats, audit logs, notifications.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from datetime import date, timedelta
import logging

from .shared import get_db, require_role, require_csrf, check_csrf

logger = logging.getLogger(__name__)

router = APIRouter()
DEFAULT_WEEKLY_HOURS_FALLBACK = 48.0
MAX_ABSENCE_DAYS_PER_WEEK = 6


@router.get('/api/statistics/dashboard')
async def get_dashboard_stats(request: Request):
    """Get dashboard statistics"""
    start_date_str = request.query_params.get('startDate')
    end_date_str = request.query_params.get('endDate')
    
    if not start_date_str or not end_date_str:
        # Default to current month
        today = date.today()
        start_date = date(today.year, today.month, 1)
        if today.month == 12:
            end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
    else:
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
    
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Employee work hours
    # IMPORTANT: For statistics calculation:
    # - AU (sick leave), U (vacation) and L (training) count as worked time
    # - Absence credit is based on configured weekly shift hours
    # - Max credit is 6 days per calendar week (never 7 days)

    # First, calculate assigned shift hours
    cursor.execute("""
        SELECT e.Id, e.Vorname, e.Name, e.TeamId,
               COUNT(sa.Id) as ShiftCount,
               COALESCE(SUM(st.DurationHours), 0) as ShiftHours
        FROM Employees e
        LEFT JOIN ShiftAssignments sa ON e.Id = sa.EmployeeId 
            AND sa.Date >= ? AND sa.Date <= ?
        LEFT JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
        GROUP BY e.Id, e.Vorname, e.Name, e.TeamId
    """, (start_date.isoformat(), end_date.isoformat()))
    
    employee_hours_map = {}
    for row in cursor.fetchall():
        employee_hours_map[row['Id']] = {
            'id': row['Id'],
            'name': f"{row['Vorname']} {row['Name']}",
            'teamId': row['TeamId'],
            'shiftCount': row['ShiftCount'],
            'shiftHours': float(row['ShiftHours'] or 0),
            'absenceHours': 0.0,
            'weeklyHours': 0.0
        }

    # Determine weekly working hours per employee:
    # 1) shift assignments in range, 2) team shift configuration, 3) global fallback
    cursor.execute("""
        SELECT e.Id,
               MAX(st.WeeklyWorkingHours) as WeeklyHours
        FROM Employees e
        LEFT JOIN ShiftAssignments sa ON e.Id = sa.EmployeeId
            AND sa.Date >= ? AND sa.Date <= ?
        LEFT JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
        GROUP BY e.Id
    """, (start_date.isoformat(), end_date.isoformat()))
    assigned_weekly_hours = {row['Id']: float(row['WeeklyHours'] or 0) for row in cursor.fetchall()}

    cursor.execute("""
        SELECT e.Id,
               MAX(st.WeeklyWorkingHours) as WeeklyHours
        FROM Employees e
        LEFT JOIN TeamShiftAssignments tsa ON e.TeamId = tsa.TeamId
        LEFT JOIN ShiftTypes st ON tsa.ShiftTypeId = st.Id
        GROUP BY e.Id
    """)
    team_weekly_hours = {row['Id']: float(row['WeeklyHours'] or 0) for row in cursor.fetchall()}

    cursor.execute("""
        SELECT COALESCE(MAX(WeeklyWorkingHours), ?) as DefaultWeeklyHours
        FROM ShiftTypes
        WHERE IsActive = 1
    """, (DEFAULT_WEEKLY_HOURS_FALLBACK,))
    weekly_hours_default = float(cursor.fetchone()['DefaultWeeklyHours'] or DEFAULT_WEEKLY_HOURS_FALLBACK)

    for emp_id, emp_data in employee_hours_map.items():
        weekly_hours = assigned_weekly_hours.get(emp_id, 0.0)
        if weekly_hours <= 0:
            weekly_hours = team_weekly_hours.get(emp_id, 0.0)
        if weekly_hours <= 0:
            weekly_hours = weekly_hours_default
        emp_data['weeklyHours'] = weekly_hours

    # Load absences with type code and clip them to the selected period in Python.
    # This ensures period overlap is counted correctly (instead of full absence range).
    cursor.execute("""
        SELECT e.Id, e.Vorname, e.Name, a.Type, a.StartDate, a.EndDate,
               at.Code as TypeCode
        FROM Absences a
        JOIN Employees e ON e.Id = a.EmployeeId
        LEFT JOIN AbsenceTypes at ON a.AbsenceTypeId = at.Id
        WHERE (a.StartDate <= ? AND a.EndDate >= ?)
           OR (a.StartDate >= ? AND a.StartDate <= ?)
        ORDER BY e.Vorname, e.Name, a.StartDate
    """, (
        end_date.isoformat(), start_date.isoformat(),
        start_date.isoformat(), end_date.isoformat()
    ))

    type_id_to_code = {1: 'AU', 2: 'U', 3: 'L'}
    employee_absence_sets = {}
    employee_absence_credit_sets = {}

    for row in cursor.fetchall():
        emp_id = row['Id']
        if emp_id not in employee_absence_sets:
            employee_absence_sets[emp_id] = {
                'employeeId': emp_id,
                'employeeName': f"{row['Vorname']} {row['Name']}",
                'allDays': set(),
                'byType': {}
            }
            employee_absence_credit_sets[emp_id] = set()

        absence_start = date.fromisoformat(row['StartDate'])
        absence_end = date.fromisoformat(row['EndDate'])
        overlap_start = max(absence_start, start_date)
        overlap_end = min(absence_end, end_date)
        if overlap_start > overlap_end:
            continue

        absence_type_code = row['TypeCode'] or type_id_to_code.get(row['Type'], str(row['Type']))
        if absence_type_code not in employee_absence_sets[emp_id]['byType']:
            employee_absence_sets[emp_id]['byType'][absence_type_code] = set()

        current_day = overlap_start
        while current_day <= overlap_end:
            employee_absence_sets[emp_id]['allDays'].add(current_day)
            employee_absence_sets[emp_id]['byType'][absence_type_code].add(current_day)
            if absence_type_code in {'AU', 'U', 'L'}:
                employee_absence_credit_sets[emp_id].add(current_day)
            current_day += timedelta(days=1)

    # Convert absence sets for frontend
    employee_absence_days = []
    for emp_absence in employee_absence_sets.values():
        by_type_counts = {
            code: len(day_set)
            for code, day_set in emp_absence['byType'].items()
            if day_set
        }
        total_days = len(emp_absence['allDays'])
        if total_days > 0:
            employee_absence_days.append({
                'employeeId': emp_absence['employeeId'],
                'employeeName': emp_absence['employeeName'],
                'totalDays': total_days,
                'byType': by_type_counts
            })

    employee_absence_days.sort(key=lambda x: x['employeeName'])

    # Add absence hour credit to employee work hours, max. 6 absence days per week.
    for emp_id, absence_days in employee_absence_credit_sets.items():
        if not absence_days:
            continue
        if emp_id not in employee_hours_map:
            employee_name = employee_absence_sets.get(emp_id, {}).get('employeeName', f"Mitarbeiter {emp_id}")
            employee_hours_map[emp_id] = {
                'id': emp_id,
                'name': employee_name,
                'teamId': None,
                'shiftCount': 0,
                'shiftHours': 0.0,
                'absenceHours': 0.0,
                'weeklyHours': weekly_hours_default
            }

        weekly_day_count = {}
        for d in absence_days:
            week_start = d - timedelta(days=d.weekday())  # Monday-based calendar week
            weekly_day_count[week_start] = weekly_day_count.get(week_start, 0) + 1

        credited_days = sum(min(days_in_week, MAX_ABSENCE_DAYS_PER_WEEK) for days_in_week in weekly_day_count.values())
        weekly_hours = employee_hours_map[emp_id]['weeklyHours']
        daily_hours = (weekly_hours / MAX_ABSENCE_DAYS_PER_WEEK) if weekly_hours > 0 else 0.0
        employee_hours_map[emp_id]['absenceHours'] = credited_days * daily_hours

    # Build final work-hours result list
    employee_work_hours = []
    for emp_data in employee_hours_map.values():
        total_hours = emp_data['shiftHours'] + emp_data['absenceHours']
        if total_hours > 0:
            employee_work_hours.append({
                'employeeId': emp_data['id'],
                'employeeName': emp_data['name'],
                'teamId': emp_data['teamId'],
                'shiftCount': emp_data['shiftCount'],
                'totalHours': total_hours
            })

    employee_work_hours.sort(key=lambda x: x['employeeName'])
    
    # Team shift distribution
    cursor.execute("""
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
    """, (start_date.isoformat(), end_date.isoformat()))
    
    team_shift_data = {}
    for row in cursor.fetchall():
        team_id = row['Id']
        if team_id not in team_shift_data:
            team_shift_data[team_id] = {
                'teamId': team_id,
                'teamName': row['Name'],
                'shiftCounts': {}
            }
        team_shift_data[team_id]['shiftCounts'][row['Code']] = row['ShiftCount']
    
    team_shift_distribution = list(team_shift_data.values())
    
    # Team workload
    cursor.execute("""
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
    """, (start_date.isoformat(), end_date.isoformat()))
    
    team_workload = []
    for row in cursor.fetchall():
        team_workload.append({
            'teamId': row['Id'],
            'teamName': row['Name'],
            'employeeCount': row['EmployeeCount'],
            'totalShifts': row['TotalShifts'],
            'averageShiftsPerEmployee': row['AvgShiftsPerEmployee']
        })
    
    # Employee shift details with weekend counts
    # Note: Only includes employees with valid shift assignments in the date range
    # First, get shift type counts per employee
    cursor.execute("""
        SELECT e.Id, e.Vorname, e.Name,
               st.Code as ShiftCode,
               st.Name as ShiftName,
               COUNT(sa.Id) as DaysWorked
        FROM Employees e
        LEFT JOIN ShiftAssignments sa ON e.Id = sa.EmployeeId 
            AND sa.Date >= ? AND sa.Date <= ?
        LEFT JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
        WHERE st.Code IS NOT NULL  -- Only include valid shift assignments
        GROUP BY e.Id, e.Vorname, e.Name, st.Code, st.Name
        ORDER BY e.Vorname, e.Name, st.Code
    """, (start_date.isoformat(), end_date.isoformat()))
    
    # Build employee shift details map
    employee_shift_details = {}
    for row in cursor.fetchall():
        emp_id = row['Id']
        if emp_id not in employee_shift_details:
            employee_shift_details[emp_id] = {
                'employeeId': emp_id,
                'employeeName': f"{row['Vorname']} {row['Name']}",
                'shiftTypes': {},
                'totalSaturdays': 0,
                'totalSundays': 0
            }
        
        shift_code = row['ShiftCode']
        employee_shift_details[emp_id]['shiftTypes'][shift_code] = {
            'name': row['ShiftName'],
            'days': row['DaysWorked']
        }
    
    # Now get weekend counts separately per employee (to avoid double counting)
    # Uses DISTINCT to count unique weekend dates, not individual shift assignments
    cursor.execute("""
        SELECT e.Id,
               COUNT(DISTINCT CASE WHEN strftime('%w', sa.Date) = '6' THEN sa.Date END) as Saturdays,
               COUNT(DISTINCT CASE WHEN strftime('%w', sa.Date) = '0' THEN sa.Date END) as Sundays
        FROM Employees e
        LEFT JOIN ShiftAssignments sa ON e.Id = sa.EmployeeId 
            AND sa.Date >= ? AND sa.Date <= ?
        WHERE sa.Id IS NOT NULL  -- Only employees with shift assignments
        GROUP BY e.Id
    """, (start_date.isoformat(), end_date.isoformat()))
    
    for row in cursor.fetchall():
        emp_id = row['Id']
        if emp_id in employee_shift_details:
            employee_shift_details[emp_id]['totalSaturdays'] = row['Saturdays']
            employee_shift_details[emp_id]['totalSundays'] = row['Sundays']
    
    # Convert to list and sort by employee name
    employee_shift_details_list = sorted(
        employee_shift_details.values(),
        key=lambda x: x['employeeName']
    )
    
    conn.close()
    
    return {
        'startDate': start_date.isoformat(),
        'endDate': end_date.isoformat(),
        'employeeWorkHours': employee_work_hours,
        'teamShiftDistribution': team_shift_distribution,
        'employeeAbsenceDays': employee_absence_days,
        'teamWorkload': team_workload,
        'employeeShiftDetails': employee_shift_details_list
    }


# ============================================================================
# AUDIT LOG ENDPOINTS
# ============================================================================

@router.get('/api/auditlogs', dependencies=[Depends(require_role('Admin'))])
async def get_audit_logs(request: Request):
    """Get audit logs with pagination and filters"""
    try:
        # Get and validate pagination parameters
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('pageSize', 50))
        except (ValueError, TypeError):
            return JSONResponse(content={'error': 'Invalid pagination parameters'}, status_code=400)
        
        # Validate pagination ranges
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = min(max(page_size, 1), 100)
        
        # Get filter parameters
        entity_name = request.query_params.get('entityName')
        action = request.query_params.get('action')
        start_date = request.query_params.get('startDate')
        end_date = request.query_params.get('endDate')
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Build WHERE clause with parameterized queries for safety
        where_clauses = []
        params = []
        
        # Whitelist valid filters to prevent any potential SQL injection
        if entity_name:
            where_clauses.append("EntityName = ?")
            params.append(entity_name)
        
        if action:
            where_clauses.append("Action = ?")
            params.append(action)
        
        if start_date:
            where_clauses.append("DATE(Timestamp) >= ?")
            params.append(start_date)
        
        if end_date:
            where_clauses.append("DATE(Timestamp) <= ?")
            params.append(end_date)
        
        # Safe: only joining static WHERE clauses, all values are parameterized
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM AuditLogs WHERE {where_sql}"
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()['total']
        
        # Calculate pagination
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
        offset = (page - 1) * page_size
        
        # Get paginated results - safe: WHERE clause uses only parameterized queries
        select_query = f"""
            SELECT Id, Timestamp, UserId, UserName, EntityName, EntityId, Action, Changes
            FROM AuditLogs
            WHERE {where_sql}
            ORDER BY Timestamp DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(select_query, params + [page_size, offset])
        
        items = []
        for row in cursor.fetchall():
            items.append({
                'id': row['Id'],
                'timestamp': row['Timestamp'],
                'userId': row['UserId'],
                'userName': row['UserName'],
                'entityName': row['EntityName'],
                'entityId': row['EntityId'],
                'action': row['Action'],
                'changes': row['Changes']
            })
        
        conn.close()
        
        return {
            'items': items,
            'page': page,
            'pageSize': page_size,
            'totalCount': total_count,
            'totalPages': total_pages,
            'hasPreviousPage': page > 1,
            'hasNextPage': page < total_pages
        }
        
    except Exception as e:
        logger.error(f"Get audit logs error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Laden der Audit-Logs: {str(e)}'}, status_code=500)


@router.get('/api/auditlogs/recent/{count}', dependencies=[Depends(require_role('Admin'))])
async def get_recent_audit_logs(request: Request, count: int):
    """Get recent audit logs (simplified endpoint for backwards compatibility)"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT Id, Timestamp, UserId, UserName, EntityName, EntityId, Action, Changes
            FROM AuditLogs
            ORDER BY Timestamp DESC
            LIMIT ?
        """, (count,))
        
        logs = []
        for row in cursor.fetchall():
            logs.append({
                'id': row['Id'],
                'timestamp': row['Timestamp'],
                'userId': row['UserId'],
                'userName': row['UserName'],
                'entityName': row['EntityName'],
                'entityId': row['EntityId'],
                'action': row['Action'],
                'changes': row['Changes']
            })
        
        conn.close()
        return logs
        
    except Exception as e:
        logger.error(f"Get recent audit logs error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Laden der Audit-Logs: {str(e)}'}, status_code=500)


# ============================================================================
# NOTIFICATION ENDPOINTS
# ============================================================================

@router.get('/api/notifications', dependencies=[Depends(require_role('Admin', 'Disponent'))])
async def get_notifications(request: Request):
    """Get admin notifications (for Admins and Disponents only)"""
    try:
        unread_only = request.query_params.get('unreadOnly', 'false').lower() == 'true'
        limit = int(request.query_params.get('limit', 50))
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        if unread_only:
            cursor.execute("""
                SELECT 
                    n.Id, n.Type, n.Severity, n.Title, n.Message,
                    n.ShiftDate, n.ShiftCode, n.RequiredStaff, n.ActualStaff,
                    n.CreatedAt, n.IsRead, n.ReadAt, n.ReadBy,
                    e.Vorname, e.Name, 
                    t.Name as TeamName
                FROM AdminNotifications n
                LEFT JOIN Employees e ON n.EmployeeId = e.Id
                LEFT JOIN Teams t ON n.TeamId = t.Id
                WHERE n.IsRead = 0
                ORDER BY n.CreatedAt DESC
                LIMIT ?
            """, (limit,))
        else:
            cursor.execute("""
                SELECT 
                    n.Id, n.Type, n.Severity, n.Title, n.Message,
                    n.ShiftDate, n.ShiftCode, n.RequiredStaff, n.ActualStaff,
                    n.CreatedAt, n.IsRead, n.ReadAt, n.ReadBy,
                    e.Vorname, e.Name, 
                    t.Name as TeamName
                FROM AdminNotifications n
                LEFT JOIN Employees e ON n.EmployeeId = e.Id
                LEFT JOIN Teams t ON n.TeamId = t.Id
                ORDER BY n.CreatedAt DESC
                LIMIT ?
            """, (limit,))
        
        notifications = []
        for row in cursor.fetchall():
            notifications.append({
                'id': row[0],
                'type': row[1],
                'severity': row[2],
                'title': row[3],
                'message': row[4],
                'shiftDate': row[5],
                'shiftCode': row[6],
                'requiredStaff': row[7],
                'actualStaff': row[8],
                'createdAt': row[9],
                'isRead': bool(row[10]),
                'readAt': row[11],
                'readBy': row[12],
                'employeeName': f"{row[13]} {row[14]}" if row[13] else None,
                'teamName': row[15]
            })
        
        conn.close()
        return notifications
        
    except Exception as e:
        logger.error(f"Get notifications error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Laden der Benachrichtigungen: {str(e)}'}, status_code=500)


@router.get('/api/notifications/count', dependencies=[Depends(require_role('Admin', 'Disponent'))])
async def get_notification_count_endpoint(request: Request):
    """Get count of unread notifications"""
    try:
        db = get_db()
        conn = db.get_connection()
        from notification_manager import get_notification_count
        count = get_notification_count(conn, unread_only=True)
        conn.close()
        
        return {'count': count}
        
    except Exception as e:
        logger.error(f"Get notification count error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler: {str(e)}'}, status_code=500)


@router.post('/api/notifications/{id}/read', dependencies=[Depends(require_role('Admin', 'Disponent')), Depends(check_csrf)])
async def mark_notification_read(request: Request, id: int):
    """Mark notification as read"""
    try:
        db = get_db()
        conn = db.get_connection()
        from notification_manager import mark_notification_as_read
        success = mark_notification_as_read(conn, id, request.session.get('user_email'))
        conn.close()
        
        if success:
            return {'success': True}
        else:
            return JSONResponse(content={'error': 'Benachrichtigung nicht gefunden'}, status_code=404)
        
    except Exception as e:
        logger.error(f"Mark notification read error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler: {str(e)}'}, status_code=500)


@router.post('/api/notifications/mark-all-read', dependencies=[Depends(require_role('Admin', 'Disponent')), Depends(check_csrf)])
async def mark_all_notifications_read(request: Request):
    """Mark all notifications as read"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE AdminNotifications
            SET IsRead = 1, ReadAt = CURRENT_TIMESTAMP, ReadBy = ?
            WHERE IsRead = 0
        """, (request.session.get('user_email'),))
        
        conn.commit()
        count = cursor.rowcount
        conn.close()
        
        return {'success': True, 'count': count}
        
    except Exception as e:
        logger.error(f"Mark all notifications read error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler: {str(e)}'}, status_code=500)
