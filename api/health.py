"""Health check router."""
import sys
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get('/api/health')
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
    return JSONResponse(content={
        'status': status,
        'db': db_status,
        'version': app_version,
        'python': python_version,
        'ortools': ortools_version,
    }, status_code=http_status)
