"""Health check Blueprint."""
from flask import Blueprint, jsonify
import sys

bp = Blueprint('health', __name__)

@bp.route('/api/health', methods=['GET'])
def health_check():
    from .shared import get_db
    try:
        db = get_db()
        with db.connection() as conn:
            conn.execute('SELECT 1')
        db_status = 'ok'
        http_status = 200
    except Exception as e:
        db_status = f'error: {str(e)}'
        http_status = 503
    
    try:
        import importlib.metadata
        ortools_version = importlib.metadata.version('ortools')
    except Exception:
        ortools_version = 'unknown'
    
    try:
        import importlib.metadata
        app_version = importlib.metadata.version('dienstplan') 
    except Exception:
        app_version = '2.1'
    
    python_version = sys.version.split()[0]
    
    status = 'healthy' if http_status == 200 else 'unhealthy'
    return jsonify({
        'status': status,
        'db': db_status,
        'version': app_version,
        'python': python_version,
        'ortools': ortools_version,
    }), http_status
