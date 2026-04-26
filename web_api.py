"""
FastAPI Web API for shift planning system.
Provides REST API endpoints compatible with the existing Web UI.

Routes are organised into FastAPI routers in the api/ package.
"""

import logging
import os

from fastapi import FastAPI, Request, Depends
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api import shared as _shared
from api.shared import Database, ensure_absence_types_table, set_db, limiter, require_auth


def configure_logging(debug: bool = False):
    log_level_str = os.environ.get('LOG_LEVEL', 'DEBUG' if debug else 'INFO')
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )


def _get_or_create_secret_key(db_path: str) -> str:
    env_key = os.environ.get('FLASK_SECRET_KEY')
    if env_key:
        return env_key

    import secrets as _secrets
    logging.getLogger(__name__).warning(
        "FLASK_SECRET_KEY not set; using ephemeral key. Set FLASK_SECRET_KEY for persistent sessions."
    )
    return _secrets.token_hex(32)


def _compute_asset_versions(static_folder: str) -> dict:
    import hashlib
    versions = {}
    assets = {
        'css': os.path.join(static_folder, 'css', 'styles.css'),
        'js': os.path.join(static_folder, 'js', 'app.js'),
    }
    min_css = os.path.join(static_folder, 'css', 'styles.min.css')
    if os.path.exists(min_css):
        assets['css_min'] = min_css

    for key, path in assets.items():
        if os.path.exists(path):
            with open(path, 'rb') as f:
                versions[key] = hashlib.sha256(f.read()).hexdigest()
        else:
            versions[key] = 'unknown'
    return versions


def create_app(db_path: str = "dienstplan.db") -> FastAPI:
    """
    Create and configure FastAPI application.

    Args:
        db_path: Path to SQLite database

    Returns:
        Configured FastAPI app
    """
    configure_logging()

    app = FastAPI(title="Dienstplan API", docs_url=None, redoc_url=None)

    # Session middleware (must be added before other middleware that reads session)
    secret_key = _get_or_create_secret_key(db_path)
    app.add_middleware(
        SessionMiddleware,
        secret_key=secret_key,
        session_cookie='dienstplan_session',
        max_age=43200,  # 12 hours
        same_site='lax',
        https_only=os.environ.get('HTTPS_ENABLED', '').lower() == 'true',
    )

    # GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # CORS
    allowed_str = os.environ.get('ALLOWED_ORIGINS', '')
    allowed_origins = [o.strip() for o in allowed_str.split(',') if o.strip()] if allowed_str else []
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Custom HTTP exception handler – return {"error": ...} instead of {"detail": ...}
    from fastapi import HTTPException
    from fastapi.responses import JSONResponse

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if isinstance(exc.detail, dict):
            return JSONResponse(content=exc.detail, status_code=exc.status_code)
        return JSONResponse(content={'error': exc.detail}, status_code=exc.status_code)

    # Initialise database
    ensure_absence_types_table(db_path)
    db = Database(db_path)
    set_db(db)
    app.state.db = db

    # Compute asset versions for cache-busting
    static_folder = os.path.join(os.path.dirname(__file__), 'wwwroot')
    asset_versions = _compute_asset_versions(static_folder)
    app.state.asset_versions = asset_versions

    # Register routers
    from api.auth import router as auth_router
    from api.employees import router as employees_router
    from api.shifts import router as shifts_router
    from api.absences import router as absences_router
    from api.statistics import router as statistics_router
    from api.settings import router as settings_router
    from api.planning import router as planning_router
    from api.health import router as health_router
    from api.audit import router as audit_router

    app.include_router(auth_router)
    app.include_router(employees_router, dependencies=[Depends(require_auth)])
    app.include_router(shifts_router, dependencies=[Depends(require_auth)])
    app.include_router(absences_router, dependencies=[Depends(require_auth)])
    app.include_router(statistics_router, dependencies=[Depends(require_auth)])
    app.include_router(settings_router)
    app.include_router(planning_router, dependencies=[Depends(require_auth)])
    app.include_router(health_router)
    app.include_router(audit_router, dependencies=[Depends(require_auth)])

    # ============================================================================
    # STATIC FILES (Web UI)
    # ============================================================================

    @app.get('/')
    async def index():
        """Serve main Web UI (no-cache so users always get the latest version)."""
        index_path = os.path.join(static_folder, 'index.html')
        headers = {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
        }
        return FileResponse(index_path, headers=headers)

    @app.get('/css/styles.css')
    async def serve_styles(req: Request):
        """Serve CSS – minified in production, full version otherwise."""
        min_css_path = os.path.join(static_folder, 'css', 'styles.min.css')
        debug_mode = os.environ.get('FASTAPI_DEBUG', '').lower() == 'true'
        if not debug_mode and os.path.exists(min_css_path):
            etag = app.state.asset_versions.get('css_min', 'unknown')[:8]
            file_path = min_css_path
        else:
            etag = app.state.asset_versions.get('css', 'unknown')[:8]
            file_path = os.path.join(static_folder, 'css', 'styles.css')

        if req.headers.get('If-None-Match') == etag:
            return Response(status_code=304)

        return FileResponse(
            file_path,
            headers={
                'Cache-Control': 'public, max-age=86400, must-revalidate',
                'ETag': etag,
            },
            media_type='text/css',
        )

    @app.get('/js/app.js')
    async def serve_app_js(req: Request):
        """Serve app.js with ETag cache-busting."""
        etag = app.state.asset_versions.get('js', 'unknown')[:8]
        if req.headers.get('If-None-Match') == etag:
            return Response(status_code=304)
        js_path = os.path.join(static_folder, 'js', 'app.js')
        return FileResponse(
            js_path,
            headers={
                'Cache-Control': 'public, max-age=86400, must-revalidate',
                'ETag': etag,
            },
            media_type='application/javascript',
        )

    # Serve remaining static files
    app.mount('/', StaticFiles(directory=static_folder), name='static')

    return app


if __name__ == "__main__":
    import uvicorn
    debug_mode = os.environ.get('FASTAPI_DEBUG', '').lower() == 'true'
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level='debug' if debug_mode else 'info')
