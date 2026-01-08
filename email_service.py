"""
Email service for sending notifications using configured SMTP settings.
"""

import smtplib
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict
from datetime import datetime


def get_email_settings(conn: sqlite3.Connection) -> Optional[Dict]:
    """
    Get email settings from database.
    
    Args:
        conn: Database connection
        
    Returns:
        Dictionary with email settings or None if not configured
    """
    cursor = conn.cursor()
    cursor.execute("""
        SELECT SmtpHost, SmtpPort, UseSsl, RequiresAuthentication, 
               Username, Password, SenderEmail, SenderName, ReplyToEmail, IsEnabled
        FROM EmailSettings
        WHERE Id = 1
    """)
    
    row = cursor.fetchone()
    if not row:
        return None
    
    return {
        'smtpHost': row[0],
        'smtpPort': row[1],
        'useSsl': bool(row[2]),
        'requiresAuthentication': bool(row[3]),
        'username': row[4],
        'password': row[5],
        'senderEmail': row[6],
        'senderName': row[7],
        'replyToEmail': row[8],
        'isEnabled': bool(row[9])
    }


def send_email(
    conn: sqlite3.Connection,
    to_email: str,
    subject: str,
    body_html: str,
    body_text: Optional[str] = None
) -> tuple[bool, str]:
    """
    Send an email using configured SMTP settings.
    
    Args:
        conn: Database connection
        to_email: Recipient email address
        subject: Email subject
        body_html: HTML body content
        body_text: Plain text body content (optional, will use HTML if not provided)
        
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    # Get email settings
    settings = get_email_settings(conn)
    
    if not settings:
        return False, "Email-Einstellungen nicht gefunden"
    
    if not settings['isEnabled']:
        return False, "E-Mail-Versand ist deaktiviert"
    
    if not settings['smtpHost'] or not settings['senderEmail']:
        return False, "SMTP-Host oder Absender-E-Mail nicht konfiguriert"
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{settings['senderName']} <{settings['senderEmail']}>" if settings['senderName'] else settings['senderEmail']
        msg['To'] = to_email
        
        if settings['replyToEmail']:
            msg['Reply-To'] = settings['replyToEmail']
        
        # Attach plain text and HTML parts
        if body_text:
            part1 = MIMEText(body_text, 'plain', 'utf-8')
            msg.attach(part1)
        
        part2 = MIMEText(body_html, 'html', 'utf-8')
        msg.attach(part2)
        
        # Connect to SMTP server
        if settings['useSsl']:
            server = smtplib.SMTP_SSL(settings['smtpHost'], settings['smtpPort'])
        else:
            server = smtplib.SMTP(settings['smtpHost'], settings['smtpPort'])
            server.starttls()
        
        # Authenticate if required
        if settings['requiresAuthentication'] and settings['username'] and settings['password']:
            server.login(settings['username'], settings['password'])
        
        # Send email
        server.send_message(msg)
        server.quit()
        
        return True, ""
        
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP-Authentifizierung fehlgeschlagen. Bitte überprüfen Sie Benutzername und Passwort."
    except smtplib.SMTPException as e:
        return False, f"SMTP-Fehler: {str(e)}"
    except Exception as e:
        return False, f"Fehler beim Senden der E-Mail: {str(e)}"


def send_password_reset_email(
    conn: sqlite3.Connection,
    to_email: str,
    reset_token: str,
    employee_name: str,
    base_url: str = "http://localhost:5000"
) -> tuple[bool, str]:
    """
    Send password reset email to user.
    
    Args:
        conn: Database connection
        to_email: Recipient email address
        reset_token: Password reset token
        employee_name: Name of the employee
        base_url: Base URL of the application
        
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    reset_link = f"{base_url}/#/reset-password?token={reset_token}"
    
    subject = "Dienstplan - Passwort zurücksetzen"
    
    body_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #1976D2; color: white; padding: 20px; text-align: center; }}
            .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
            .button {{ display: inline-block; padding: 12px 24px; background-color: #1976D2; 
                      color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
            .footer {{ margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; 
                      font-size: 12px; color: #666; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Dienstplan - Passwort zurücksetzen</h1>
            </div>
            <div class="content">
                <p>Hallo {employee_name},</p>
                <p>Sie haben eine Anfrage zum Zurücksetzen Ihres Passworts gestellt.</p>
                <p>Klicken Sie auf den folgenden Link, um ein neues Passwort zu setzen:</p>
                <p style="text-align: center;">
                    <a href="{reset_link}" class="button">Passwort zurücksetzen</a>
                </p>
                <p>Oder kopieren Sie diesen Link in Ihren Browser:</p>
                <p style="word-break: break-all; background-color: #fff; padding: 10px; border: 1px solid #ddd;">
                    {reset_link}
                </p>
                <p><strong>Dieser Link ist 24 Stunden gültig.</strong></p>
                <p>Wenn Sie diese Anfrage nicht gestellt haben, können Sie diese E-Mail ignorieren.</p>
            </div>
            <div class="footer">
                <p>Diese E-Mail wurde automatisch generiert. Bitte antworten Sie nicht auf diese E-Mail.</p>
                <p>&copy; {datetime.now().year} Fritz Winter Eisengießerei GmbH & Co. KG</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    body_text = f"""
Hallo {employee_name},

Sie haben eine Anfrage zum Zurücksetzen Ihres Passworts gestellt.

Klicken Sie auf den folgenden Link, um ein neues Passwort zu setzen:
{reset_link}

Dieser Link ist 24 Stunden gültig.

Wenn Sie diese Anfrage nicht gestellt haben, können Sie diese E-Mail ignorieren.

---
Diese E-Mail wurde automatisch generiert. Bitte antworten Sie nicht auf diese E-Mail.
© {datetime.now().year} Fritz Winter Eisengießerei GmbH & Co. KG
    """
    
    return send_email(conn, to_email, subject, body_html, body_text)


def send_test_email(
    conn: sqlite3.Connection,
    to_email: str
) -> tuple[bool, str]:
    """
    Send a test email to verify SMTP settings.
    
    Args:
        conn: Database connection
        to_email: Recipient email address for test
        
    Returns:
        Tuple of (success: bool, error_message: str)
    """
    subject = "Dienstplan - Test E-Mail"
    
    body_html = """
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2>Test E-Mail erfolgreich!</h2>
        <p>Ihre E-Mail-Einstellungen funktionieren korrekt.</p>
        <p>Diese Nachricht wurde vom Dienstplan-System gesendet.</p>
    </body>
    </html>
    """
    
    body_text = """
Test E-Mail erfolgreich!

Ihre E-Mail-Einstellungen funktionieren korrekt.

Diese Nachricht wurde vom Dienstplan-System gesendet.
    """
    
    return send_email(conn, to_email, subject, body_html, body_text)
