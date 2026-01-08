#!/usr/bin/env python3
"""
Migration script to add password management features to existing Dienstplan databases.

This script adds:
- EmailSettings table for SMTP configuration
- PasswordResetTokens table for password reset functionality

Usage:
    python migrate_add_password_management.py [database_path]
    
    If no database path is provided, defaults to 'dienstplan.db'
"""

import sqlite3
import sys
import os


def migrate_database(db_path: str = "dienstplan.db"):
    """
    Add password management tables to existing database.
    
    Args:
        db_path: Path to the SQLite database file
    """
    if not os.path.exists(db_path):
        print(f"Error: Database file '{db_path}' not found!")
        return False
    
    print(f"Migrating database: {db_path}")
    print("=" * 60)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if EmailSettings table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='EmailSettings'")
        if cursor.fetchone():
            print("⚠️  EmailSettings table already exists, skipping...")
        else:
            print("Creating EmailSettings table...")
            cursor.execute("""
                CREATE TABLE EmailSettings (
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
            print("✓ EmailSettings table created")
        
        # Check if PasswordResetTokens table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='PasswordResetTokens'")
        if cursor.fetchone():
            print("⚠️  PasswordResetTokens table already exists, skipping...")
        else:
            print("Creating PasswordResetTokens table...")
            cursor.execute("""
                CREATE TABLE PasswordResetTokens (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    EmployeeId INTEGER NOT NULL,
                    Token TEXT NOT NULL UNIQUE,
                    ExpiresAt TEXT NOT NULL,
                    IsUsed INTEGER NOT NULL DEFAULT 0,
                    UsedAt TEXT,
                    CreatedAt TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (EmployeeId) REFERENCES Employees(Id)
                )
            """)
            print("✓ PasswordResetTokens table created")
            
            # Create indexes
            print("Creating indexes for PasswordResetTokens...")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_passwordresettokens_token 
                ON PasswordResetTokens(Token)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_passwordresettokens_employee 
                ON PasswordResetTokens(EmployeeId, IsUsed, ExpiresAt)
            """)
            print("✓ Indexes created")
        
        conn.commit()
        print("\n" + "=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Configure email settings in Admin > E-Mail-Einstellungen")
        print("2. Test password reset functionality")
        print("3. Users can now change their passwords via profile")
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = "dienstplan.db"
    
    print("Dienstplan Database Migration")
    print("Add Password Management Features")
    print("=" * 60)
    
    success = migrate_database(db_path)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
