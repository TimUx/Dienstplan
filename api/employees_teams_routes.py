"""Team CRUD API routes."""

import json
import logging

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from .shared import get_db, require_role, log_audit, check_csrf, parse_json_body

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get('/api/teams')
def get_teams(request: Request):
    """Get all teams with employee count"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT t.Id, t.Name, t.Description, t.Email,
               COUNT(e.Id) as EmployeeCount
        FROM Teams t
        LEFT JOIN Employees e ON t.Id = e.TeamId
        GROUP BY t.Id, t.Name, t.Description, t.Email
        ORDER BY t.Name
    """)
    
    teams = []
    for row in cursor.fetchall():
        employee_count = int(row['EmployeeCount'])
        
        teams.append({
            'id': row['Id'],
            'name': row['Name'],
            'description': row['Description'],
            'email': row['Email'],
                            'employeeCount': employee_count
        })
    
    conn.close()
    return teams


@router.get('/api/teams/{id}')
def get_team(request: Request, id: int):
    """Get single team by ID"""
    conn = None
    db = get_db()
    try:
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT t.Id, t.Name, t.Description, t.Email,
                   COUNT(e.Id) as EmployeeCount
            FROM Teams t
            LEFT JOIN Employees e ON t.Id = e.TeamId
            WHERE t.Id = ?
            GROUP BY t.Id, t.Name, t.Description, t.Email
        """, (id,))
        
        row = cursor.fetchone()
        
        if not row:
            return JSONResponse(content={'error': 'Team nicht gefunden'}, status_code=404)
        
        employee_count = int(row['EmployeeCount'])
        
        return {
            'id': row['Id'],
            'name': row['Name'],
            'description': row['Description'],
            'email': row['Email'],
                            'employeeCount': employee_count
        }
    finally:
        if conn:
            conn.close()


@router.post('/api/teams', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def create_team(request: Request, data: dict = Depends(parse_json_body)):
    """Create new team"""
    try:
        # Validate required fields
        if not data.get('name'):
            return JSONResponse(content={'error': 'Teamname ist Pflichtfeld'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO Teams (Name, Description, Email)
            VALUES (?, ?, ?)
        """, (
            data.get('name'),
            data.get('description'),
            data.get('email')
        ))
        
        team_id = cursor.lastrowid
        
        # Log audit entry
        changes = json.dumps({
            'name': data.get('name'),
            'description': data.get('description'),
            'email': data.get('email'),
                        }, ensure_ascii=False)
        log_audit(conn, 'Team', team_id, 'Created', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return JSONResponse(content={'success': True, 'id': team_id}, status_code=201)
        
    except Exception as e:
        logger.error(f"Create team error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Erstellen: {str(e)}'}, status_code=500)


@router.put('/api/teams/{id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def update_team(request: Request, id: int, data: dict = Depends(parse_json_body)):
    """Update team"""
    try:
        # Validate required fields
        if not data.get('name'):
            return JSONResponse(content={'error': 'Teamname ist Pflichtfeld'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if team exists and get old values for audit
        cursor.execute("SELECT Name, Description, Email FROM Teams WHERE Id = ?", (id,))
        old_row = cursor.fetchone()
        if not old_row:
            conn.close()
            return JSONResponse(content={'error': 'Team nicht gefunden'}, status_code=404)
        
        cursor.execute("""
            UPDATE Teams 
            SET Name = ?, Description = ?, Email = ?
            WHERE Id = ?
        """, (
            data.get('name'),
            data.get('description'),
            data.get('email'),
            id
        ))
        
        # Log audit entry with changes
        changes_dict = {}
        if old_row['Name'] != data.get('name'):
            changes_dict['name'] = {'old': old_row['Name'], 'new': data.get('name')}
        if old_row['Description'] != data.get('description'):
            changes_dict['description'] = {'old': old_row['Description'], 'new': data.get('description')}
        if old_row['Email'] != data.get('email'):
            changes_dict['email'] = {'old': old_row['Email'], 'new': data.get('email')}
        if changes_dict:
            changes = json.dumps(changes_dict, ensure_ascii=False)
            log_audit(conn, 'Team', id, 'Updated', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Update team error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Aktualisieren: {str(e)}'}, status_code=500)


@router.delete('/api/teams/{id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def delete_team(request: Request, id: int):
    """Delete team (Admin only)"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if team exists and get info for audit
        cursor.execute("SELECT Name FROM Teams WHERE Id = ?", (id,))
        team_row = cursor.fetchone()
        if not team_row:
            conn.close()
            return JSONResponse(content={'error': 'Team nicht gefunden'}, status_code=404)
        
        # Check if team has employees
        cursor.execute("SELECT COUNT(*) as count FROM Employees WHERE TeamId = ?", (id,))
        employee_count = cursor.fetchone()['count']
        
        if employee_count > 0:
            conn.close()
            return JSONResponse(content={'error': f'Team hat {employee_count} Mitarbeiter und kann nicht gelöscht werden'}, status_code=400)
        
        # Clear TeamId from AdminNotifications to avoid foreign key constraint violations
        # (AdminNotifications don't have CASCADE delete)
        cursor.execute("UPDATE AdminNotifications SET TeamId = NULL WHERE TeamId = ?", (id,))
        
        # Delete team (TeamShiftAssignments will be automatically deleted due to CASCADE)
        cursor.execute("DELETE FROM Teams WHERE Id = ?", (id,))
        
        # Log audit entry
        changes = json.dumps({'name': team_row['Name']}, ensure_ascii=False)
        log_audit(conn, 'Team', id, 'Deleted', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Delete team error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Löschen: {str(e)}'}, status_code=500)

