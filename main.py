"""
Main entry point for the Python OR-Tools shift planning system.
Provides both CLI and web server interfaces.
"""

import argparse
import logging
import os
import sys
from datetime import date, timedelta
from typing import Optional

from data_loader import generate_sample_data, load_from_database
from db_init import initialize_database, run_migrations
from model import create_shift_planning_model
from solver import solve_shift_planning

logger = logging.getLogger(__name__)

try:
    import uvicorn
except ImportError:
    uvicorn = None


def run_cli_planning(
    start_date: date,
    end_date: date,
    use_sample_data: bool = False,
    db_path: str = "dienstplan.db",
    time_limit: int = 300
):
    """
    Run shift planning from command line.
    
    Args:
        start_date: Start date for planning
        end_date: End date for planning
        use_sample_data: If True, use generated sample data instead of database
        db_path: Path to SQLite database
        time_limit: Solver time limit in seconds
    """
    logger.info("SHIFT PLANNING SYSTEM - Python OR-Tools Migration")
    
    # Load data
    if use_sample_data:
        logger.info("Loading sample data...")
        employees, teams, absences = generate_sample_data()
        shift_types = None  # Use default STANDARD_SHIFT_TYPES
    else:
        logger.info(f"Loading data from database: {db_path}")
        try:
            employees, teams, absences, shift_types = load_from_database(db_path)
        except Exception as e:
            logger.error(f"Error loading database: {e}")
            logger.warning("Using sample data instead...")
            employees, teams, absences = generate_sample_data()
            shift_types = None  # Use default STANDARD_SHIFT_TYPES
    
    logger.info(f"Loaded {len(employees)} employees")
    logger.info(f"Loaded {len(teams)} teams")
    logger.info(f"Loaded {len(absences)} absences")

    
    # Create model
    logger.info(f"Creating planning model for {start_date} to {end_date}...")
    planning_model = create_shift_planning_model(
        employees, teams, start_date, end_date, absences, shift_types=shift_types
    )
    planning_model.print_model_statistics()
    
    # Solve
    logger.info("Solving shift planning problem...")
    result = solve_shift_planning(planning_model, time_limit_seconds=time_limit)
    
    if not result:
        logger.error("No solution found!")
        return 1
    
    assignments, complete_schedule, planning_report = result
    logger.info("Solution found!")
    logger.info(f"Total assignments: {len(assignments)}")
    logger.info(f"Complete schedule entries: {len(complete_schedule)}")
    
    # Print planning report (includes validation results)
    logger.info(planning_report.generate_text_summary())
    
    # Print summary
    logger.info("SUMMARY BY TEAM")
    
    for team in teams:
        logger.info(f"Team: {team.name}")
        team_employees = [emp for emp in employees if emp.team_id == team.id]
        for emp in team_employees:
            emp_assignments = [a for a in assignments if a.employee_id == emp.id]
            logger.info(f"  {emp.full_name}: {len(emp_assignments)} shifts")
    

    
    # Save results if database mode
    if not use_sample_data:
        logger.info("Saving results to database...")
        try:
            save_assignments_to_database(assignments, db_path)
            logger.info("Results saved successfully!")
        except Exception as e:
            logger.error(f"Error saving results: {e}")
    
    return 0


