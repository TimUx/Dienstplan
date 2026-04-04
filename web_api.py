"""
Flask Web API for shift planning system.
Provides REST API endpoints compatible with the existing .NET Web UI.

Routes are organized into Flask Blueprints in the api/ package.
"""

from flask import Flask, make_response
from flask_cors import CORS
from flask_compress import Compress

from api import shared as _shared
from api.shared import Database, ensure_absence_types_table


def create_app(db_path: str = "dienstplan.db") -> Flask:
    """
    Create and configure Flask application.

    Args:
        db_path: Path to SQLite database

    Returns:
        Configured Flask app
    """
    app = Flask(__name__, static_folder='wwwroot', static_url_path='')

    # Configure session
    import os
    app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SESSION_COOKIE_NAME'] = 'dienstplan_session'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    CORS(app, supports_credentials=True)

    # Enable Gzip compression for all responses
    Compress(app)

    # Rate limiter – keyed by remote IP address
    _shared.limiter.init_app(app)

    # Ensure AbsenceTypes table exists (for existing databases)
    ensure_absence_types_table(db_path)

    # Store db instance in app config so blueprints can access it via get_db()
    app.config['db'] = Database(db_path)

    # Register blueprints
    from api.auth import bp as auth_bp
    from api.employees import bp as employees_bp
    from api.shifts import bp as shifts_bp
    from api.absences import bp as absences_bp
    from api.statistics import bp as statistics_bp
    from api.settings import bp as settings_bp
    from api.planning import bp as planning_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(shifts_bp)
    app.register_blueprint(absences_bp)
    app.register_blueprint(statistics_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(planning_bp)

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
        """Serve styles with long-term caching"""
        response = make_response(app.send_static_file('css/styles.css'))
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        return response

    @app.route('/js/app.js')
    def serve_app_js():
        """Serve app.js with long-term caching"""
        response = make_response(app.send_static_file('js/app.js'))
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
        return response

    return app


if __name__ == "__main__":
    import os
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    app = create_app()
    app.run(debug=debug_mode, port=5000)
