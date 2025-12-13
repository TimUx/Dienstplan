"""
Main entry point for the Python OR-Tools shift planning system.
Provides both CLI and web server interfaces.
"""

import argparse
import sys
from datetime import date, timedelta
from typing import Optional

from data_loader import generate_sample_data, load_from_database
from model import create_shift_planning_model
from solver import solve_shift_planning
from validation import validate_shift_plan


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
    print("=" * 60)
    print("SHIFT PLANNING SYSTEM - Python OR-Tools Migration")
    print("=" * 60)
    print()
    
    # Load data
    if use_sample_data:
        print("Loading sample data...")
        employees, teams, absences = generate_sample_data()
    else:
        print(f"Loading data from database: {db_path}")
        try:
            employees, teams, absences = load_from_database(db_path)
        except Exception as e:
            print(f"Error loading database: {e}")
            print("Using sample data instead...")
            employees, teams, absences = generate_sample_data()
    
    print(f"  - Loaded {len(employees)} employees")
    print(f"  - Loaded {len(teams)} teams")
    print(f"  - Loaded {len(absences)} absences")
    print()
    
    # Create model
    print(f"Creating planning model for {start_date} to {end_date}...")
    planning_model = create_shift_planning_model(
        employees, start_date, end_date, absences
    )
    planning_model.print_model_statistics()
    
    # Solve
    print("\nSolving shift planning problem...")
    result = solve_shift_planning(planning_model, time_limit_seconds=time_limit)
    
    if not result:
        print("\n✗ No solution found!")
        return 1
    
    assignments, special_functions = result
    print(f"\n✓ Solution found!")
    print(f"  - Total assignments: {len(assignments)}")
    print(f"  - Special functions: {len(special_functions)}")
    
    # Validate
    print("\nValidating solution...")
    validation_result = validate_shift_plan(
        assignments, employees, absences, start_date, end_date
    )
    validation_result.print_report()
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY BY TEAM")
    print("=" * 60)
    
    for team in teams:
        print(f"\n{team.name}:")
        team_employees = [emp for emp in employees if emp.team_id == team.id]
        for emp in team_employees:
            emp_assignments = [a for a in assignments if a.employee_id == emp.id]
            print(f"  {emp.full_name}: {len(emp_assignments)} shifts")
    
    # Springers
    springers = [emp for emp in employees if emp.is_springer]
    if springers:
        print(f"\nSpringer:")
        for emp in springers:
            emp_assignments = [a for a in assignments if a.employee_id == emp.id]
            print(f"  {emp.full_name}: {len(emp_assignments)} shifts")
    
    print("\n" + "=" * 60)
    
    # Save results if database mode
    if not use_sample_data:
        print("\nSaving results to database...")
        try:
            save_assignments_to_database(assignments, db_path)
            print("✓ Results saved successfully!")
        except Exception as e:
            print(f"✗ Error saving results: {e}")
    
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
            (EmployeeId, ShiftTypeId, Date, IsManual, IsSpringerAssignment, IsFixed, CreatedAt, CreatedBy)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            assignment.employee_id,
            assignment.shift_type_id,
            assignment.date.isoformat(),
            0,  # IsManual = False (automatic)
            1 if assignment.is_springer_assignment else 0,
            0,  # IsFixed = False
            datetime.utcnow().isoformat(),
            "Python-OR-Tools"
        ))
    
    conn.commit()
    conn.close()


def start_web_server(host: str = "0.0.0.0", port: int = 5000, db_path: str = "dienstplan.db", debug: bool = False):
    """
    Start Flask web server with REST API.
    This provides the backend for the existing .NET Web UI.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        db_path: Path to SQLite database
        debug: Enable debug mode (WARNING: Only use in development!)
    """
    from web_api import create_app
    
    print("=" * 60)
    print("SHIFT PLANNING WEB SERVER - Python OR-Tools Backend")
    print("=" * 60)
    print(f"Starting web server on http://{host}:{port}")
    print(f"Database: {db_path}")
    if debug:
        print("⚠️  WARNING: Debug mode enabled - DO NOT use in production!")
    print()
    print("The existing Web UI from .NET version is compatible with this backend.")
    print("=" * 60)
    print()
    
    app = create_app(db_path)
    app.run(host=host, port=port, debug=debug)


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Shift Planning System - Python OR-Tools Migration"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
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
    
    if args.command == "plan":
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
