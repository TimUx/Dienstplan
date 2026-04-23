"""Shift schedule (calendar) API routes."""

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .error_utils import api_error
from .shared import get_db, _paginate

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get('/api/shifts/schedule')

def get_schedule(request: Request):
    """Get shift schedule for a date range.

    Optional pagination query parameters:
      - page  (int, default 1): 1-based page number for assignments
      - limit (int, default 0): assignments per page; 0 means return all
    """
    start_date_str = request.query_params.get('startDate')
    end_date_str = request.query_params.get('endDate')
    view = request.query_params.get('view', 'week')

    # Parse pagination parameters
    try:
        page = max(1, int(request.query_params.get('page', 1)))
        limit = max(0, int(request.query_params.get('limit', 0)))
    except (ValueError, TypeError):
        return JSONResponse(content={'error': 'page and limit must be integers'}, status_code=400)

    if not start_date_str:
        return JSONResponse(content={'error': 'startDate is required'}, status_code=400)
    
    # Validate and parse dates
    try:
        start_date = date.fromisoformat(start_date_str)
    except (ValueError, TypeError):
        return JSONResponse(content={'error': 'Invalid startDate format. Use YYYY-MM-DD'}, status_code=400)
    
    # Calculate end date based on view
    if not end_date_str:
        if view == 'week':
            end_date = start_date + timedelta(days=6)
        elif view == 'month':
            # Get last day of month
            if start_date.month == 12:
                end_date = date(start_date.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(start_date.year, start_date.month + 1, 1) - timedelta(days=1)
            
            # Expand to complete calendar weeks (Sunday-Saturday)
            # Find Sunday of the week containing start_date (first day of month)
            start_weekday = start_date.weekday()  # Monday=0, Sunday=6
            if start_weekday != 6:  # Not Sunday
                days_back = start_weekday + 1
                start_date = start_date - timedelta(days=days_back)
            
            # Find Saturday of the week containing end_date (last day of month)
            end_weekday = end_date.weekday()  # Monday=0, Sunday=6
            if end_weekday != 5:  # If not Saturday already
                days_forward = (5 - end_weekday + 7) % 7
                end_date = end_date + timedelta(days=days_forward)
        elif view == 'year':
            end_date = date(start_date.year, 12, 31)
        else:
            end_date = start_date + timedelta(days=30)
    else:
        try:
            end_date = date.fromisoformat(end_date_str)
        except (ValueError, TypeError):
            return JSONResponse(content={'error': 'Invalid endDate format. Use YYYY-MM-DD'}, status_code=400)
    
    conn = None
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if user is admin (can see unapproved plans)
        user_roles = request.session.get('user_roles', [])
        is_admin = 'Admin' in user_roles
        
        # Get approved months if user is not admin
        approved_months = set()
        if not is_admin:
            cursor.execute("""
                SELECT Year, Month FROM ShiftPlanApprovals
                WHERE IsApproved = 1
            """)
            for row in cursor.fetchall():
                approved_months.add((row['Year'], row['Month']))
        
        # Get assignments
        cursor.execute("""
            SELECT sa.*, e.Vorname, e.Name, e.TeamId,
                   st.Code, st.Name as ShiftName, st.ColorCode
            FROM ShiftAssignments sa
            JOIN Employees e ON sa.EmployeeId = e.Id
            JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
            WHERE sa.Date >= ? AND sa.Date <= ?
            ORDER BY sa.Date, e.TeamId, e.Name, e.Vorname
        """, (start_date.isoformat(), end_date.isoformat()))
        
        assignments = []
        for row in cursor.fetchall():
            assignment_date = date.fromisoformat(row['Date'])
            year_month = (assignment_date.year, assignment_date.month)
            
            # Filter based on approval status for non-admin users
            if not is_admin and year_month not in approved_months:
                # Skip unapproved plans for regular users
                continue
            
            assignments.append({
                'id': row['Id'],
                'employeeId': row['EmployeeId'],
                'employeeName': f"{row['Vorname']} {row['Name']}",
                'teamId': row['TeamId'],
                'shiftTypeId': row['ShiftTypeId'],
                'shiftCode': row['Code'],
                'shiftName': row['ShiftName'],
                'colorCode': row['ColorCode'],
                'date': row['Date'],
                'isManual': bool(row['IsManual']),
                'isFixed': bool(row['IsFixed']),
                'notes': row['Notes']
            })
        
        # Get absences from Absences table
        cursor.execute("""
            SELECT a.*, e.Vorname, e.Name, e.TeamId
            FROM Absences a
            JOIN Employees e ON a.EmployeeId = e.Id
            WHERE (a.StartDate <= ? AND a.EndDate >= ?)
               OR (a.StartDate >= ? AND a.StartDate <= ?)
        """, (end_date.isoformat(), start_date.isoformat(), 
              start_date.isoformat(), end_date.isoformat()))
        
        absences = []
        for row in cursor.fetchall():
            type_index = row['Type']
            absences.append({
                'id': row['Id'],
                'employeeId': row['EmployeeId'],
                'employeeName': f"{row['Vorname']} {row['Name']}",
                'teamId': row['TeamId'],
                'type': ['', 'Krank', 'Urlaub', 'Lehrgang'][type_index],
                'status': 'Genehmigt' if type_index == 2 else None,  # Only Urlaub type has status
                'startDate': row['StartDate'],
                'endDate': row['EndDate'],
                'notes': row['Notes']
            })
        
        # Also get vacation requests (all statuses) and add them as absences
        cursor.execute("""
            SELECT vr.Id, vr.EmployeeId, vr.StartDate, vr.EndDate, vr.Notes, vr.Status,
                   e.Vorname, e.Name, e.TeamId
            FROM VacationRequests vr
            JOIN Employees e ON vr.EmployeeId = e.Id
            WHERE ((vr.StartDate <= ? AND vr.EndDate >= ?)
               OR (vr.StartDate >= ? AND vr.StartDate <= ?))
        """, (end_date.isoformat(), start_date.isoformat(),
              start_date.isoformat(), end_date.isoformat()))
        
        vacation_id_offset = 10000  # Offset to avoid ID conflicts
        for row in cursor.fetchall():
            # Determine the type label based on status
            if row['Status'] == 'Genehmigt':
                type_label = 'Urlaub'
                notes = row['Notes'] or 'Genehmigter Urlaub'
            elif row['Status'] == 'InBearbeitung':
                type_label = 'Urlaub (in Genehmigung)'
                notes = row['Notes'] or 'Urlaubsantrag in Bearbeitung'
            else:  # Abgelehnt
                type_label = 'Urlaub (abgelehnt)'
                notes = row['Notes'] or 'Urlaubsantrag abgelehnt'
            
            absences.append({
                'id': vacation_id_offset + row['Id'],
                'employeeId': row['EmployeeId'],
                'employeeName': f"{row['Vorname']} {row['Name']}",
                'teamId': row['TeamId'],
                'type': type_label,
                'status': row['Status'],  # Include status for color-coding
                'startDate': row['StartDate'],
                'endDate': row['EndDate'],
                'notes': notes
            })
        
        # Get vacation periods (Ferienzeiten) that overlap with the date range
        cursor.execute("""
            SELECT Id, Name, StartDate, EndDate, ColorCode
            FROM VacationPeriods
            WHERE (StartDate <= ? AND EndDate >= ?)
               OR (StartDate >= ? AND StartDate <= ?)
            ORDER BY StartDate
        """, (end_date.isoformat(), start_date.isoformat(),
              start_date.isoformat(), end_date.isoformat()))
        
        vacation_periods = []
        for row in cursor.fetchall():
            vacation_periods.append({
                'id': row['Id'],
                'name': row['Name'],
                'startDate': row['StartDate'],
                'endDate': row['EndDate'],
                'colorCode': row['ColorCode'] or '#E8F5E9'
            })
        
        pagination = _paginate(assignments, page, limit)

        return {
            'startDate': start_date.isoformat(),
            'endDate': end_date.isoformat(),
            'assignments': pagination['data'],
            'absences': absences,
            'vacationPeriods': vacation_periods,
            'pagination': {
                'total': pagination['total'],
                'page': pagination['page'],
                'limit': pagination['limit'],
                'totalPages': pagination['totalPages'],
            }
        }
        
    except Exception as e:
        return api_error(
            logger,
            'Datenbankfehler beim Laden des Dienstplans',
            status_code=500,
            exc=e,
            context='get_schedule failed',
        )
    finally:
        if conn:
            conn.close()

