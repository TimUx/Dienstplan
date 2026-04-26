"""
Settings APIRouter: global settings, email settings.
"""

from fastapi import APIRouter, Request, Depends, UploadFile, File
from fastapi.responses import JSONResponse, Response
from datetime import datetime
import json
import logging
import os

from .shared import get_db, require_auth, require_role, log_audit, require_csrf, check_csrf, parse_json_body
from .error_utils import api_error

logger = logging.getLogger(__name__)

router = APIRouter()
DEFAULT_COMPANY_NAME = 'Fritz Winter Eisengießerei GmbH & Co. KG'
DEFAULT_HEADER_LOGO_URL = '/images/fw-logo-white.svg'


def _ensure_app_settings_table(cursor) -> None:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS AppSettings (
            Key TEXT PRIMARY KEY,
            Value TEXT,
            ModifiedAt TEXT,
            ModifiedBy TEXT
        )
    """)


def _get_app_setting(cursor, key: str, fallback: str) -> str:
    cursor.execute("SELECT Value FROM AppSettings WHERE Key = ?", (key,))
    row = cursor.fetchone()
    if row and row[0] is not None:
        return row[0]
    return fallback


def _upsert_app_setting(cursor, key: str, value: str, modified_by: str) -> None:
    cursor.execute("""
        INSERT INTO AppSettings (Key, Value, ModifiedAt, ModifiedBy)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(Key) DO UPDATE SET
            Value = excluded.Value,
            ModifiedAt = excluded.ModifiedAt,
            ModifiedBy = excluded.ModifiedBy
    """, (key, value, datetime.utcnow().isoformat(), modified_by))


@router.get('/api/settings/global', dependencies=[Depends(require_auth)])
def get_global_settings(request: Request):
    """Get global shift planning settings"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM GlobalSettings WHERE Id = 1")
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            # Return defaults if not found
            return {
                'maxConsecutiveShifts': 6,
                'maxConsecutiveNightShifts': 3,
                'minRestHoursBetweenShifts': 11
            }
        
        return {
            'maxConsecutiveShifts': row['MaxConsecutiveShifts'],
            'maxConsecutiveNightShifts': row['MaxConsecutiveNightShifts'],
            'minRestHoursBetweenShifts': row['MinRestHoursBetweenShifts'],
            'modifiedAt': row['ModifiedAt'],
            'modifiedBy': row['ModifiedBy']
        }
        
    except Exception as e:
        return api_error(
            logger,
            'Fehler beim Laden der globalen Einstellungen',
            status_code=500,
            exc=e,
            context='get_global_settings',
        )


@router.put('/api/settings/global', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def update_global_settings(request: Request, data: dict = Depends(parse_json_body)):
    """Update global shift planning settings (Admin only)"""
    try:
        
        # Note: maxConsecutiveShifts and maxConsecutiveNightShifts are deprecated
        # These settings are now configured per shift type in the ShiftTypes table
        # We keep them in the database for backward compatibility but don't expose them in the UI
        
        db = get_db()
        conn = db.get_connection()
        try:
            cursor = conn.cursor()

            # Load existing values for deprecated fields
            cursor.execute("SELECT MaxConsecutiveShifts, MaxConsecutiveNightShifts FROM GlobalSettings WHERE Id = 1")
            existing = cursor.fetchone()

            # Use existing values for deprecated fields, or defaults if not found
            max_consecutive_shifts = existing['MaxConsecutiveShifts'] if existing else 6
            max_consecutive_night_shifts = existing['MaxConsecutiveNightShifts'] if existing else 3

            # Only update minRestHoursBetweenShifts from the request
            min_rest_hours = data.get('minRestHoursBetweenShifts', 11)

            # Validation
            if min_rest_hours < 8 or min_rest_hours > 24:
                return JSONResponse(content={'error': 'Mindest-Ruhezeit muss zwischen 8 und 24 Stunden liegen'}, status_code=400)

            # Update or insert settings (keeping deprecated fields as-is)
            cursor.execute("""
                INSERT INTO GlobalSettings
                (Id, MaxConsecutiveShifts, MaxConsecutiveNightShifts, MinRestHoursBetweenShifts, ModifiedAt, ModifiedBy)
                VALUES (1, ?, ?, ?, ?, ?)
                ON CONFLICT(Id) DO UPDATE SET
                    MinRestHoursBetweenShifts = excluded.MinRestHoursBetweenShifts,
                    ModifiedAt = excluded.ModifiedAt,
                    ModifiedBy = excluded.ModifiedBy
            """, (
                max_consecutive_shifts,
                max_consecutive_night_shifts,
                min_rest_hours,
                datetime.utcnow().isoformat(),
                request.session.get('user_email', 'system')
            ))

            # Log audit entry
            changes = json.dumps({'minRestHoursBetweenShifts': min_rest_hours}, ensure_ascii=False)
            log_audit(conn, 'GlobalSettings', 1, 'Updated', changes,
                      user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))

            conn.commit()
            return {'success': True}
        finally:
            conn.close()
        
    except Exception as e:
        return api_error(
            logger,
            'Fehler beim Aktualisieren der globalen Einstellungen',
            status_code=500,
            exc=e,
            context='update_global_settings',
        )


