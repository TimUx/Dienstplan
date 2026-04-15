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
    # - AU (sick leave) and U (vacation): Count actual shift hours only (shifts are removed when absence is created)
    # - L (Lehrgang/training): Count 8h per training day even though shifts are removed
    
    # First, calculate shift hours
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
            'lehrgangHours': 0.0
        }
    
    # Then, calculate Lehrgang hours separately
    # Note: Type is stored as INTEGER in database: 1=AU, 2=U, 3=L
    cursor.execute("""
        SELECT a.EmployeeId,
               SUM(
                   CASE
                       WHEN a.StartDate >= ? AND a.EndDate <= ? THEN
                           julianday(a.EndDate) - julianday(a.StartDate) + 1
                       WHEN a.StartDate < ? AND a.EndDate <= ? THEN
                           julianday(a.EndDate) - julianday(?) + 1
                       WHEN a.StartDate >= ? AND a.EndDate > ? THEN
                           julianday(?) - julianday(a.StartDate) + 1
                       WHEN a.StartDate < ? AND a.EndDate > ? THEN
                           julianday(?) - julianday(?) + 1
                       ELSE 0
                   END
               ) * 8.0 as LehrgangHours
        FROM Absences a
        WHERE a.Type = 3
          AND ((a.StartDate <= ? AND a.EndDate >= ?)
            OR (a.StartDate >= ? AND a.StartDate <= ?))
        GROUP BY a.EmployeeId
    """, (
        start_date.isoformat(), end_date.isoformat(),  # Case 1: absence fully within period
        start_date.isoformat(), end_date.isoformat(), start_date.isoformat(),  # Case 2: absence starts before period
        start_date.isoformat(), end_date.isoformat(), end_date.isoformat(),  # Case 3: absence ends after period
        start_date.isoformat(), end_date.isoformat(), end_date.isoformat(), start_date.isoformat(),  # Case 4: absence spans entire period
        end_date.isoformat(), start_date.isoformat(),  # Overlap condition
        start_date.isoformat(), end_date.isoformat()  # Overlap condition
    ))
    
    for row in cursor.fetchall():
        emp_id = row['EmployeeId']
        lehrgang_hours = float(row['LehrgangHours'] or 0)
        
        if emp_id not in employee_hours_map:
            # Employee has Lehrgang but no shifts in this period
            cursor.execute("""
                SELECT Id, Vorname, Name, TeamId
                FROM Employees
                WHERE Id = ?
            """, (emp_id,))
            emp_row = cursor.fetchone()
            if emp_row:
                employee_hours_map[emp_id] = {
                    'id': emp_id,
                    'name': f"{emp_row['Vorname']} {emp_row['Name']}",
                    'teamId': emp_row['TeamId'],
                    'shiftCount': 0,
                    'shiftHours': 0.0,
                    'lehrgangHours': lehrgang_hours
                }
        else:
            employee_hours_map[emp_id]['lehrgangHours'] = lehrgang_hours
    
    # Build final result list
    employee_work_hours = []
    for emp_data in employee_hours_map.values():
        total_hours = emp_data['shiftHours'] + emp_data['lehrgangHours']
        if total_hours > 0:  # Only include employees with hours
            employee_work_hours.append({
                'employeeId': emp_data['id'],
                'employeeName': emp_data['name'],
                'teamId': emp_data['teamId'],
                'shiftCount': emp_data['shiftCount'],
                'totalHours': total_hours
            })
    
    # Sort alphabetically by employee name
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
    
    # Employee absence days - categorized by type
    cursor.execute("""
        SELECT e.Id, e.Vorname, e.Name, a.Type,
               SUM(julianday(a.EndDate) - julianday(a.StartDate) + 1) as TotalDays
        FROM Employees e
        JOIN Absences a ON e.Id = a.EmployeeId
        WHERE (a.StartDate <= ? AND a.EndDate >= ?)
           OR (a.StartDate >= ? AND a.StartDate <= ?)
        GROUP BY e.Id, e.Vorname, e.Name, a.Type
        HAVING TotalDays > 0
        ORDER BY e.Vorname, e.Name, a.Type
    """, (end_date.isoformat(), start_date.isoformat(),
          start_date.isoformat(), end_date.isoformat()))
    
    # Build employee absence data with categorization
    # Map integer type IDs to string codes for frontend display
    type_id_to_code = {1: 'AU', 2: 'U', 3: 'L'}
    
    employee_absence_map = {}
    for row in cursor.fetchall():
        emp_id = row['Id']
        if emp_id not in employee_absence_map:
            employee_absence_map[emp_id] = {
                'employeeId': emp_id,
                'employeeName': f"{row['Vorname']} {row['Name']}",
                'totalDays': 0,
                'byType': {}
            }
        
        absence_type_id = row['Type']
        absence_type_code = type_id_to_code.get(absence_type_id, str(absence_type_id))
        days = int(row['TotalDays'])
        employee_absence_map[emp_id]['byType'][absence_type_code] = days
        employee_absence_map[emp_id]['totalDays'] += days
    
    # Sort alphabetically by employee name
    employee_absence_days = sorted(
        employee_absence_map.values(),
        key=lambda x: x['employeeName']
    )
    
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
    })


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
