"""Vacation year plan (read-only) API routes."""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from .shared import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get('/api/vacationyearplan/{year}')
def get_vacation_year_plan(request: Request, year: int):
    """
    Get vacation plan for a specific year.
    Returns vacation data only if the year is approved by admin.
    All users can access this endpoint.
    """
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Check if year is approved
    cursor.execute("""
        SELECT IsApproved FROM VacationYearApprovals WHERE Year = ?
    """, (year,))
    
    approval_row = cursor.fetchone()
    
    # If year is not approved, return empty data
    if not approval_row or not approval_row['IsApproved']:
        conn.close()
        return {
            'year': year,
            'isApproved': False,
            'vacations': [],
            'message': 'Urlaubsdaten für dieses Jahr wurden noch nicht freigegeben.'
        }
    
    # Get all vacation data for the year (from VacationRequests and Absences)
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    
    # Get approved vacation requests
    cursor.execute("""
        SELECT 
            vr.Id,
            vr.EmployeeId,
            e.Vorname,
            e.Name,
            e.TeamId,
            t.Name as TeamName,
            vr.StartDate,
            vr.EndDate,
            vr.Status,
            vr.Notes,
            'VacationRequest' as Source
        FROM VacationRequests vr
        JOIN Employees e ON vr.EmployeeId = e.Id
        LEFT JOIN Teams t ON e.TeamId = t.Id
        WHERE (vr.StartDate <= ? AND vr.EndDate >= ?)
        ORDER BY vr.StartDate, e.Name, e.Vorname
    """, (end_date, start_date))
    
    vacation_requests = []
    for row in cursor.fetchall():
        vacation_requests.append({
            'id': row['Id'],
            'employeeId': row['EmployeeId'],
            'employeeName': f"{row['Vorname']} {row['Name']}",
            'teamId': row['TeamId'],
            'teamName': row['TeamName'],
            'startDate': row['StartDate'],
            'endDate': row['EndDate'],
            'status': row['Status'],
            'notes': row['Notes'],
            'source': row['Source']
        })
    
    # Get vacation absences (Type 2 = Urlaub)
    cursor.execute("""
        SELECT 
            a.Id,
            a.EmployeeId,
            e.Vorname,
            e.Name,
            e.TeamId,
            t.Name as TeamName,
            a.StartDate,
            a.EndDate,
            a.Notes,
            'Absence' as Source
        FROM Absences a
        JOIN Employees e ON a.EmployeeId = e.Id
        LEFT JOIN Teams t ON e.TeamId = t.Id
        WHERE a.Type = 2
        AND (a.StartDate <= ? AND a.EndDate >= ?)
        ORDER BY a.StartDate, e.Name, e.Vorname
    """, (end_date, start_date))
    
    absences = []
    for row in cursor.fetchall():
        absences.append({
            'id': row['Id'],
            'employeeId': row['EmployeeId'],
            'employeeName': f"{row['Vorname']} {row['Name']}",
            'teamId': row['TeamId'],
            'teamName': row['TeamName'],
            'startDate': row['StartDate'],
            'endDate': row['EndDate'],
            'status': 'Genehmigt',  # Absences are always approved
            'notes': row['Notes'],
            'source': row['Source']
        })
    
    conn.close()
    
    return {
        'year': year,
        'isApproved': True,
        'vacationRequests': vacation_requests,
        'absences': absences
    }
