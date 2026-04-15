"""Audit Log router: view audit entries."""
from fastapi import APIRouter, Request, Depends
from .shared import get_db, require_role, _paginate

router = APIRouter()

@router.get('/api/audit-logs', dependencies=[Depends(require_role('Admin'))])
def get_audit_logs(request: Request):
    """Get audit logs with filtering and pagination (Admin only)."""
    entity_name = request.query_params.get('entity_name', '')
    user_id = request.query_params.get('user_id', '')
    action = request.query_params.get('action', '')
    start_date = request.query_params.get('startDate', '')
    end_date = request.query_params.get('endDate', '')
    page = int(request.query_params.get('page', 1))
    limit = int(request.query_params.get('limit', 50))
    
    query = "SELECT * FROM AuditLogs WHERE 1=1"
    params = []
    
    if entity_name:
        query += " AND EntityName = ?"
        params.append(entity_name)
    if user_id:
        query += " AND UserId = ?"
        params.append(user_id)
    if action:
        query += " AND Action = ?"
        params.append(action)
    if start_date:
        query += " AND Timestamp >= ?"
        params.append(start_date)
    if end_date:
        query += " AND Timestamp <= ?"
        params.append(end_date + 'T23:59:59')
    
    query += " ORDER BY Timestamp DESC"
    
    with get_db().connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
    
    logs = [{
        'id': row['Id'],
        'timestamp': row['Timestamp'],
        'userId': row['UserId'],
        'userName': row['UserName'],
        'entityName': row['EntityName'],
        'entityId': row['EntityId'],
        'action': row['Action'],
        'changes': row['Changes'],
    } for row in rows]
    
    return _paginate(logs, page, limit)
