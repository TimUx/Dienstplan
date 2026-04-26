"""
Shared utilities for the Dienstplan API blueprints.

Contains: Database class, dependencies, helper functions, rate limiter.
"""

import logging
import sqlite3
import json
import hashlib
import bcrypt
import secrets
import sys
from contextlib import contextmanager
from functools import wraps
from datetime import datetime, date, timedelta
from typing import Optional, Dict

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# Module-level rate limiter – attached to app in create_app()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per minute", "2000 per hour"])

# Module-level DB instance set by create_app()
_db_instance: Optional["Database"] = None


# ============================================================================
# CSRF PROTECTION
# ============================================================================

def generate_csrf_token(request: Request) -> str:
    if 'csrf_token' not in request.session:
        request.session['csrf_token'] = secrets.token_hex(32)
    return request.session['csrf_token']


def validate_csrf_token(request: Request, token: str) -> bool:
    return bool(token and token == request.session.get('csrf_token'))


async def check_csrf(request: Request):
    """FastAPI dependency – blocks request if CSRF token is missing or invalid."""
    token = request.headers.get('X-CSRF-Token') or (await request.form()).get('csrf_token')
    if not validate_csrf_token(request, token):
        raise HTTPException(status_code=403, detail={'error': 'CSRF token invalid or missing'})

# Keep old name as alias for backwards compatibility
require_csrf = check_csrf


def get_row_value(row: sqlite3.Row, key: str, default):
    """
    Helper to safely get value from sqlite3.Row with default.
    
    sqlite3.Row objects don't have a .get() method like dictionaries.
    This helper provides similar functionality with proper error handling.
    
    Args:
        row: sqlite3.Row object
        key: Column name
        default: Default value if key doesn't exist or value is None
        
    Returns:
        Value from row or default
    """
    try:
        val = row[key]
        return val if val is not None else default
    except (KeyError, IndexError):
        return default


class Database:
    """Database connection helper"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def connection(self):
        """Context manager for database connection - auto-closes on exit."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()


def get_db() -> "Database":
    """Return the global Database instance configured at startup."""
    if _db_instance is None:
        raise RuntimeError("Database not initialised. Call set_db() first.")
    return _db_instance


def set_db(db: "Database") -> None:
    """Set the global Database instance (called from create_app)."""
    global _db_instance
    _db_instance = db


def hash_password(password: str) -> str:
    """Hash password using bcrypt with automatic salting."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify password against hash.

    Supports both bcrypt hashes (new) and legacy SHA256 hashes (old) so
    that existing accounts keep working until their password is changed via
    the normal account-management flow.
    """
    if password_hash.startswith('$2b$') or password_hash.startswith('$2a$'):
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    # Legacy path: compare against SHA256 hash stored before bcrypt migration.
    # This path is only reached for accounts whose passwords pre-date the
    # migration; the next password change will store a bcrypt hash instead.
    legacy_hash = hashlib.sha256(password.encode()).hexdigest()  # nosec B324
    return legacy_hash == password_hash


def _paginate(items: list, page: int, limit: int) -> dict:
    """
    Return a pagination envelope for *items*.

    Args:
        items: Full list of items.
        page:  1-based page number.
        limit: Items per page.  0 means "return all" (no pagination applied).

    Returns:
        Dict with keys: data, total, page, limit, totalPages.
    """
    total = len(items)
    if limit > 0:
        offset = (page - 1) * limit
        data = items[offset:offset + limit]
        total_pages = (total + limit - 1) // limit
    else:
        data = items
        total_pages = 1
    return {
        'data': data,
        'total': total,
        'page': page,
        'limit': limit,
        'totalPages': total_pages,
    }


def get_absence_type_defaults() -> dict:
    """Legacy absence type fallback values. Kept for backward compatibility only."""
    return {
        1: {'id': 1, 'name': 'Krank / AU', 'code': 'AU', 'colorCode': '#FFB6C1'},
        2: {'id': 2, 'name': 'Urlaub', 'code': 'U', 'colorCode': '#90EE90'},
        3: {'id': 3, 'name': 'Lehrgang', 'code': 'L', 'colorCode': '#87CEEB'},
    }


