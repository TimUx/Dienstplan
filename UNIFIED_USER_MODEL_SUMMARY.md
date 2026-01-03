# Unified Employee/User Model - Implementation Summary

## Overview

Successfully implemented a unified data model that merges employee and user authentication into a single `Employees` table. This eliminates the need for separate user accounts and complex linking.

## Problem Solved

**Before:** Employees and authentication were separate entities that needed to be linked via EmployeeId
**After:** Every employee can optionally have authentication credentials stored directly in their record

## Architecture Change

### Previous Architecture (Linked Model)
```
┌─────────────┐         ┌──────────────┐
│ AspNetUsers │◄────────┤  Employees   │
│   (auth)    │ EmployeeId│  (HR data)   │
└──────┬──────┘         └──────────────┘
       │
       ▼
┌──────────────────┐
│ AspNetUserRoles  │
└──────────────────┘
```

### New Architecture (Unified Model)
```
┌─────────────────────────────────┐
│         Employees               │
│  (auth + HR data combined)      │
│  - Vorname, Name, Personalnummer│
│  - Email, PasswordHash          │
│  - SecurityStamp, LockoutEnd    │
│  - TeamId, Funktion, etc.       │
└────────────┬────────────────────┘
             │
             ▼
      ┌──────────────────┐
      │ AspNetUserRoles  │
      │ UserId = EmployeeId│
      └──────────────────┘
```

## Database Schema Changes

### Employees Table - New Fields
```sql
CREATE TABLE Employees (
    Id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- Employee Data (existing)
    Vorname TEXT NOT NULL,
    Name TEXT NOT NULL,
    Personalnummer TEXT NOT NULL UNIQUE,
    Geburtsdatum TEXT,
    Funktion TEXT,
    TeamId INTEGER,
    
    -- Authentication Fields (NEW)
    Email TEXT UNIQUE,
    NormalizedEmail TEXT,
    PasswordHash TEXT,
    SecurityStamp TEXT,
    LockoutEnd TEXT,
    AccessFailedCount INTEGER DEFAULT 0,
    IsActive INTEGER DEFAULT 1,
    
    -- Qualifications (existing)
    IsFerienjobber INTEGER DEFAULT 0,
    IsBrandmeldetechniker INTEGER DEFAULT 0,
    IsBrandschutzbeauftragter INTEGER DEFAULT 0,
    IsTdQualified INTEGER DEFAULT 0,
    IsTeamLeader INTEGER DEFAULT 0,
    CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### AspNetUserRoles - Updated Reference
```sql
CREATE TABLE AspNetUserRoles (
    UserId TEXT NOT NULL,  -- Now contains Employees.Id
    RoleId TEXT NOT NULL,
    PRIMARY KEY (UserId, RoleId),
    FOREIGN KEY (UserId) REFERENCES Employees(Id),
    FOREIGN KEY (RoleId) REFERENCES AspNetRoles(Id)
);
```

### Roles
Only two roles remain:
- **Admin**: Full system access
- **Mitarbeiter**: Read-only schedules, can submit vacation requests and shift exchanges

## API Changes

### Authentication

**Login (POST /api/auth/login)**
```json
Request:
{
  "email": "max@example.com",
  "password": "Secret123!"
}

Response:
{
  "success": true,
  "user": {
    "email": "max@example.com",
    "fullName": "Max Mustermann",
    "roles": ["Mitarbeiter"]
  }
}
```

### Employee/User Management (Admin Only)

**List All (GET /api/users)**
Returns all employees with authentication status:
```json
[
  {
    "id": 1,
    "vorname": "Admin",
    "name": "Administrator",
    "fullName": "Admin Administrator",
    "personalnummer": "ADMIN001",
    "email": "admin@fritzwinter.de",
    "funktion": "Administrator",
    "teamId": null,
    "teamName": null,
    "hasPassword": true,
    "roles": ["Admin"],
    "isActive": true,
    "accessFailedCount": 0,
    "lockoutEnd": null,
    "isFerienjobber": false,
    "isBrandmeldetechniker": false,
    "isBrandschutzbeauftragter": false,
    "isTdQualified": false,
    "isTeamLeader": false
  }
]
```

**Create Employee with Auth (POST /api/users)**
```json
Request:
{
  "vorname": "Max",
  "name": "Mustermann",
  "personalnummer": "EMP001",
  "email": "max@example.com",  // Optional
  "password": "Secret123!",     // Required if email provided
  "roles": ["Mitarbeiter"],
  "funktion": "Techniker",
  "teamId": 1,
  "geburtsdatum": "1990-01-15",
  "isFerienjobber": false,
  "isBrandmeldetechniker": false,
  "isBrandschutzbeauftragter": false
}

Response:
{
  "success": true,
  "userId": 2,
  "employeeId": 2
}
```

**Update Employee (PUT /api/users/:id)**
```json
Request:
{
  "vorname": "Max",
  "name": "Mustermann",
  "personalnummer": "EMP001",
  "email": "max.new@example.com",
  "password": "NewSecret123!",  // Optional password change
  "roles": ["Admin"],           // Change role
  "funktion": "Senior Techniker",
  "teamId": 2
}

