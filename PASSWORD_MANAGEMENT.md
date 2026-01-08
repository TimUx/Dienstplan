# Password Management Features

This document describes the password management features added to the Dienstplan system.

## Features

### 1. Admin: Set/Change User Passwords

Administrators can now set or change passwords when creating or editing users/employees:

- When **creating a new user**: Password field is required
- When **editing an existing user**: Password field is optional (leave empty to keep current password)

**How to use:**
1. Login as Admin
2. Go to **Verwaltung** (Management) or **Admin** panel
3. Click **Benutzer** (Users) tab
4. Click **➕ Benutzer hinzufügen** (Add User) or edit an existing user
5. Enter password (minimum 8 characters)

### 2. Password Forgot Function

Users can request a password reset link via email if they forget their password.

**Requirements:**
- Email settings must be configured in Admin panel
- User must have a valid email address

**How to use:**
1. On login page, click **"Passwort vergessen?"** (Forgot Password?)
2. Enter your email address
3. Check your email for reset link (valid for 24 hours)
4. Click the link and set a new password

### 3. User Profile: Change Own Password

Users can change their own password without admin intervention.

**How to use:**
1. Login to the system
2. Click **🔒 Passwort ändern** button in the top right corner
3. Enter your current password
4. Enter your new password (minimum 8 characters)
5. Confirm the new password
6. Click **Passwort ändern** (Change Password)

## Email Configuration

To enable password reset functionality, administrators must configure email settings:

1. Login as Admin
2. Go to **Admin** > **E-Mail-Einstellungen**
3. Click **E-Mail-Einstellungen bearbeiten**
4. Configure SMTP settings:
   - **SMTP Server**: Your mail server address (e.g., smtp.gmail.com)
   - **SMTP Port**: Usually 587 (STARTTLS) or 465 (SSL)
   - **SSL/TLS**: Enable if your server requires it
   - **Authentication**: Enable and provide username/password if required
   - **Sender Email**: Email address that will appear as sender
   - **Sender Name**: Display name for the sender
5. Click **Test senden** to verify settings
6. Save the configuration

### Common SMTP Providers

**Gmail:**
- Server: smtp.gmail.com
- Port: 587
- SSL: Yes
- Note: You may need to create an "App Password" in Google Account settings

**Microsoft 365:**
- Server: smtp.office365.com
- Port: 587
- SSL: Yes

**Custom SMTP Server:**
- Contact your IT department for settings

## Security Features

- **Password Hashing**: All passwords are hashed using SHA256
- **Token Expiry**: Password reset tokens expire after 24 hours
- **One-Time Use**: Reset tokens can only be used once
- **Email Enumeration Protection**: System doesn't reveal if an email exists
- **Current Password Verification**: Users must know their current password to change it
- **Minimum Password Length**: 8 characters required

## Database Migration

For existing Dienstplan installations, run the migration script:

```bash
python migrate_add_password_management.py [database_path]
```

This adds the required tables:
- `EmailSettings`: Stores SMTP configuration
- `PasswordResetTokens`: Manages password reset tokens

## API Endpoints

### Password Management

- `POST /api/auth/change-password` - Change own password (authenticated)
- `POST /api/auth/forgot-password` - Request password reset link
- `POST /api/auth/reset-password` - Reset password with token
- `POST /api/auth/validate-reset-token` - Check if token is valid

### Email Settings (Admin Only)

- `GET /api/email-settings` - Get current email configuration
- `POST /api/email-settings` - Save email configuration
- `POST /api/email-settings/test` - Send test email

## Troubleshooting

### Password reset email not received

1. Check spam/junk folder
2. Verify email settings are correct (Admin panel)
3. Test email settings using **Test senden** button
4. Check that sender email is verified with your SMTP provider
5. Verify user has a valid email address in their profile

### Cannot change password

1. Ensure current password is correct
2. New password must be at least 8 characters
3. Make sure you're logged in
4. Check browser console for errors

### Email sending errors

- **Authentication Failed**: Check username and password in email settings
- **Connection Timeout**: Verify SMTP server address and port
- **SSL/TLS Error**: Try different SSL/TLS settings
- **Relay Not Allowed**: Some SMTP servers require authenticated sender

## Testing

Run the test suite to verify functionality:

```bash
python test_password_management.py
```

This tests:
- Password hashing and verification
- Database table structure
- API endpoints functionality
- Token generation and validation

## Future Enhancements

Potential improvements for future versions:
- Password complexity requirements (uppercase, lowercase, numbers, symbols)
- Password history (prevent reusing recent passwords)
- Multi-factor authentication (2FA)
- Password expiration policies
- Account lockout after failed attempts
- Upgrade to bcrypt/Argon2 for password hashing

## Support

For issues or questions:
- Check the main [README.md](README.md)
- Review the [BENUTZERHANDBUCH.md](BENUTZERHANDBUCH.md)
- Open an issue on GitHub
