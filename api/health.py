"""Health check router."""
import sys
import subprocess
from pathlib import Path
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


def _get_last_merge_or_commit_iso() -> str:
    repo_root = Path(__file__).resolve().parent.parent
    commands = [
        ['git', '-C', str(repo_root), 'log', '--merges', '-1', '--format=%cI'],
        ['git', '-C', str(repo_root), 'log', '-1', '--format=%cI'],
    ]
    for command in commands:
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )
            value = result.stdout.strip()
            if result.returncode == 0 and value:
                return value
        except (FileNotFoundError, OSError, subprocess.SubprocessError):
            continue
    return 'unknown'

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
        app_version = '2.2'
    
    python_version = sys.version.split()[0]
    
    status = 'healthy' if http_status == 200 else 'unhealthy'
    return JSONResponse(content={
        'status': status,
        'db': db_status,
        'version': app_version,
        'python': python_version,
        'ortools': ortools_version,
        'last_updated': _get_last_merge_or_commit_iso(),
    }, status_code=http_status)