def save_assignments_to_database(assignments, db_path: str):
    """Save shift assignments to SQLite database"""
    import sqlite3
    from datetime import datetime
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Delete existing assignments in the date range
    if assignments:
        min_date = min(a.date for a in assignments)
        max_date = max(a.date for a in assignments)
        cursor.execute(
            "DELETE FROM ShiftAssignments WHERE Date >= ? AND Date <= ? AND IsFixed = 0",
            (min_date.isoformat(), max_date.isoformat())
        )
    
    # Insert new assignments
    for assignment in assignments:
        cursor.execute("""
            INSERT INTO ShiftAssignments 
            (EmployeeId, ShiftTypeId, Date, IsManual, IsFixed, CreatedAt, CreatedBy)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            assignment.employee_id,
            assignment.shift_type_id,
            assignment.date.isoformat(),
            0,  # IsManual = False (automatic)
            0,  # IsFixed = False
            datetime.utcnow().isoformat(),
            "Python-OR-Tools"
        ))
    
    conn.commit()
    conn.close()


def start_web_server(host: str = "0.0.0.0", port: int = 5000, db_path: str = "dienstplan.db", debug: bool = False):
    """
    Start web server with REST API using Uvicorn (ASGI) production server.
    This provides the backend for the existing Web UI.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        db_path: Path to SQLite database
        debug: Enable debug/reload mode (WARNING: Only use in development!)
    """
    from web_api import create_app
    
    logger.info(f"SHIFT PLANNING WEB SERVER starting on http://{host}:{port}")
    logger.info(f"Database: {db_path}")
    if debug:
        logger.warning("Debug mode enabled - auto-reload active! DO NOT use in production!")
    else:
        logger.info("Using Uvicorn production ASGI server")

    
    # Check if database exists, if not initialize it; otherwise run migrations
    if not os.path.exists(db_path):
        print(f"[i] No database found at {db_path}")
        print("   Initializing new database with default structure...")
    
        try:
            # Initialize without sample data for production use
            initialize_database(db_path, with_sample_data=False)
        
        except Exception as e:
            print(f"[!] Error initializing database: {e}")
            print("   The application may not work correctly.")
        
    else:
        # Existing database – apply any outstanding migrations automatically
        try:
            run_migrations(db_path)
        except Exception as e:
            logger.error(f"Error running migrations: {e}")
    
    print("The existing Web UI from .NET version is compatible with this backend.")
    print("=" * 60)

    
    app = create_app(db_path)
    
    try:
        import uvicorn
    except ImportError:
        logger.error("uvicorn is not installed. Please run: pip install uvicorn[standard]")
        raise

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="debug" if debug else "info",
        reload=debug,
    )


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Shift Planning System - Python OR-Tools Migration"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Database initialization command
    init_parser = subparsers.add_parser("init-db", help="Initialize database schema")
    init_parser.add_argument(
        "--db",
        type=str,
        default="dienstplan.db",
        help="Path to SQLite database (default: dienstplan.db)"
    )
    init_parser.add_argument(
        "--with-sample-data",
        action="store_true",
        help="Include sample teams and data"
    )
    
    # CLI planning command
    plan_parser = subparsers.add_parser("plan", help="Run shift planning")
    plan_parser.add_argument(
        "--start-date",
        type=str,
        required=True,
        help="Start date (YYYY-MM-DD)"
    )
    plan_parser.add_argument(
        "--end-date",
        type=str,
        required=True,
        help="End date (YYYY-MM-DD)"
    )
    plan_parser.add_argument(
        "--sample-data",
        action="store_true",
        help="Use generated sample data instead of database"
    )
    plan_parser.add_argument(
        "--db",
        type=str,
        default="dienstplan.db",
        help="Path to SQLite database (default: dienstplan.db)"
    )
    plan_parser.add_argument(
        "--time-limit",
        type=int,
        default=300,
        help="Solver time limit in seconds (default: 300)"
    )
    
    # Web server command
    server_parser = subparsers.add_parser("serve", help="Start web server")
    server_parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    server_parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to bind to (default: 5000)"
    )
    server_parser.add_argument(
        "--db",
        type=str,
        default="dienstplan.db",
        help="Path to SQLite database (default: dienstplan.db)"
    )
    server_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (WARNING: Only for development!)"
    )
    
    args = parser.parse_args()
    
    if args.command == "init-db":
        initialize_database(args.db, with_sample_data=args.with_sample_data)
        return 0
    
    elif args.command == "plan":
        start_date = date.fromisoformat(args.start_date)
        end_date = date.fromisoformat(args.end_date)
        return run_cli_planning(
            start_date,
            end_date,
            args.sample_data,
            args.db,
            args.time_limit
        )
    
    elif args.command == "serve":
        start_web_server(args.host, args.port, args.db, args.debug)
        return 0
    
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