Response:
{
  "success": true
}
```

**Delete Employee (DELETE /api/users/:id)**
```json
Response:
{
  "success": true
}
```

### Get Employees (GET /api/employees)

Now includes authentication status (public endpoint):
```json
[
  {
    "id": 1,
    "vorname": "Admin",
    "name": "Administrator",
    "fullName": "Admin Administrator",
    "personalnummer": "ADMIN001",
    "email": "admin@fritzwinter.de",
    "hasPassword": true,        // NEW
    "roles": ["Admin"],         // NEW
    "funktion": "Administrator",
    "teamId": null,
    "teamName": null,
    "geburtsdatum": null,
    "isActive": true,
    "isFerienjobber": false,
    "isBrandmeldetechniker": false,
    "isBrandschutzbeauftragter": false,
    "isTdQualified": false,
    "isTeamLeader": false
  }
]
```

## Migration for Existing Databases

### Step 1: Merge Users into Employees
```bash
python migrate_merge_users_employees.py dienstplan.db
```

This script:
1. Adds authentication fields to Employees table
2. Migrates AspNetUsers data to Employees
3. Updates AspNetUserRoles to reference Employees.Id
4. Creates backup of AspNetUsers table
5. Preserves all existing data

### Step 2: Remove Disponent Role
```bash
python migrate_remove_disponent_role.py dienstplan.db
```

This script:
1. Converts all Disponent users to Admin role
2. Removes Disponent role from database

## Code Changes Summary

### web_api.py

**New/Updated Functions:**
- `get_employee_by_email()` - Replaces `get_user_by_email()`, queries Employees
- `login()` - Authenticates against Employees table
- `get_all_users()` - Lists all employees with auth status
- `get_user(id)` - Gets single employee with complete data
- `create_user()` - Creates employee with optional auth credentials
- `update_user(id)` - Updates employee including password change
- `delete_user(id)` - Deletes employee with admin protection
- `get_employees()` - Now shows hasPassword and roles

### db_init.py

**Updated Functions:**
- `create_database_schema()` - Employees table includes auth fields
- `create_default_admin()` - Creates admin as Employee record (ADMIN001)
- `initialize_default_roles()` - Only Admin and Mitarbeiter roles

## Benefits

### Simplified Architecture
- ✅ **Single source of truth** - All employee data in one table
- ✅ **No complex linking** - No EmployeeId foreign keys to manage
- ✅ **Cleaner queries** - Direct access to employee + auth data

### Better User Experience
- ✅ **One form** for employee and user management
- ✅ **Optional authentication** - Not all employees need login
- ✅ **Unified view** - See employee data and login status together

### Easier Maintenance
- ✅ **Fewer tables** to manage
- ✅ **Simpler migrations** - Single table updates
- ✅ **Clear data model** - Employee IS the user

## Testing Results

All tests passed successfully:

✅ **Database Initialization**
- Admin employee created (ID: 1, ADMIN001)
- Role assigned correctly (UserId=1 in AspNetUserRoles)

✅ **Authentication**
- Admin login successful
- New employee login successful
- Failed login tracking works

✅ **User Management**
- GET /api/users returns unified data
- POST /api/users creates employee with auth
- PUT /api/users updates employee
- DELETE /api/users with admin protection works

✅ **Employee Endpoint**
- GET /api/employees shows hasPassword and roles
- Public access works correctly

## Backward Compatibility

### During Migration
- AspNetUsers table kept as backup
- Migration script is interactive (requires confirmation)
- All data preserved during migration

### After Migration
- Old `/api/users` endpoints work with new model
- Frontend changes not required (API contract maintained)
- Can drop AspNetUsers after verification

## Security Considerations

- ✅ Password hashing unchanged (SHA256)
- ✅ Failed login attempts tracked
- ✅ Account lockout functionality preserved
- ✅ Session management unchanged
- ✅ Role-based access control maintained
- ✅ Last admin deletion prevented

## Future Enhancements

### Potential Improvements
1. **Password Reset** - Add email-based password reset
2. **Two-Factor Auth** - Add 2FA support
3. **Password Policy** - Enforce complexity requirements
4. **Audit Trail** - Enhanced logging of auth events
5. **Bulk Import** - Import employees with optional auth

### Not Recommended
- ❌ Don't add AspNetUsers back
- ❌ Don't separate auth from employee data
- ❌ Don't create complex linking again

## Conclusion

The unified employee/user model simplifies the architecture, improves maintainability, and provides a better user experience. The migration path is clear and safe, with full data preservation.

**Status:** ✅ **PRODUCTION READY**

For questions or issues, refer to:
- Migration scripts: `migrate_merge_users_employees.py`
- API implementation: `web_api.py`
- Database schema: `db_init.py`
