"""Audit Log Blueprint: view audit entries."""
from flask import Blueprint, jsonify, request
from .shared import get_db, require_role, _paginate

bp = Blueprint('audit', __name__)

@bp.route('/api/audit-logs', methods=['GET'])
@require_role('Admin')
def get_audit_logs():
    """Get audit logs with filtering and pagination (Admin only)."""
    entity_name = request.args.get('entity_name', '')
    user_id = request.args.get('user_id', '')
    action = request.args.get('action', '')
    start_date = request.args.get('startDate', '')
    end_date = request.args.get('endDate', '')
    page = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 50))
    
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
    
    return jsonify(_paginate(logs, page, limit))
