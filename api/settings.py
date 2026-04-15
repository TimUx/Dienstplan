"""
Settings Blueprint: global settings, email settings.
"""

from flask import Blueprint, jsonify, request, session, current_app
from datetime import datetime
import json

from .shared import get_db, require_auth, require_role, log_audit, require_csrf

bp = Blueprint('settings', __name__)


@bp.route('/api/settings/global', methods=['GET'])
def get_global_settings():
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
            return jsonify({
                'maxConsecutiveShifts': 6,
                'maxConsecutiveNightShifts': 3,
                'minRestHoursBetweenShifts': 11
            })
        
        return jsonify({
            'maxConsecutiveShifts': row['MaxConsecutiveShifts'],
            'maxConsecutiveNightShifts': row['MaxConsecutiveNightShifts'],
            'minRestHoursBetweenShifts': row['MinRestHoursBetweenShifts'],
            'modifiedAt': row['ModifiedAt'],
            'modifiedBy': row['ModifiedBy']
        })
        
    except Exception as e:
        current_app.logger.error(f"Get global settings error: {str(e)}")
        return jsonify({'error': f'Fehler beim Laden: {str(e)}'}), 500


@bp.route('/api/settings/global', methods=['PUT'])
@require_role('Admin')
@require_csrf
def update_global_settings():
    """Update global shift planning settings (Admin only)"""
    try:
        data = request.get_json()
        
        # Note: maxConsecutiveShifts and maxConsecutiveNightShifts are deprecated
        # These settings are now configured per shift type in the ShiftTypes table
        # We keep them in the database for backward compatibility but don't expose them in the UI
        
        db = get_db()
        conn = db.get_connection()
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
            return jsonify({'error': 'Mindest-Ruhezeit muss zwischen 8 und 24 Stunden liegen'}), 400
        
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
            session.get('user_email', 'system')
        ))
        
        # Log audit entry
        changes = json.dumps({'minRestHoursBetweenShifts': min_rest_hours}, ensure_ascii=False)
        log_audit(conn, 'GlobalSettings', 1, 'Updated', changes)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Update global settings error: {str(e)}")
        return jsonify({'error': f'Fehler beim Aktualisieren: {str(e)}'}), 500


@bp.route('/api/email-settings', methods=['GET'])
@require_role('Admin')
def get_email_settings():
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
            return jsonify({
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
            })
        else:
            # Return default values if not configured
            return jsonify({
                'smtpHost': '',
                'smtpPort': 587,
                'useSsl': True,
                'requiresAuthentication': True,
                'username': '',
                'senderEmail': '',
                'senderName': 'Dienstplan',
                'replyToEmail': '',
                'isEnabled': False
            })
            
    except Exception as e:
        current_app.logger.error(f"Get email settings error: {str(e)}")
        return jsonify({'error': f'Fehler: {str(e)}'}), 500


@bp.route('/api/email-settings', methods=['POST'])
@require_role('Admin')
@require_csrf
def save_email_settings():
    """Save email settings (Admin only)"""
    try:
        data = request.get_json()
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Check if settings exist
        cursor.execute("SELECT Id FROM EmailSettings WHERE Id = 1")
        exists = cursor.fetchone()
        
        if exists:
            # Update existing settings
            # Only update password if provided
            if data.get('password'):
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
                    session.get('user_email')
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
                    session.get('user_email')
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
                data.get('password'),
                data.get('senderEmail'),
                data.get('senderName'),
                data.get('replyToEmail'),
                1 if data.get('isEnabled') else 0,
                session.get('user_email')
            ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Save email settings error: {str(e)}")
        return jsonify({'error': f'Fehler: {str(e)}'}), 500


@bp.route('/api/email-settings/test', methods=['POST'])
@require_role('Admin')
@require_csrf
def test_email_settings():
    """Send test email to verify settings (Admin only)"""
    try:
        data = request.get_json()
        test_email = data.get('testEmail')
        
        if not test_email:
            return jsonify({'error': 'Test-E-Mail-Adresse erforderlich'}), 400
        
        from email_service import send_test_email
        
        db = get_db()
        conn = db.get_connection()
        success, error = send_test_email(conn, test_email)
        conn.close()
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': error}), 500
            
    except Exception as e:
        current_app.logger.error(f"Test email error: {str(e)}")
        return jsonify({'error': f'Fehler: {str(e)}'}), 500


# ─────────────────────────────────────────────────────────────────────────────
# Shift-settings export / import
# ─────────────────────────────────────────────────────────────────────────────

@bp.route('/api/settings/shifts/export', methods=['GET'])
@require_auth
def export_shift_settings():
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

        from flask import Response
        filename = f"schichteinstellungen_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        return Response(
            json.dumps(export_data, ensure_ascii=False, indent=2),
            mimetype='application/json',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'},
        )

    except Exception as e:
        current_app.logger.error(f"Export shift settings error: {str(e)}")
        return jsonify({'error': f'Fehler beim Exportieren: {str(e)}'}), 500


@bp.route('/api/settings/shifts/import', methods=['POST'])
@require_role('Admin')
@require_csrf
def import_shift_settings():
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
    conflict_mode = request.args.get('conflict_mode', 'skip').lower()
    if conflict_mode not in ('skip', 'update', 'replace'):
        return jsonify({'error': 'Ungültiger conflict_mode. Erlaubt: skip, update, replace'}), 400

    if 'file' not in request.files:
        return jsonify({'error': 'Keine Datei hochgeladen'}), 400

    uploaded_file = request.files['file']
    if not uploaded_file.filename:
        return jsonify({'error': 'Keine Datei ausgewählt'}), 400

    try:
        raw = uploaded_file.read().decode('utf-8')
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return jsonify({'error': f'Ungültige JSON-Datei: {exc}'}), 400

    # Basic structure validation
    if not isinstance(data, dict):
        return jsonify({'error': 'Ungültiges Dateiformat: erwartet JSON-Objekt'}), 400

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
        user = session.get('user_email', 'import')

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
                  json.dumps({'conflict_mode': conflict_mode, 'summary': result}, ensure_ascii=False))

        conn.commit()
        conn.close()

        return jsonify({'success': True, **result}), 200

    except Exception as e:
        current_app.logger.error(f"Import shift settings error: {str(e)}")
        return jsonify({'error': f'Fehler beim Importieren: {str(e)}'}), 500
