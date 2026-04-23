"""Rotation groups API routes."""

import json
import logging

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from .shared import get_db, require_role, log_audit, check_csrf, parse_json_body

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get('/api/rotationgroups')
def get_rotation_groups(request: Request):
    """Get all rotation groups"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT Id, Name, Description, IsActive, CreatedAt, CreatedBy, ModifiedAt, ModifiedBy
            FROM RotationGroups
            ORDER BY Name
        """)
        
        groups = []
        for row in cursor.fetchall():
            # Get shifts for this group
            cursor.execute("""
                SELECT st.Id, st.Code, st.Name, st.ColorCode, rgs.RotationOrder
                FROM RotationGroupShifts rgs
                INNER JOIN ShiftTypes st ON rgs.ShiftTypeId = st.Id
                WHERE rgs.RotationGroupId = ?
                ORDER BY rgs.RotationOrder
            """, (row['Id'],))
            
            shifts = []
            for shift_row in cursor.fetchall():
                shifts.append({
                    'id': shift_row['Id'],
                    'code': shift_row['Code'],
                    'name': shift_row['Name'],
                    'colorCode': shift_row['ColorCode'],
                    'rotationOrder': shift_row['RotationOrder']
                })
            
            groups.append({
                'id': row['Id'],
                'name': row['Name'],
                'description': row['Description'],
                'isActive': bool(row['IsActive']),
                'shifts': shifts,
                'createdAt': row['CreatedAt'],
                'createdBy': row['CreatedBy'],
                'modifiedAt': row['ModifiedAt'],
                'modifiedBy': row['ModifiedBy']
            })
        
        conn.close()
        return groups
        
    except Exception as e:
        logger.error(f"Get rotation groups error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Laden: {str(e)}'}, status_code=500)


@router.post('/api/rotationgroups', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def create_rotation_group(request: Request, data: dict = Depends(parse_json_body)):
    """Create new rotation group (Admin only)"""
    try:
        name = data.get('name')
        description = data.get('description', '')
        is_active = data.get('isActive', True)
        shifts = data.get('shifts', [])  # [{shiftTypeId, rotationOrder}]
        
        if not name:
            return JSONResponse(content={'error': 'Name ist erforderlich'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Insert rotation group
        cursor.execute("""
            INSERT INTO RotationGroups (Name, Description, IsActive, CreatedBy)
            VALUES (?, ?, ?, ?)
        """, (name, description, 1 if is_active else 0, request.session.get('user_email', 'system')))
        
        group_id = cursor.lastrowid
        
        # Insert shifts
        for shift in shifts:
            cursor.execute("""
                INSERT INTO RotationGroupShifts (RotationGroupId, ShiftTypeId, RotationOrder, CreatedBy)
                VALUES (?, ?, ?, ?)
            """, (group_id, shift['shiftTypeId'], shift['rotationOrder'], request.session.get('user_email', 'system')))
        
        # Log audit entry
        changes = json.dumps({'name': name, 'shifts': shifts}, ensure_ascii=False)
        log_audit(conn, 'RotationGroup', group_id, 'Created', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return JSONResponse(content={'success': True, 'id': group_id}, status_code=201)
        
    except Exception as e:
        logger.error(f"Create rotation group error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Erstellen: {str(e)}'}, status_code=500)


@router.get('/api/rotationgroups/{id}')
def get_rotation_group(request: Request, id: int):
    """Get single rotation group by ID"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT Id, Name, Description, IsActive, CreatedAt, CreatedBy, ModifiedAt, ModifiedBy
            FROM RotationGroups
            WHERE Id = ?
        """, (id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return JSONResponse(content={'error': 'Rotationsgruppe nicht gefunden'}, status_code=404)
        
        # Get shifts for this group
        cursor.execute("""
            SELECT st.Id, st.Code, st.Name, st.ColorCode, rgs.RotationOrder
            FROM RotationGroupShifts rgs
            INNER JOIN ShiftTypes st ON rgs.ShiftTypeId = st.Id
            WHERE rgs.RotationGroupId = ?
            ORDER BY rgs.RotationOrder
        """, (id,))
        
        shifts = []
        for shift_row in cursor.fetchall():
            shifts.append({
                'id': shift_row['Id'],
                'code': shift_row['Code'],
                'name': shift_row['Name'],
                'colorCode': shift_row['ColorCode'],
                'rotationOrder': shift_row['RotationOrder']
            })
        
        group = {
            'id': row['Id'],
            'name': row['Name'],
            'description': row['Description'],
            'isActive': bool(row['IsActive']),
            'shifts': shifts,
            'createdAt': row['CreatedAt'],
            'createdBy': row['CreatedBy'],
            'modifiedAt': row['ModifiedAt'],
            'modifiedBy': row['ModifiedBy']
        }
        
        conn.close()
        return group
        
    except Exception as e:
        logger.error(f"Get rotation group error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Laden: {str(e)}'}, status_code=500)


@router.put('/api/rotationgroups/{id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def update_rotation_group(request: Request, id: int, data: dict = Depends(parse_json_body)):
    """Update rotation group (Admin only)"""
    try:
        name = data.get('name')
        description = data.get('description', '')
        is_active = data.get('isActive', True)
        shifts = data.get('shifts', [])  # [{shiftTypeId, rotationOrder}]
        
        if not name:
            return JSONResponse(content={'error': 'Name ist erforderlich'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if group exists
        cursor.execute("SELECT Id FROM RotationGroups WHERE Id = ?", (id,))
        if not cursor.fetchone():
            conn.close()
            return JSONResponse(content={'error': 'Rotationsgruppe nicht gefunden'}, status_code=404)
        
        # Update rotation group
        cursor.execute("""
            UPDATE RotationGroups
            SET Name = ?, Description = ?, IsActive = ?, ModifiedAt = CURRENT_TIMESTAMP, ModifiedBy = ?
            WHERE Id = ?
        """, (name, description, 1 if is_active else 0, request.session.get('user_email', 'system'), id))
        
        # Delete existing shifts
        cursor.execute("DELETE FROM RotationGroupShifts WHERE RotationGroupId = ?", (id,))
        
        # Insert new shifts
        for shift in shifts:
            cursor.execute("""
                INSERT INTO RotationGroupShifts (RotationGroupId, ShiftTypeId, RotationOrder, CreatedBy)
                VALUES (?, ?, ?, ?)
            """, (id, shift['shiftTypeId'], shift['rotationOrder'], request.session.get('user_email', 'system')))
        
        # Log audit entry
        changes = json.dumps({'name': name, 'shifts': shifts}, ensure_ascii=False)
        log_audit(conn, 'RotationGroup', id, 'Updated', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Update rotation group error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Aktualisieren: {str(e)}'}, status_code=500)


@router.delete('/api/rotationgroups/{id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def delete_rotation_group(request: Request, id: int):
    """Delete rotation group (Admin only)"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if group exists
        cursor.execute("SELECT Name FROM RotationGroups WHERE Id = ?", (id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return JSONResponse(content={'error': 'Rotationsgruppe nicht gefunden'}, status_code=404)
        
        group_name = row['Name']
        
        # Delete rotation group (cascade will delete shifts)
        cursor.execute("DELETE FROM RotationGroups WHERE Id = ?", (id,))
        
        # Log audit entry
        log_audit(conn, 'RotationGroup', id, 'Deleted', json.dumps({'name': group_name}, ensure_ascii=False), user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Delete rotation group error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Löschen: {str(e)}'}, status_code=500)

