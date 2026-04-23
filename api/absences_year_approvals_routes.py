"""Vacation year approvals API routes."""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from .shared import get_db, require_role, log_audit, check_csrf, parse_json_body

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get('/api/vacationyearapprovals')
def get_vacation_year_approvals(request: Request):
    """Get all vacation year approvals"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM VacationYearApprovals
        ORDER BY Year DESC
    """)
    
    approvals = []
    for row in cursor.fetchall():
        approvals.append({
            'id': row['Id'],
            'year': row['Year'],
            'isApproved': bool(row['IsApproved']),
            'approvedAt': row['ApprovedAt'],
            'approvedBy': row['ApprovedBy'],
            'createdAt': row['CreatedAt'],
            'modifiedAt': row['ModifiedAt'],
            'notes': row['Notes']
        })
    
    conn.close()
    return approvals


@router.get('/api/vacationyearapprovals/{year}')
def get_vacation_year_approval(request: Request, year: int):
    """Get vacation year approval status for a specific year"""
    db = get_db()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM VacationYearApprovals WHERE Year = ?
    """, (year,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {
            'year': year,
            'isApproved': False,
            'exists': False
        }
    
    return {
        'id': row['Id'],
        'year': row['Year'],
        'isApproved': bool(row['IsApproved']),
        'approvedAt': row['ApprovedAt'],
        'approvedBy': row['ApprovedBy'],
        'createdAt': row['CreatedAt'],
        'modifiedAt': row['ModifiedAt'],
        'notes': row['Notes'],
        'exists': True
    }


@router.post('/api/vacationyearapprovals', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def create_or_update_vacation_year_approval(request: Request, data: dict = Depends(parse_json_body)):
    """Create or update vacation year approval (Admin only)"""
    try:
        year = data.get('year')
        is_approved = data.get('isApproved', False)
        notes = data.get('notes')
        
        if not year:
            return JSONResponse(content={'error': 'Jahr ist erforderlich'}, status_code=400)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if entry exists
        cursor.execute("""
            SELECT Id FROM VacationYearApprovals WHERE Year = ?
        """, (year,))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing entry
            cursor.execute("""
                UPDATE VacationYearApprovals 
                SET IsApproved = ?,
                    ApprovedAt = ?,
                    ApprovedBy = ?,
                    ModifiedAt = ?,
                    Notes = ?
                WHERE Year = ?
            """, (
                1 if is_approved else 0,
                datetime.utcnow().isoformat() if is_approved else None,
                request.session.get('user_email') if is_approved else None,
                datetime.utcnow().isoformat(),
                notes,
                year
            ))
            
            approval_id = existing['Id']
            action = 'Updated'
        else:
            # Create new entry
            cursor.execute("""
                INSERT INTO VacationYearApprovals 
                (Year, IsApproved, ApprovedAt, ApprovedBy, CreatedAt, Notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                year,
                1 if is_approved else 0,
                datetime.utcnow().isoformat() if is_approved else None,
                request.session.get('user_email') if is_approved else None,
                datetime.utcnow().isoformat(),
                notes
            ))
            
            approval_id = cursor.lastrowid
            action = 'Created'
        
        # Log audit entry
        changes = json.dumps({
            'year': year,
            'isApproved': is_approved,
            'notes': notes
        }, ensure_ascii=False)
        log_audit(conn, 'VacationYearApproval', approval_id, action, changes, user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))
        
        conn.commit()
        conn.close()
        
        return JSONResponse(content={'success': True, 'id': approval_id, 'year': year}, status_code=201)
        
    except Exception as e:
        logger.error(f"Create/update vacation year approval error: {str(e)}")
        return JSONResponse(content={'error': f'Fehler beim Speichern: {str(e)}'}, status_code=500)