def get_employee_by_email(db: Database, email: str) -> Optional[Dict]:
    """Get employee by email (employees now include authentication data)"""
    with db.connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT e.*, GROUP_CONCAT(r.Name) as roles
            FROM Employees e
            LEFT JOIN AspNetUserRoles ur ON CAST(e.Id AS TEXT) = ur.UserId
            LEFT JOIN AspNetRoles r ON ur.RoleId = r.Id
            WHERE e.Email = ?
            GROUP BY e.Id
        """, (email,))
        row = cursor.fetchone()

    if not row:
        return None

    full_name = f"{row['Vorname']} {row['Name']}"

    return {
        'id': row['Id'],
        'email': row['Email'],
        'passwordHash': row['PasswordHash'],
        'fullName': full_name,
        'vorname': row['Vorname'],
        'name': row['Name'],
        'personalnummer': row['Personalnummer'],
        'lockoutEnd': row['LockoutEnd'],
        'accessFailedCount': row['AccessFailedCount'],
        'roles': row['roles'].split(',') if row['roles'] else []
    }


def require_auth(request: Request):
    """FastAPI dependency – requires authenticated session."""
    if 'user_id' not in request.session:
        raise HTTPException(status_code=401, detail={'error': 'Authentication required'})


def require_role(*required_roles: str):
    """Factory that returns a FastAPI dependency checking for specific role(s)."""
    def _check(request: Request):
        if 'user_id' not in request.session:
            raise HTTPException(status_code=401, detail={'error': 'Authentication required'})

        user_roles = request.session.get('user_roles')
        if not user_roles:
            try:
                db = get_db()
                with db.connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """SELECT GROUP_CONCAT(r.Name) as roles
                           FROM AspNetUserRoles ur
                           JOIN AspNetRoles r ON ur.RoleId = r.Id
                           WHERE ur.UserId = ?""",
                        (str(request.session['user_id']),)
                    )
                    row = cursor.fetchone()
                user_roles = row['roles'].split(',') if row and row['roles'] else []
                request.session['user_roles'] = user_roles
            except Exception as e:
                logger.warning(f"Could not refresh user roles from DB: {e}")
                user_roles = []

        if not any(role in user_roles for role in required_roles):
            raise HTTPException(status_code=403, detail={'error': 'Insufficient permissions'})

    return _check


def log_audit(conn, entity_name: str, entity_id: str, action: str, changes: Optional[str] = None, 
              user_id: Optional[str] = None, user_name: Optional[str] = None):
    """
    Log an audit entry to the AuditLogs table.
    
    Args:
        conn: Database connection (must be already opened)
        entity_name: Name of the entity (e.g., 'Employee', 'Team', 'ShiftAssignment', 'Absence')
        entity_id: ID of the entity being modified
        action: Action performed (e.g., 'Create', 'Update', 'Delete')
        changes: Optional JSON string with details of changes
        user_id: User ID performing the action
        user_name: User name/email performing the action
    
    Note: Audit logging failures are logged but do not prevent the main operation from succeeding.
    """
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO AuditLogs (Timestamp, UserId, UserName, EntityName, EntityId, Action, Changes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            user_id,
            user_name,
            entity_name,
            str(entity_id),
            action,
            changes
        ))
    except Exception as e:
        logger.warning(f"Failed to log audit entry: {e}")


def extend_planning_dates_to_complete_weeks(start_date: date, end_date: date) -> tuple:
    """
    Extend planning dates to complete weeks (Sunday-Saturday).
    
    This ensures shift planning always happens in complete weeks to maintain proper
    rotation patterns across week boundaries, especially important for team-based
    rotation systems.
    
    Example: January 2026 (Thu Jan 1 - Sat Jan 31)
    - Extended: Sun Dec 28, 2025 - Sat Jan 31, 2026 (exactly 5 complete weeks)
    
    Args:
        start_date: Original start date (first day of month)
        end_date: Original end date (last day of month)
    
    Returns:
        Tuple of (extended_start_date, extended_end_date) with complete weeks
    """
    # Extend START backwards to previous Sunday if not already Sunday
    # weekday() returns: 0=Monday, 1=Tuesday, ..., 6=Sunday
    extended_start = start_date
    if start_date.weekday() != 6:  # Not Sunday
        # Monday=0 -> go back 1 day, Tuesday=1 -> go back 2 days, ..., Saturday=5 -> go back 6 days
        days_since_sunday = start_date.weekday() + 1
        extended_start = start_date - timedelta(days=days_since_sunday)
    
    # Extend END forward to next Saturday if not already Saturday
    extended_end = end_date
    if end_date.weekday() != 5:  # Not Saturday
        # Sunday=6 -> go forward 6 days, Monday=0 -> go forward 5 days, ..., Friday=4 -> go forward 1 day
        days_until_saturday = (5 - end_date.weekday() + 7) % 7
        extended_end = end_date + timedelta(days=days_until_saturday)
    
    return extended_start, extended_end


def validate_monthly_date_range(start_date: date, end_date: date) -> tuple:
    """
    Validate that the date range covers exactly one complete month.
    
    NOTE: The actual planning period will be extended to complete weeks
    (Sunday to Saturday) which may include days from adjacent months.
    
    Args:
        start_date: Start date of the range (first day of month)
        end_date: End date of the range (last day of month)
    
    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty string.
    """
    # Validate that the date range is within a single month
    if start_date.year != end_date.year or start_date.month != end_date.month:
        return False, 'Shift planning is only allowed for a single month. Year-based planning has been removed.'
    
    # Validate that the date range covers the entire month
    # First day of month
    first_day = date(start_date.year, start_date.month, 1)
    # Last day of month
    if start_date.month == 12:
        last_day = date(start_date.year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(start_date.year, start_date.month + 1, 1) - timedelta(days=1)
    
    if start_date != first_day or end_date != last_day:
        return False, f'Planning must cover the entire month. Expected: {first_day.isoformat()} to {last_day.isoformat()}'
    
    return True, ''


async def parse_json_body(request: Request) -> dict:
    """FastAPI dependency – parse JSON request body (works with sync handlers)."""
    try:
        return await request.json()
    except Exception:
        return {}


def ensure_absence_types_table(db_path: str):
    """
    Ensure the AbsenceTypes table exists and is populated with default values.
    This is called at app startup to handle existing databases that may not have this table.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    cursor = conn.cursor()
    
    try:
        cursor.execute("BEGIN IMMEDIATE")
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='AbsenceTypes'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            logger.info("Creating AbsenceTypes table...")
            cursor.execute("""
                CREATE TABLE AbsenceTypes (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    Name TEXT NOT NULL,
                    Code TEXT NOT NULL UNIQUE,
                    ColorCode TEXT NOT NULL DEFAULT '#E0E0E0',
                    IsSystemType INTEGER NOT NULL DEFAULT 0,
                    CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    CreatedBy TEXT,
                    ModifiedAt TEXT,
                    ModifiedBy TEXT
                )
            """)
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='Absences'")
            absences_exists = cursor.fetchone() is not None
            if absences_exists:
                cursor.execute("PRAGMA table_info(Absences)")
                columns = [col[1] for col in cursor.fetchall()]
                if 'AbsenceTypeId' not in columns:
                    logger.info("Adding AbsenceTypeId column to Absences table...")
                    cursor.execute("ALTER TABLE Absences ADD COLUMN AbsenceTypeId INTEGER")
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_absences_type 
                        ON Absences(AbsenceTypeId)
                    """)
            
            logger.info("AbsenceTypes table created")
        
        standard_types = [
            ('Urlaub', 'U', '#90EE90', 1),
            ('Krank / AU', 'AU', '#FFB6C1', 1),
            ('Lehrgang', 'L', '#87CEEB', 1)
        ]
        
        cursor.execute("SELECT COUNT(*) FROM AbsenceTypes WHERE Code IN ('U', 'AU', 'L') AND IsSystemType = 1")
        existing_standard_count = cursor.fetchone()[0]
        
        if existing_standard_count < len(standard_types):
            logger.info("Initializing default absence types...")
            
            cursor.executemany("""
                INSERT OR IGNORE INTO AbsenceTypes (Name, Code, ColorCode, IsSystemType, CreatedBy)
                VALUES (?, ?, ?, ?, 'system')
            """, standard_types)
            
            logger.info("Default absence types initialized (U, AU, L)")
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error ensuring AbsenceTypes table: {e}")
        logger.error("Possible causes: database permissions, disk space, or database corruption")
        logger.error("Please check database file permissions and disk space")
        raise
    finally:
        conn.close()
