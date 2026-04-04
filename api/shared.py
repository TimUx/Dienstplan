"""
Shared utilities for the Dienstplan API blueprints.

Contains: Database class, decorators, helper functions, rate limiter.
"""

from flask import jsonify, session, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime, date, timedelta
from typing import Optional, Dict
import sqlite3
import json
import hashlib
import bcrypt
import secrets
import sys
from functools import wraps


# Module-level limiter (init_app called in create_app)
limiter = Limiter(get_remote_address, default_limits=[], storage_uri="memory://")


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
        conn.row_factory = sqlite3.Row
        return conn


def get_db() -> Database:
    """Get the Database instance from the current app config."""
    return current_app.config['db']


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


def get_employee_by_email(db: Database, email: str) -> Optional[Dict]:
    """Get employee by email (employees now include authentication data)"""
    conn = db.get_connection()
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
    conn.close()
    
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


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def require_role(*required_roles):
    """Decorator to require specific role(s)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'Authentication required'}), 401
            
            user_roles = session.get('user_roles', [])
            if not any(role in user_roles for role in required_roles):
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


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
        user_id: Optional user ID (will try to get from session if not provided)
        user_name: Optional user name (will try to get from session if not provided)
    
    Note: Audit logging failures are logged but do not prevent the main operation from succeeding.
    """
    try:
        cursor = conn.cursor()
        
        # Get user info from session if not provided
        if user_id is None:
            user_id = session.get('user_id')
        if user_name is None:
            user_name = session.get('user_email')
        
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
        # Log the audit failure but don't raise - we don't want audit logging to break business operations
        print(f"Warning: Failed to log audit entry: {e}", file=sys.stderr)


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


def ensure_absence_types_table(db_path: str):
    """
    Ensure the AbsenceTypes table exists and is populated with default values.
    This is called at app startup to handle existing databases that may not have this table.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("BEGIN IMMEDIATE")
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='AbsenceTypes'")
        table_exists = cursor.fetchone() is not None
        
        if not table_exists:
            print("[i] Creating AbsenceTypes table...")
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
            
            cursor.execute("PRAGMA table_info(Absences)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'AbsenceTypeId' not in columns:
                print("[i] Adding AbsenceTypeId column to Absences table...")
                cursor.execute("ALTER TABLE Absences ADD COLUMN AbsenceTypeId INTEGER")
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_absences_type 
                    ON Absences(AbsenceTypeId)
                """)
            
            print("[✓] AbsenceTypes table created")
        
        standard_types = [
            ('Urlaub', 'U', '#90EE90', 1),
            ('Krank / AU', 'AU', '#FFB6C1', 1),
            ('Lehrgang', 'L', '#87CEEB', 1)
        ]
        
        cursor.execute("SELECT COUNT(*) FROM AbsenceTypes WHERE Code IN ('U', 'AU', 'L') AND IsSystemType = 1")
        existing_standard_count = cursor.fetchone()[0]
        
        if existing_standard_count < len(standard_types):
            print("[i] Initializing default absence types...")
            
            cursor.executemany("""
                INSERT OR IGNORE INTO AbsenceTypes (Name, Code, ColorCode, IsSystemType, CreatedBy)
                VALUES (?, ?, ?, ?, 'system')
            """, standard_types)
            
            print("[✓] Default absence types initialized (U, AU, L)")
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[!] Error ensuring AbsenceTypes table: {e}", file=sys.stderr)
        print("[!] Possible causes: database permissions, disk space, or database corruption", file=sys.stderr)
        print("[!] Please check database file permissions and disk space", file=sys.stderr)
        raise
    finally:
        conn.close()
