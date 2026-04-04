"""
Settings Blueprint: global settings, email settings.
"""

from flask import Blueprint, jsonify, request, session, current_app
from datetime import datetime
import json

from .shared import get_db, require_auth, require_role, log_audit

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