@router.get('/api/settings/branding')
def get_branding_settings(request: Request):
    """Get public branding settings (logo + footer company name)."""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        _ensure_app_settings_table(cursor)

        company_name = _get_app_setting(cursor, 'CompanyNameFooter', DEFAULT_COMPANY_NAME)
        logo_url = _get_app_setting(cursor, 'HeaderLogoUrl', DEFAULT_HEADER_LOGO_URL)

        cursor.execute("SELECT ModifiedAt FROM AppSettings WHERE Key = 'HeaderLogoUrl'")
        logo_row = cursor.fetchone()

        conn.commit()
        conn.close()

        return {
            'companyName': company_name,
            'headerLogoUrl': logo_url,
            'logoModifiedAt': logo_row[0] if logo_row and logo_row[0] else None,
        }
    except Exception as e:
        return api_error(
            logger,
            'Fehler beim Laden der Branding-Einstellungen',
            status_code=500,
            exc=e,
            context='get_branding_settings',
        )


@router.put('/api/settings/branding', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def update_branding_settings(request: Request, data: dict = Depends(parse_json_body)):
    """Update branding text settings (Admin only)."""
    try:
        company_name = (data.get('companyName') or '').strip()
        if not company_name:
            return JSONResponse(content={'error': 'Firmenname darf nicht leer sein'}, status_code=400)
        if len(company_name) > 200:
            return JSONResponse(content={'error': 'Firmenname darf maximal 200 Zeichen haben'}, status_code=400)

        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        _ensure_app_settings_table(cursor)

        modified_by = request.session.get('user_email', 'system')
        _upsert_app_setting(cursor, 'CompanyNameFooter', company_name, modified_by)

        changes = json.dumps({'companyName': company_name}, ensure_ascii=False)
        log_audit(conn, 'BrandingSettings', 'CompanyNameFooter', 'Updated', changes,
                  user_id=request.session.get('user_id'), user_name=modified_by)

        conn.commit()
        conn.close()
        return {'success': True, 'companyName': company_name}
    except Exception as e:
        return api_error(
            logger,
            'Fehler beim Speichern der Branding-Einstellungen',
            status_code=500,
            exc=e,
            context='update_branding_settings',
        )


@router.post('/api/settings/branding/logo', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
async def upload_branding_logo(request: Request, file: UploadFile = File(...)):
    """Upload and activate custom header logo (Admin only).

    Args:
        request: FastAPI request object with authenticated admin session.
        file: Uploaded image file (PNG/JPG/JPEG/SVG/WEBP, max. 5 MB).
    """
    try:
        if not file or not file.filename:
            return JSONResponse(content={'error': 'Keine Logo-Datei übergeben'}, status_code=400)

        _, ext = os.path.splitext(file.filename.lower())
        if ext not in {'.png', '.jpg', '.jpeg', '.svg', '.webp'}:
            return JSONResponse(content={'error': 'Nur PNG, JPG, JPEG, SVG oder WEBP sind erlaubt'}, status_code=400)

        content = await file.read()
        if not content:
            return JSONResponse(content={'error': 'Die Datei ist leer'}, status_code=400)
        if len(content) > 5 * 1024 * 1024:
            return JSONResponse(content={'error': 'Datei zu groß (max. 5 MB)'}, status_code=400)

        project_root = os.path.dirname(os.path.dirname(__file__))
        images_dir = os.path.join(project_root, 'wwwroot', 'images')
        os.makedirs(images_dir, exist_ok=True)

        for old_ext in ('.png', '.jpg', '.jpeg', '.svg', '.webp'):
            old_path = os.path.join(images_dir, f'company-logo-custom{old_ext}')
            if os.path.exists(old_path):
                os.remove(old_path)

        target_name = f'company-logo-custom{ext}'
        target_path = os.path.join(images_dir, target_name)
        with open(target_path, 'wb') as f:
            f.write(content)

        logo_url = f'/images/{target_name}'

        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        _ensure_app_settings_table(cursor)
        modified_by = request.session.get('user_email', 'system')
        _upsert_app_setting(cursor, 'HeaderLogoUrl', logo_url, modified_by)

        changes = json.dumps({'headerLogoUrl': logo_url}, ensure_ascii=False)
        log_audit(conn, 'BrandingSettings', 'HeaderLogoUrl', 'Updated', changes,
                  user_id=request.session.get('user_id'), user_name=modified_by)

        conn.commit()
        conn.close()
        return {'success': True, 'headerLogoUrl': logo_url}
    except Exception as e:
        return api_error(
            logger,
            'Fehler beim Upload des Logos',
            status_code=500,
            exc=e,
            context='upload_branding_logo',
        )


@router.get('/api/email-settings', dependencies=[Depends(require_role('Admin'))])
def get_email_settings(request: Request):
    """Get email settings (Admin only)"""
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT SmtpHost, SmtpPort, UseSsl, RequiresAuthentication, 
                   Username, SenderEmail, SenderName, ReplyToEmail, IsEnabled
            FROM EmailSettings
            WHERE Id = 1
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'smtpHost': row[0],
                'smtpPort': row[1],
                'useSsl': bool(row[2]),
                'requiresAuthentication': bool(row[3]),
                'username': row[4],
                # Don't send password for security
                'senderEmail': row[5],
                'senderName': row[6],
                'replyToEmail': row[7],
                'isEnabled': bool(row[8])
            }
        else:
            # Return default values if not configured
            return {
                'smtpHost': '',
                'smtpPort': 587,
                'useSsl': True,
                'requiresAuthentication': True,
                'username': '',
                'senderEmail': '',
                'senderName': 'Dienstplan',
                'replyToEmail': '',
                'isEnabled': False
            }
            
    except Exception as e:
        return api_error(
            logger,
            'Fehler beim Laden der E-Mail-Einstellungen',
            status_code=500,
            exc=e,
            context='get_email_settings',
        )


@router.post('/api/email-settings', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def save_email_settings(request: Request, data: dict = Depends(parse_json_body)):
    """Save email settings (Admin only)"""
    try:
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if settings exist
        cursor.execute("SELECT Id FROM EmailSettings WHERE Id = 1")
        exists = cursor.fetchone()
        
        smtp_password_env = os.environ.get('DIENSTPLAN_SMTP_PASSWORD')
        if exists:
            # Update existing settings
            # Only update password if provided
            if smtp_password_env:
                cursor.execute("""
                    UPDATE EmailSettings
                    SET SmtpHost = ?, SmtpPort = ?, UseSsl = ?, RequiresAuthentication = ?,
                        Username = ?, Password = NULL, SenderEmail = ?, SenderName = ?,
                        ReplyToEmail = ?, IsEnabled = ?, ModifiedAt = ?, ModifiedBy = ?
                    WHERE Id = 1
                """, (
                    data.get('smtpHost'),
                    data.get('smtpPort', 587),
                    1 if data.get('useSsl') else 0,
                    1 if data.get('requiresAuthentication') else 0,
                    data.get('username'),
                    data.get('senderEmail'),
                    data.get('senderName'),
                    data.get('replyToEmail'),
                    1 if data.get('isEnabled') else 0,
                    datetime.utcnow().isoformat(),
                    request.session.get('user_email')
                ))
            elif data.get('password'):
                cursor.execute("""
                    UPDATE EmailSettings
                    SET SmtpHost = ?, SmtpPort = ?, UseSsl = ?, RequiresAuthentication = ?,
                        Username = ?, Password = ?, SenderEmail = ?, SenderName = ?, 
                        ReplyToEmail = ?, IsEnabled = ?, ModifiedAt = ?, ModifiedBy = ?
                    WHERE Id = 1
                """, (
                    data.get('smtpHost'),
                    data.get('smtpPort', 587),
                    1 if data.get('useSsl') else 0,
                    1 if data.get('requiresAuthentication') else 0,
                    data.get('username'),
                    data.get('password'),
                    data.get('senderEmail'),
                    data.get('senderName'),
                    data.get('replyToEmail'),
                    1 if data.get('isEnabled') else 0,
                    datetime.utcnow().isoformat(),
                    request.session.get('user_email')
                ))
            else:
                cursor.execute("""
                    UPDATE EmailSettings
                    SET SmtpHost = ?, SmtpPort = ?, UseSsl = ?, RequiresAuthentication = ?,
                        Username = ?, SenderEmail = ?, SenderName = ?, 
                        ReplyToEmail = ?, IsEnabled = ?, ModifiedAt = ?, ModifiedBy = ?
                    WHERE Id = 1
                """, (
                    data.get('smtpHost'),
                    data.get('smtpPort', 587),
                    1 if data.get('useSsl') else 0,
                    1 if data.get('requiresAuthentication') else 0,
                    data.get('username'),
                    data.get('senderEmail'),
                    data.get('senderName'),
                    data.get('replyToEmail'),
                    1 if data.get('isEnabled') else 0,
                    datetime.utcnow().isoformat(),
                    request.session.get('user_email')
                ))
        else:
            # Insert new settings
            cursor.execute("""
                INSERT INTO EmailSettings 
                (Id, SmtpHost, SmtpPort, UseSsl, RequiresAuthentication, 
                 Username, Password, SenderEmail, SenderName, ReplyToEmail, 
                 IsEnabled, ModifiedBy)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('smtpHost'),
                data.get('smtpPort', 587),
                1 if data.get('useSsl') else 0,
                1 if data.get('requiresAuthentication') else 0,
                data.get('username'),
                None if smtp_password_env else data.get('password'),
                data.get('senderEmail'),
                data.get('senderName'),
                data.get('replyToEmail'),
                1 if data.get('isEnabled') else 0,
                request.session.get('user_email')
            ))
        
        conn.commit()
        conn.close()
        
        return {'success': True}
        
    except Exception as e:
        return api_error(
            logger,
            'Fehler beim Speichern der E-Mail-Einstellungen',
            status_code=500,
            exc=e,
            context='save_email_settings',
        )


@router.post('/api/email-settings/test', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def test_email_settings(request: Request, data: dict = Depends(parse_json_body)):
    """Send test email to verify settings (Admin only)"""
    try:
        test_email = data.get('testEmail')
        
        if not test_email:
            return JSONResponse(content={'error': 'Test-E-Mail-Adresse erforderlich'}, status_code=400)
        
        from email_service import send_test_email
        
        db = get_db()
        conn = db.get_connection()
        success, error = send_test_email(conn, test_email)
        conn.close()
        
        if success:
            return {'success': True}
        else:
            return JSONResponse(content={'error': error}, status_code=500)
            
    except Exception as e:
        return api_error(
            logger,
            'Fehler beim Senden der Test-E-Mail',
            status_code=500,
            exc=e,
            context='test_email_settings',
        )


# ─────────────────────────────────────────────────────────────────────────────
# Shift-settings export / import
# ─────────────────────────────────────────────────────────────────────────────

@router.get('/api/settings/shifts/export', dependencies=[Depends(require_auth)])
def export_shift_settings(request: Request):
    """Export all shift settings (shift types, rotation groups, global settings) as JSON.

    Returns a JSON file containing:
      - shiftTypes: list of shift type definitions with all configuration fields
      - rotationGroups: list of rotation groups with their shift sequences
      - globalSettings: global shift planning parameters
      - exportedAt: ISO timestamp of export
      - version: format version for future compatibility checks
    """
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()

        # ── Shift types ──────────────────────────────────────────────────────
        cursor.execute("""
            SELECT Id, Code, Name, StartTime, EndTime, DurationHours, ColorCode,
                   WeeklyWorkingHours, MinStaffWeekday, MaxStaffWeekday,
                   MinStaffWeekend, MaxStaffWeekend,
                   WorksMonday, WorksTuesday, WorksWednesday, WorksThursday,
                   WorksFriday, WorksSaturday, WorksSunday, MaxConsecutiveDays
            FROM ShiftTypes
            ORDER BY Id
        """)
        shift_types = []
        for row in cursor.fetchall():
            shift_types.append({
                'id': row['Id'],
                'code': row['Code'],
                'name': row['Name'],
                'startTime': row['StartTime'],
                'endTime': row['EndTime'],
                'durationHours': row['DurationHours'],
                'colorCode': row['ColorCode'],
                'weeklyWorkingHours': row['WeeklyWorkingHours'],
                'minStaffWeekday': row['MinStaffWeekday'],
                'maxStaffWeekday': row['MaxStaffWeekday'],
                'minStaffWeekend': row['MinStaffWeekend'],
                'maxStaffWeekend': row['MaxStaffWeekend'],
                'worksMonday': bool(row['WorksMonday']),
                'worksTuesday': bool(row['WorksTuesday']),
                'worksWednesday': bool(row['WorksWednesday']),
                'worksThursday': bool(row['WorksThursday']),
                'worksFriday': bool(row['WorksFriday']),
                'worksSaturday': bool(row['WorksSaturday']),
                'worksSunday': bool(row['WorksSunday']),
                'maxConsecutiveDays': row['MaxConsecutiveDays'],
            })

        # ── Rotation groups ───────────────────────────────────────────────────
        cursor.execute("""
            SELECT Id, Name, Description, IsActive
            FROM RotationGroups
            ORDER BY Id
        """)
        rotation_groups = []
        for rg_row in cursor.fetchall():
            cursor.execute("""
                SELECT st.Code, rgs.RotationOrder
                FROM RotationGroupShifts rgs
                INNER JOIN ShiftTypes st ON rgs.ShiftTypeId = st.Id
                WHERE rgs.RotationGroupId = ?
                ORDER BY rgs.RotationOrder
            """, (rg_row['Id'],))
            shifts_in_group = [
                {'shiftCode': s['Code'], 'rotationOrder': s['RotationOrder']}
                for s in cursor.fetchall()
            ]
            rotation_groups.append({
                'name': rg_row['Name'],
                'description': rg_row['Description'],
                'isActive': bool(rg_row['IsActive']),
                'shifts': shifts_in_group,
            })

        # ── Global settings ───────────────────────────────────────────────────
        cursor.execute("SELECT * FROM GlobalSettings WHERE Id = 1")
        gs_row = cursor.fetchone()
        global_settings = {
            'maxConsecutiveShifts': gs_row['MaxConsecutiveShifts'] if gs_row else 6,
            'maxConsecutiveNightShifts': gs_row['MaxConsecutiveNightShifts'] if gs_row else 3,
            'minRestHoursBetweenShifts': gs_row['MinRestHoursBetweenShifts'] if gs_row else 11,
        }

        conn.close()

        export_data = {
            'version': '1.0',
            'exportedAt': datetime.utcnow().isoformat() + 'Z',
            'shiftTypes': shift_types,
            'rotationGroups': rotation_groups,
            'globalSettings': global_settings,
        }

        filename = f"schichteinstellungen_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        return Response(
            content=json.dumps(export_data, ensure_ascii=False, indent=2),
            media_type='application/json',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'},
        )

    except Exception as e:
        return api_error(
            logger,
            'Fehler beim Exportieren der Schichteinstellungen',
            status_code=500,
            exc=e,
            context='export_shift_settings',
        )


@router.post('/api/settings/shifts/import', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
async def import_shift_settings(request: Request, file: UploadFile = File(...)):
    """Import shift settings from a previously exported JSON file.

    Accepts a multipart/form-data upload with a single ``file`` field containing
    the JSON produced by the export endpoint.

    Behaviour (conflict_mode query parameter):
      - ``skip``    (default): existing records are left unchanged.
      - ``update``           : existing records are updated with imported values.
      - ``replace``          : all existing shift-types / rotation-groups are
                               deleted first, then the imported data is inserted.

    Returns a JSON summary with counts of created / updated / skipped records
    and any errors.
    """
    conflict_mode = request.query_params.get('conflict_mode', 'skip').lower()
    if conflict_mode not in ('skip', 'update', 'replace'):
        return JSONResponse(content={'error': 'Ungültiger conflict_mode. Erlaubt: skip, update, replace'}, status_code=400)

    if not file or not file.filename:
        return JSONResponse(content={'error': 'Keine Datei hochgeladen'}, status_code=400)

    try:
        raw = (await file.read()).decode('utf-8')
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JSONResponse(content={'error': 'Ungültige JSON-Datei: Datei konnte nicht gelesen werden'}, status_code=400)

    # Basic structure validation
    if not isinstance(data, dict):
        return JSONResponse(content={'error': 'Ungültiges Dateiformat: erwartet JSON-Objekt'}, status_code=400)

    shift_types = data.get('shiftTypes', [])
    rotation_groups = data.get('rotationGroups', [])
    global_settings = data.get('globalSettings', {})

    result = {
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'errors': [],
    }

    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        user = request.session.get('user_email', 'import')

        if conflict_mode == 'replace':
            # Delete all existing rotation group data first (FK dependency)
            cursor.execute("DELETE FROM RotationGroupShifts")
            cursor.execute("DELETE FROM RotationGroups")
            cursor.execute("DELETE FROM ShiftTypes")

        # ── Import shift types ────────────────────────────────────────────────
        for st in shift_types:
            try:
                code = st.get('code', '').strip()
                if not code:
                    result['errors'].append('Schichttyp ohne Code übersprungen')
                    result['skipped'] += 1
                    continue

                cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = ?", (code,))
                existing = cursor.fetchone()

                if existing:
                    if conflict_mode == 'skip':
                        result['skipped'] += 1
                        continue
                    # update or replace
                    cursor.execute("""
                        UPDATE ShiftTypes SET
                            Name = ?, StartTime = ?, EndTime = ?, DurationHours = ?,
                            ColorCode = ?, WeeklyWorkingHours = ?,
                            MinStaffWeekday = ?, MaxStaffWeekday = ?,
                            MinStaffWeekend = ?, MaxStaffWeekend = ?,
                            WorksMonday = ?, WorksTuesday = ?, WorksWednesday = ?,
                            WorksThursday = ?, WorksFriday = ?, WorksSaturday = ?,
                            WorksSunday = ?, MaxConsecutiveDays = ?
                        WHERE Code = ?
                    """, (
                        st.get('name', code),
                        st.get('startTime', ''),
                        st.get('endTime', ''),
                        st.get('durationHours', 8.0),
                        st.get('colorCode', '#607D8B'),
                        st.get('weeklyWorkingHours', 40.0),
                        st.get('minStaffWeekday', 1),
                        st.get('maxStaffWeekday', 10),
                        st.get('minStaffWeekend', 1),
                        st.get('maxStaffWeekend', 5),
                        1 if st.get('worksMonday', True) else 0,
                        1 if st.get('worksTuesday', True) else 0,
                        1 if st.get('worksWednesday', True) else 0,
                        1 if st.get('worksThursday', True) else 0,
                        1 if st.get('worksFriday', True) else 0,
                        1 if st.get('worksSaturday', False) else 0,
                        1 if st.get('worksSunday', False) else 0,
                        st.get('maxConsecutiveDays', 6),
                        code,
                    ))
                    result['updated'] += 1
                else:
                    cursor.execute("""
                        INSERT INTO ShiftTypes
                            (Code, Name, StartTime, EndTime, DurationHours, ColorCode,
                             WeeklyWorkingHours, MinStaffWeekday, MaxStaffWeekday,
                             MinStaffWeekend, MaxStaffWeekend,
                             WorksMonday, WorksTuesday, WorksWednesday, WorksThursday,
                             WorksFriday, WorksSaturday, WorksSunday, MaxConsecutiveDays)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (
                        code,
                        st.get('name', code),
                        st.get('startTime', ''),
                        st.get('endTime', ''),
                        st.get('durationHours', 8.0),
                        st.get('colorCode', '#607D8B'),
                        st.get('weeklyWorkingHours', 40.0),
                        st.get('minStaffWeekday', 1),
                        st.get('maxStaffWeekday', 10),
                        st.get('minStaffWeekend', 1),
                        st.get('maxStaffWeekend', 5),
                        1 if st.get('worksMonday', True) else 0,
                        1 if st.get('worksTuesday', True) else 0,
                        1 if st.get('worksWednesday', True) else 0,
                        1 if st.get('worksThursday', True) else 0,
                        1 if st.get('worksFriday', True) else 0,
                        1 if st.get('worksSaturday', False) else 0,
                        1 if st.get('worksSunday', False) else 0,
                        st.get('maxConsecutiveDays', 6),
                    ))
                    result['created'] += 1

            except Exception as e:
                result['errors'].append(f"Schichttyp '{st.get('code', '?')}': {e}")

        # ── Import rotation groups ────────────────────────────────────────────
        for rg in rotation_groups:
            try:
                name = rg.get('name', '').strip()
                if not name:
                    result['errors'].append('Rotationsgruppe ohne Name übersprungen')
                    result['skipped'] += 1
                    continue

                cursor.execute("SELECT Id FROM RotationGroups WHERE Name = ?", (name,))
                existing_rg = cursor.fetchone()

                if existing_rg:
                    if conflict_mode == 'skip':
                        result['skipped'] += 1
                        continue
                    # update
                    rg_id = existing_rg['Id']
                    cursor.execute("""
                        UPDATE RotationGroups SET
                            Description = ?, IsActive = ?, ModifiedAt = ?, ModifiedBy = ?
                        WHERE Id = ?
                    """, (
                        rg.get('description', ''),
                        1 if rg.get('isActive', True) else 0,
                        datetime.utcnow().isoformat(),
                        user,
                        rg_id,
                    ))
                    cursor.execute("DELETE FROM RotationGroupShifts WHERE RotationGroupId = ?", (rg_id,))
                    result['updated'] += 1
                else:
                    cursor.execute("""
                        INSERT INTO RotationGroups (Name, Description, IsActive, CreatedBy)
                        VALUES (?, ?, ?, ?)
                    """, (name, rg.get('description', ''), 1 if rg.get('isActive', True) else 0, user))
                    rg_id = cursor.lastrowid
                    result['created'] += 1

                # Insert shift entries for this rotation group
                for shift_entry in rg.get('shifts', []):
                    shift_code = shift_entry.get('shiftCode', '').strip()
                    if not shift_code:
                        continue
                    cursor.execute("SELECT Id FROM ShiftTypes WHERE Code = ?", (shift_code,))
                    st_row = cursor.fetchone()
                    if not st_row:
                        result['errors'].append(
                            f"Rotationsgruppe '{name}': Schichttyp '{shift_code}' nicht gefunden – übersprungen"
                        )
                        continue
                    cursor.execute("""
                        INSERT INTO RotationGroupShifts (RotationGroupId, ShiftTypeId, RotationOrder, CreatedBy)
                        VALUES (?, ?, ?, ?)
                    """, (rg_id, st_row['Id'], shift_entry.get('rotationOrder', 0), user))

            except Exception as e:
                result['errors'].append(f"Rotationsgruppe '{rg.get('name', '?')}': {e}")

        # ── Import global settings (always update) ────────────────────────────
        if global_settings:
            try:
                min_rest = global_settings.get('minRestHoursBetweenShifts', 11)
                max_consec = global_settings.get('maxConsecutiveShifts', 6)
                max_consec_night = global_settings.get('maxConsecutiveNightShifts', 3)

                cursor.execute("""
                    INSERT INTO GlobalSettings
                        (Id, MaxConsecutiveShifts, MaxConsecutiveNightShifts,
                         MinRestHoursBetweenShifts, ModifiedAt, ModifiedBy)
                    VALUES (1, ?, ?, ?, ?, ?)
                    ON CONFLICT(Id) DO UPDATE SET
                        MaxConsecutiveShifts = excluded.MaxConsecutiveShifts,
                        MaxConsecutiveNightShifts = excluded.MaxConsecutiveNightShifts,
                        MinRestHoursBetweenShifts = excluded.MinRestHoursBetweenShifts,
                        ModifiedAt = excluded.ModifiedAt,
                        ModifiedBy = excluded.ModifiedBy
                """, (max_consec, max_consec_night, min_rest, datetime.utcnow().isoformat(), user))

            except Exception as e:
                result['errors'].append(f"Allgemeine Einstellungen: {e}")

        log_audit(conn, 'ShiftSettings', 0, 'Imported',
                  json.dumps({'conflict_mode': conflict_mode, 'summary': result}, ensure_ascii=False),
                  user_id=request.session.get('user_id'), user_name=request.session.get('user_email'))

        conn.commit()
        conn.close()

        return {'success': True, **result}

    except Exception as e:
        return api_error(
            logger,
            'Fehler beim Importieren der Schichteinstellungen',
            status_code=500,
            exc=e,
            context='import_shift_settings',
        )
