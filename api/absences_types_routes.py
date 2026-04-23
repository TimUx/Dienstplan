"""Absence types API routes."""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from .shared import get_db, require_role, log_audit, check_csrf, parse_json_body

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get('/api/absencetypes')
def get_absence_types(request: Request):
    """Get all absence types (system and custom)"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT Id, Name, Code, ColorCode, IsSystemType, CreatedAt, CreatedBy, ModifiedAt, ModifiedBy
        FROM AbsenceTypes
        ORDER BY IsSystemType DESC, Name ASC
    """)
    
    absence_types = []
    for row in cursor.fetchall():
        absence_types.append({
            'id': row['Id'],
            'name': row['Name'],
            'code': row['Code'],
            'colorCode': row['ColorCode'],
            'isSystemType': bool(row['IsSystemType']),
            'createdAt': row['CreatedAt'],
            'createdBy': row['CreatedBy'],
            'modifiedAt': row['ModifiedAt'],
            'modifiedBy': row['ModifiedBy']
        })
    
    conn.close()
    return absence_types


@router.post('/api/absencetypes', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def create_absence_type(request: Request, data: dict = Depends(parse_json_body)):
    """Create new custom absence type (Admin only)"""
    try:
        if not data.get('name') or not data.get('code'):
            return JSONResponse(content={'error': 'Name und Code sind erforderlich'}, status_code=400)
        
        # Validate code doesn't conflict with system types
        code = data.get('code').upper()
        if code in ['U', 'AU', 'L']:
            return JSONResponse(content={'error': 'Code U, AU und L sind für Systemtypen reserviert'}, status_code=400)
        
        # Set default color if not provided
        color_code = data.get('colorCode', '#E0E0E0')
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if code already exists
        cursor.execute("SELECT Id FROM AbsenceTypes WHERE Code = ?", (code,))
        if cursor.fetchone():
            conn.close()
            return JSONResponse(content={'error': f'Ein Abwesenheitstyp mit dem Kürzel "{code}" existiert bereits'}, status_code=400)
        
        cursor.execute("""
            INSERT INTO AbsenceTypes 
            (Name, Code, ColorCode, IsSystemType, CreatedAt, CreatedBy)
            VALUES (?, ?, ?, 0, ?, ?)
        """, (
            data.get('name'),
            code,
            color_code,
            datetime.utcnow().isoformat(),
            request.session.get('user_email')
        ))
        
        absence_type_id = cursor.lastrowid
        
        # Log audit entry
        changes = json.dumps({
            'name': data.get('name'),
            'code': code,
            'colorCode': color_code
        }, ensure_ascii=False)
        log_audit(conn, 'AbsenceType', absence_type_id, 'Created', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return JSONResponse(content={'success': True, 'id': absence_type_id}, status_code=201)
        
    except Exception as e:
        logger.error(f"Create absence type error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Erstellen: {str(e)}'}, status_code=500)


@router.put('/api/absencetypes/{id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def update_absence_type(request: Request, id: int, data: dict = Depends(parse_json_body)):
    """Update custom absence type (Admin only)"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if absence type exists and is not a system type
        cursor.execute("SELECT IsSystemType, Code FROM AbsenceTypes WHERE Id = ?", (id,))
        type_row = cursor.fetchone()
        
        if not type_row:
            conn.close()
            return JSONResponse(content={'error': 'Abwesenheitstyp nicht gefunden'}, status_code=404)
        
        if type_row['IsSystemType']:
            conn.close()
            return JSONResponse(content={'error': 'Systemtypen (U, AU, L) können nicht geändert werden'}, status_code=400)
        
        # Build update query dynamically based on provided fields
        update_fields = []
        params = []
        
        if data.get('name'):
            update_fields.append("Name = ?")
            params.append(data.get('name'))
        
        if data.get('code'):
            new_code = data.get('code').upper()
            if new_code in ['U', 'AU', 'L']:
                conn.close()
                return JSONResponse(content={'error': 'Code U, AU und L sind für Systemtypen reserviert'}, status_code=400)
            
            # Check if code already exists for a different type
            cursor.execute("SELECT Id FROM AbsenceTypes WHERE Code = ? AND Id != ?", (new_code, id))
            if cursor.fetchone():
                conn.close()
                return JSONResponse(content={'error': f'Ein Abwesenheitstyp mit dem Kürzel "{new_code}" existiert bereits'}, status_code=400)
            
            update_fields.append("Code = ?")
            params.append(new_code)
        
        if data.get('colorCode'):
            update_fields.append("ColorCode = ?")
            params.append(data.get('colorCode'))
        
        if not update_fields:
            conn.close()
            return JSONResponse(content={'error': 'Keine Felder zum Aktualisieren'}, status_code=400)
        
        update_fields.append("ModifiedAt = ?")
        params.append(datetime.utcnow().isoformat())
        
        update_fields.append("ModifiedBy = ?")
        params.append(request.session.get('user_email'))
        
        params.append(id)
        
        cursor.execute(f"""
            UPDATE AbsenceTypes 
            SET {', '.join(update_fields)}
            WHERE Id = ?
        """, params)
        
        # Log audit entry
        log_audit(conn, 'AbsenceType', id, 'Updated', json.dumps(data, ensure_ascii=False), user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Update absence type error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Aktualisieren: {str(e)}'}, status_code=500)


@router.delete('/api/absencetypes/{id}', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def delete_absence_type(request: Request, id: int):
    """Delete custom absence type (Admin only)"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if absence type exists and is not a system type
        cursor.execute("SELECT IsSystemType, Code, Name FROM AbsenceTypes WHERE Id = ?", (id,))
        type_row = cursor.fetchone()
        
        if not type_row:
            conn.close()
            return JSONResponse(content={'error': 'Abwesenheitstyp nicht gefunden'}, status_code=404)
        
        if type_row['IsSystemType']:
            conn.close()
            return JSONResponse(content={'error': 'Systemtypen (U, AU, L) können nicht gelöscht werden'}, status_code=400)
        
        # Check if any absences use this type
        cursor.execute("SELECT COUNT(*) FROM Absences WHERE AbsenceTypeId = ?", (id,))
        usage_count = cursor.fetchone()[0]
        
        if usage_count > 0:
            conn.close()
            return JSONResponse(content={
                'error': f'Dieser Abwesenheitstyp kann nicht gelöscht werden, da er von {usage_count} Abwesenheit(en) verwendet wird'
            }, status_code=400)
        
        cursor.execute("DELETE FROM AbsenceTypes WHERE Id = ?", (id,))
        
        # Log audit entry
        changes = json.dumps({
            'code': type_row['Code'],
            'name': type_row['Name']
        }, ensure_ascii=False)
        log_audit(conn, 'AbsenceType', id, 'Deleted', changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"Delete absence type error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Löschen: {str(e)}'}, status_code=500)

