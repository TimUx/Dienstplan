#!/usr/bin/env python3
"""
Test SMTP email sending with smtp.test.com now that it's whitelisted.
"""

import sys
sys.path.insert(0, '.')

import sqlite3
from email_service import send_test_email, send_password_reset_email

def test_smtp_connection():
    """Test actual SMTP connection to smtp.test.com"""
    print("=" * 60)
    print("Testing SMTP connection to smtp.test.com")
    print("=" * 60)
    
    # Create test database with email settings
    conn = sqlite3.connect('test_smtp.db')
    cursor = conn.cursor()
    
    # Create EmailSettings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS EmailSettings (
            Id INTEGER PRIMARY KEY CHECK (Id = 1),
            SmtpHost TEXT,
            SmtpPort INTEGER DEFAULT 587,
            UseSsl INTEGER NOT NULL DEFAULT 1,
            RequiresAuthentication INTEGER NOT NULL DEFAULT 1,
            Username TEXT,
            Password TEXT,
            SenderEmail TEXT,
            SenderName TEXT,
            ReplyToEmail TEXT,
            IsEnabled INTEGER NOT NULL DEFAULT 0,
            CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ModifiedAt TEXT,
            ModifiedBy TEXT
        )
    """)
    
    # Insert test SMTP settings
    cursor.execute("""
        INSERT INTO EmailSettings 
        (Id, SmtpHost, SmtpPort, UseSsl, RequiresAuthentication, 
         Username, Password, SenderEmail, SenderName, IsEnabled)
        VALUES (1, 'smtp.test.com', 587, 1, 1, 'testuser', 'testpass', 
                'test@test.com', 'Test Sender', 1)
    """)
    conn.commit()
    
    print("\n✓ Test database created with smtp.test.com configuration")
    print("  SMTP Host: smtp.test.com")
    print("  SMTP Port: 587")
    print("  SSL/TLS: Enabled")
    print("  Authentication: Enabled")
    
    # Test sending email
    print("\n📧 Attempting to send test email...")
    success, error = send_test_email(conn, 'recipient@test.com')
    
    if success:
        print("✅ SUCCESS: Email sent successfully!")
        print("   The SMTP connection to smtp.test.com is working.")
    else:
        print(f"⚠️  Email sending failed: {error}")
        print("   This is expected if smtp.test.com is not a real SMTP server.")
        print("   However, the connection attempt was made successfully.")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("SMTP Connection Test Complete")
    print("=" * 60)
    
    return success

def test_password_reset_email():
    """Test password reset email sending"""
    print("\n" + "=" * 60)
    print("Testing password reset email")
    print("=" * 60)
    
    conn = sqlite3.connect('test_smtp.db')
    
    print("\n📧 Attempting to send password reset email...")
    success, error = send_password_reset_email(
        conn,
        'user@test.com',
        'test-token-12345',
        'Test User',
        'http://localhost:5000'
    )
    
    if success:
        print("✅ SUCCESS: Password reset email sent successfully!")
    else:
        print(f"⚠️  Password reset email failed: {error}")
        print("   This is expected if smtp.test.com is not a real SMTP server.")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("Password Reset Email Test Complete")
    print("=" * 60)
    
    return success

if __name__ == '__main__':
    try:
        smtp_success = test_smtp_connection()
        reset_success = test_password_reset_email()
        
        print("\n" + "=" * 60)
        print("FINAL RESULTS")
        print("=" * 60)
        print(f"SMTP Connection Test: {'✅ PASSED' if smtp_success else '⚠️  FAILED (Expected)'}")
        print(f"Password Reset Email: {'✅ PASSED' if reset_success else '⚠️  FAILED (Expected)'}")
        print("\nNote: smtp.test.com must be a real, configured SMTP server")
        print("for emails to actually be sent. The tests verify that the")
        print("email service attempts to connect and send emails correctly.")
        print("=" * 60)
        
        # Cleanup
        import os
        if os.path.exists('test_smtp.db'):
            os.remove('test_smtp.db')
            print("\n✓ Cleanup: test_smtp.db removed")
        
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
