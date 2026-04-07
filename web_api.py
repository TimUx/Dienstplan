"""
Flask Web API for shift planning system.
Provides REST API endpoints compatible with the existing .NET Web UI.

Routes are organized into Flask Blueprints in the api/ package.
"""

import logging
import os

from flask import Flask, make_response, request
from flask_cors import CORS
from flask_compress import Compress

from api import shared as _shared
from api.shared import Database, ensure_absence_types_table


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

    import sqlite3
    import secrets as _secrets

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT Value FROM AppSettings WHERE Key = 'SecretKey'")
        row = cursor.fetchone()
        if row and row[0]:
            conn.close()
            return row[0]

        new_key = _secrets.token_hex(32)
        cursor.execute(
            "INSERT OR IGNORE INTO AppSettings (Key, Value) VALUES ('SecretKey', ?)",
            (new_key,)
        )
        conn.commit()
        conn.close()
        logging.getLogger(__name__).warning(
            "Generated new SECRET_KEY and stored in DB. Set FLASK_SECRET_KEY env var for production."
        )
        return new_key
    except Exception:
        import secrets as _secrets2
        return _secrets2.token_hex(32)


def _configure_cors(app):
    allowed_str = os.environ.get('ALLOWED_ORIGINS', '')
    if allowed_str:
        allowed_origins = [o.strip() for o in allowed_str.split(',') if o.strip()]
    else:
        allowed_origins = []

    if allowed_origins:
        CORS(app, origins=allowed_origins, supports_credentials=True)
    else:
        CORS(app, origins=[], supports_credentials=True)


def configure_session_security(app):
    from datetime import timedelta
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)
    if os.environ.get('HTTPS_ENABLED', '').lower() == 'true':
        app.config['SESSION_COOKIE_SECURE'] = True


def _compute_asset_versions(app):
    import hashlib
    versions = {}
    assets = {
        'css': os.path.join(app.static_folder, 'css', 'styles.css'),
        'js': os.path.join(app.static_folder, 'js', 'app.js'),
    }
    min_css = os.path.join(app.static_folder, 'css', 'styles.min.css')
    if os.path.exists(min_css):
        assets['css_min'] = min_css

    for key, path in assets.items():
        if os.path.exists(path):
            with open(path, 'rb') as f:
                versions[key] = hashlib.sha256(f.read()).hexdigest()
        else:
            versions[key] = 'unknown'
    app.config['asset_versions'] = versions


def create_app(db_path: str = "dienstplan.db") -> Flask:
    """
    Create and configure Flask application.

    Args:
        db_path: Path to SQLite database

    Returns:
        Configured Flask app
    """
    app = Flask(__name__, static_folder='wwwroot', static_url_path='')

    debug_mode = app.debug

    configure_logging(debug=debug_mode)

    # Configure session
    app.config['SECRET_KEY'] = _get_or_create_secret_key(db_path)
    app.config['SESSION_COOKIE_NAME'] = 'dienstplan_session'
    configure_session_security(app)

    _configure_cors(app)

    # Enable Gzip compression for all responses
    Compress(app)

    # Rate limiter – keyed by remote IP address
    _shared.limiter.init_app(app)

    # Ensure AbsenceTypes table exists (for existing databases)
    ensure_absence_types_table(db_path)

    # Store db instance in app config so blueprints can access it via get_db()
    app.config['db'] = Database(db_path)

    # Compute asset version hashes for cache-busting
    _compute_asset_versions(app)

    # Register blueprints
    from api.auth import bp as auth_bp
    from api.employees import bp as employees_bp
    from api.shifts import bp as shifts_bp
    from api.absences import bp as absences_bp
    from api.statistics import bp as statistics_bp
    from api.settings import bp as settings_bp
    from api.planning import bp as planning_bp
    from api.health import bp as health_bp
    from api.audit import bp as audit_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(shifts_bp)
    app.register_blueprint(absences_bp)
    app.register_blueprint(statistics_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(planning_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(audit_bp)

    # ============================================================================
    # STATIC FILES (Web UI)
    # ============================================================================

    @app.route('/')
    def index():
        """Serve the main web UI (no-cache so users always get the latest version)"""
        response = make_response(app.send_static_file('index.html'))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response

    @app.route('/css/styles.css')
    def serve_styles():
        """Serve styles - minified in production, full version in development"""
        min_css_path = os.path.join(app.static_folder, 'css', 'styles.min.css')
        if not app.debug and os.path.exists(min_css_path):
            response = make_response(app.send_static_file('css/styles.min.css'))
            etag = app.config.get('asset_versions', {}).get('css_min', 'unknown')[:8]
        else:
            response = make_response(app.send_static_file('css/styles.css'))
            etag = app.config.get('asset_versions', {}).get('css', 'unknown')[:8]

        if_none_match = request.headers.get('If-None-Match', '')
        if if_none_match == etag:
            return make_response('', 304)

        response.headers['Cache-Control'] = 'public, max-age=86400, must-revalidate'
        response.headers['ETag'] = etag
        return response

    @app.route('/js/app.js')
    def serve_app_js():
        """Serve app.js with cache-busting via ETag"""
        etag = app.config.get('asset_versions', {}).get('js', 'unknown')[:8]
        if_none_match = request.headers.get('If-None-Match', '')
        if if_none_match == etag:
            return make_response('', 304)
        response = make_response(app.send_static_file('js/app.js'))
        response.headers['Cache-Control'] = 'public, max-age=86400, must-revalidate'
        response.headers['ETag'] = etag
        return response

    return app


if __name__ == "__main__":
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app = create_app()
    app.run(debug=debug_mode, port=5000)
