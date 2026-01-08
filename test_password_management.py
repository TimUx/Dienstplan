#!/usr/bin/env python3
"""
Test script for password management features.
"""

import sys
sys.path.insert(0, '.')

from web_api import create_app, hash_password, verify_password
import sqlite3
from datetime import datetime, timedelta
import secrets

def test_password_hashing():
    """Test password hashing and verification"""
    print("Testing password hashing...")
    password = "TestPassword123!"
    hashed = hash_password(password)
    
    assert verify_password(password, hashed), "Password verification failed"
    assert not verify_password("WrongPassword", hashed), "Wrong password should not verify"
    print("✓ Password hashing works correctly")

def test_email_settings_table():
    """Test EmailSettings table structure"""
    print("\nTesting EmailSettings table...")
    conn = sqlite3.connect('test_password.db')
    cursor = conn.cursor()
    
    # Insert test email settings
    cursor.execute("""
        INSERT INTO EmailSettings 
        (Id, SmtpHost, SmtpPort, UseSsl, RequiresAuthentication, 
         Username, Password, SenderEmail, SenderName, IsEnabled)
        VALUES (1, 'smtp.test.com', 587, 1, 1, 'test@test.com', 'password123', 
                'sender@test.com', 'Test Sender', 1)
    """)
    conn.commit()
    
    # Retrieve settings
    cursor.execute("SELECT * FROM EmailSettings WHERE Id = 1")
    row = cursor.fetchone()
    assert row is not None, "Failed to insert email settings"
    print(f"✓ EmailSettings table works correctly: {row[1]}:{row[2]}")
    
    conn.close()

def test_password_reset_tokens():
    """Test PasswordResetTokens table"""
    print("\nTesting PasswordResetTokens table...")
    conn = sqlite3.connect('test_password.db')
    cursor = conn.cursor()
    
    # Get admin employee ID
    cursor.execute("SELECT Id FROM Employees WHERE Email = 'admin@fritzwinter.de'")
    admin_row = cursor.fetchone()
    assert admin_row is not None, "Admin employee not found"
    admin_id = admin_row[0]
    
    # Create a test reset token
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()
    
    cursor.execute("""
        INSERT INTO PasswordResetTokens (EmployeeId, Token, ExpiresAt)
        VALUES (?, ?, ?)
    """, (admin_id, token, expires_at))
    conn.commit()
    
    # Verify token was created
    cursor.execute("SELECT * FROM PasswordResetTokens WHERE Token = ?", (token,))
    row = cursor.fetchone()
    assert row is not None, "Failed to create reset token"
    assert row[2] == token, "Token mismatch"
    assert row[4] == 0, "Token should not be used initially"
    print(f"✓ PasswordResetTokens table works correctly")
    
    # Test token retrieval
    cursor.execute("""
        SELECT Id, EmployeeId, ExpiresAt FROM PasswordResetTokens 
        WHERE Token = ? AND IsUsed = 0
    """, (token,))
    token_row = cursor.fetchone()
    assert token_row is not None, "Token retrieval failed"
    print(f"✓ Token retrieval works correctly")
    
    conn.close()

def test_api_endpoints():
    """Test password management API endpoints"""
    print("\nTesting API endpoints...")
    app = create_app('test_password.db')
    
    with app.test_client() as client:
        # Test forgot password endpoint (public, no auth required)
        response = client.post('/api/auth/forgot-password',
                             json={'email': 'admin@fritzwinter.de'},
                             content_type='application/json')
        print(f"Forgot password endpoint status: {response.status_code}")
        # Should return 200 even if email doesn't have SMTP configured
        assert response.status_code == 200, f"Forgot password failed: {response.status_code}"
        print("✓ Forgot password endpoint works")
        
        # Test validate token endpoint
        response = client.post('/api/auth/validate-reset-token',
                             json={'token': 'invalid-token'},
                             content_type='application/json')
        print(f"Validate token endpoint status: {response.status_code}")
        assert response.status_code == 200, "Validate token endpoint failed"
        data = response.get_json()
        assert data['valid'] == False, "Invalid token should not be valid"
        print("✓ Validate token endpoint works")
        
        # Test login (to get authenticated session)
        response = client.post('/api/auth/login',
                             json={'email': 'admin@fritzwinter.de', 'password': 'Admin123!'},
                             content_type='application/json')
        print(f"Login endpoint status: {response.status_code}")
        assert response.status_code == 200, "Login failed"
        print("✓ Login works")
        
        # Test change password endpoint (requires auth)
        response = client.post('/api/auth/change-password',
                             json={'currentPassword': 'Admin123!', 
                                   'newPassword': 'NewPassword123!'},
                             content_type='application/json')
        print(f"Change password endpoint status: {response.status_code}")
        assert response.status_code == 200, f"Change password failed: {response.status_code}"
        print("✓ Change password endpoint works")
        
        # Test email settings endpoint (requires admin auth)
        response = client.get('/api/email-settings')
        print(f"Email settings endpoint status: {response.status_code}")
        assert response.status_code == 200, "Email settings GET failed"
        print("✓ Email settings GET endpoint works")

def main():
    """Run all tests"""
    print("=" * 60)
    print("Password Management Features Test Suite")
    print("=" * 60)
    
    try:
        test_password_hashing()
        test_email_settings_table()
        test_password_reset_tokens()
        test_api_endpoints()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed successfully!")
        print("=" * 60)
        return 0
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
