# Quick Start Guide - Dienstplan System

This guide will help you get the Dienstplan system up and running in minutes.

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `ortools` - Google OR-Tools Constraint Solver
- `Flask` - Web framework
- `flask-cors` - CORS support

## Step 2: Initialize Database

Before starting the server, you need to initialize the SQLite database with the required schema:

```bash
python main.py init-db --with-sample-data
```

This command will:
- ✅ Create all necessary database tables
- ✅ Initialize default roles (Admin, Disponent, Mitarbeiter)
- ✅ Create default admin user
- ✅ Add standard shift types (F, S, N, Z, BMT, BSB, K, U, L)
- ✅ Add sample teams (Team Alpha, Beta, Gamma)

**Default Admin Credentials:**
- **Email**: `admin@fritzwinter.de`
- **Password**: `Admin123!`

⚠️ **IMPORTANT**: Change the default admin password after first login!

### Alternative: Initialize Without Sample Data

If you don't want sample teams:

```bash
python main.py init-db
```

This will only create the schema, roles, admin user, and shift types.

## Step 3: Start the Web Server

```bash
python main.py serve
```

The server will start on `http://localhost:5000`

### Custom Host/Port

```bash
python main.py serve --host 0.0.0.0 --port 8080
```

### Use Different Database

```bash
python main.py serve --db /path/to/custom.db
```

## Step 4: Access the Web Interface

Open your web browser and navigate to:

```
http://localhost:5000
```

You should see the Dienstplan web interface.

## Step 5: Login

Click the login button and use the default credentials:

- **Email**: `admin@fritzwinter.de`
- **Password**: `Admin123!`

After logging in as admin, you have full access to:
- ✅ Employee management
- ✅ Team management
- ✅ Shift planning
- ✅ Vacation requests
- ✅ Shift exchanges
- ✅ Statistics
- ✅ Administration panel

## Next Steps

### Add Employees

1. Navigate to "Mitarbeiter" (Employees)
2. Click "Mitarbeiter hinzufügen" (Add Employee)
3. Fill in the employee details
4. Assign to a team
5. Mark special roles (Springer, BMT, BSB)

### Plan Shifts

1. Navigate to "Dienstplan" (Schedule)
2. Click "Schichten planen" (Plan Shifts)
3. Select the period (month or year)
4. Click "Planen" (Plan)
5. Wait for the OR-Tools solver to find optimal solution

The system will automatically:
- ✅ Respect all work time regulations
- ✅ Maintain minimum staffing requirements
- ✅ Distribute shifts fairly
- ✅ Avoid forbidden shift transitions
- ✅ Ensure rest periods
- ✅ Assign special functions (BMT/BSB)

### Create Additional Users

As an admin, you can create more users:

1. Navigate to "Administration"
2. Click "Benutzer hinzufügen" (Add User)
3. Enter email, password, and assign role
4. Roles available:
   - **Admin**: Full access to all features
   - **Disponent**: Can plan shifts and manage employees
   - **Mitarbeiter**: Read-only access

## CLI Commands Reference

### Initialize Database

```bash
# With sample data
python main.py init-db --with-sample-data

# Without sample data
python main.py init-db

# Custom database path
python main.py init-db --db /path/to/db.db
```

### Start Web Server

```bash
# Default (localhost:5000)
python main.py serve

# Custom host and port
python main.py serve --host 0.0.0.0 --port 8080

# With debug mode (development only!)
python main.py serve --debug

# Custom database
python main.py serve --db /path/to/db.db
```

### Run CLI Planning

```bash
# Plan shifts for January 2025
python main.py plan --start-date 2025-01-01 --end-date 2025-01-31

# Use sample data (for testing)
python main.py plan --start-date 2025-01-01 --end-date 2025-01-31 --sample-data

# Custom time limit (in seconds)
python main.py plan --start-date 2025-01-01 --end-date 2025-01-31 --time-limit 600

# Custom database
python main.py plan --start-date 2025-01-01 --end-date 2025-01-31 --db /path/to/db.db
```

## Troubleshooting

### Database Table Errors

If you see errors like "no such table: Teams", you need to initialize the database:

```bash
python main.py init-db --with-sample-data
```

### Port Already in Use

If port 5000 is already in use, specify a different port:

```bash
python main.py serve --port 8080
```

### Module Not Found Errors

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Login Fails

Make sure you initialized the database first:

```bash
python main.py init-db
```

Then use the default credentials:
- Email: `admin@fritzwinter.de`
- Password: `Admin123!`

## Database Location

By default, the database is created in the current directory as `dienstplan.db`.

To use a different location, always specify `--db` parameter:

```bash
python main.py init-db --db /var/lib/dienstplan/production.db
python main.py serve --db /var/lib/dienstplan/production.db
```

## Production Deployment

For production deployment, consider:

1. **Use a production WSGI server** (not Flask development server)
   - gunicorn
   - uWSGI
   
2. **Set up HTTPS** (use reverse proxy like nginx)

3. **Change default admin password**

4. **Regular database backups**

5. **Use environment-specific database paths**

See [BUILD_GUIDE.md](BUILD_GUIDE.md) for more deployment options.

## Support

For more information:
- Full documentation: [README.md](../README.md)
- Architecture: [ARCHITECTURE.md](../ARCHITECTURE.md)
- Migration guide: [MIGRATION.md](../MIGRATION.md)
- Usage guide: [USAGE_GUIDE.md](USAGE_GUIDE.md)

---

**Version 2.0 - Python Edition**

© 2025 Fritz Winter Eisengießerei GmbH & Co. KG
