#!/usr/bin/env python3
"""
Dienstplan System Information Export Script

This script extracts all necessary information from the Dienstplan system
and formats it for analysis by Copilot Agents.

Exports:
- Database schema and relationships
- Global settings and configurations
- Shift types and their properties
- Teams and employees
- Absences and vacation requests
- Shift assignments
- Rotation groups and patterns
- Email configuration
- Statistics and summaries

Usage:
    python export_system_info.py [--db dienstplan.db] [--output info.txt]
    python export_system_info.py --help
"""

import argparse
import sqlite3
import sys
from datetime import date, datetime
from typing import Dict, List, Any, Optional
import json


class SystemInfoExporter:
    """Exports comprehensive system information from Dienstplan database"""
    
    def __init__(self, db_path: str):
        """
        Initialize exporter with database path.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    def __enter__(self):
        """Context manager entry - connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close database connection"""
        if self.conn:
            self.conn.close()
            
    def export_all(self) -> str:
        """
        Export all system information as formatted text.
        
        Returns:
            Formatted string with all system information
        """
        output = []
        
        # Header
        output.append("=" * 80)
        output.append("DIENSTPLAN SYSTEM INFORMATION EXPORT")
        output.append("=" * 80)
        output.append(f"Export Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        output.append(f"Database: {self.db_path}")
        output.append("=" * 80)
        output.append("")
        
        # Export each section
        sections = [
            ("DATABASE SCHEMA", self._export_schema),
            ("GLOBAL SETTINGS", self._export_global_settings),
            ("EMAIL SETTINGS", self._export_email_settings),
            ("SHIFT TYPES", self._export_shift_types),
            ("TEAMS", self._export_teams),
            ("EMPLOYEES", self._export_employees),
            ("ABSENCES", self._export_absences),
            ("ABSENCE TYPES", self._export_absence_types),
            ("VACATION REQUESTS", self._export_vacation_requests),
            ("VACATION PERIODS", self._export_vacation_periods),
            ("SHIFT ASSIGNMENTS", self._export_shift_assignments),
            ("ROTATION GROUPS", self._export_rotation_groups),
            ("TEAM-SHIFT ASSIGNMENTS", self._export_team_shift_assignments),
            ("SHIFT EXCHANGES", self._export_shift_exchanges),
            ("STATISTICS", self._export_statistics),
        ]
        
        for title, export_func in sections:
            output.append("")
            output.append("-" * 80)
            output.append(f"SECTION: {title}")
            output.append("-" * 80)
            output.append("")
            
            try:
                section_content = export_func()
                output.append(section_content)
            except Exception as e:
                output.append(f"[ERROR] Failed to export {title}: {str(e)}")
                output.append("")
        
        # Footer
        output.append("")
        output.append("=" * 80)
        output.append("END OF EXPORT")
        output.append("=" * 80)
        
        return "\n".join(output)
    
    def _export_schema(self) -> str:
        """Export database schema information"""
        output = []
        
        # Get all tables
        self.cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        tables = [row['name'] for row in self.cursor.fetchall()]
        
        output.append(f"Total Tables: {len(tables)}")
        output.append("")
        
        for table in tables:
            # Get table schema
            self.cursor.execute(f"PRAGMA table_info({table})")
            columns = self.cursor.fetchall()
            
            output.append(f"Table: {table}")
            output.append(f"  Columns ({len(columns)}):")
            for col in columns:
                null_constraint = "NOT NULL" if col['notnull'] else "NULL"
                pk_marker = " [PRIMARY KEY]" if col['pk'] else ""
                default_val = f" DEFAULT {col['dflt_value']}" if col['dflt_value'] else ""
                output.append(f"    - {col['name']}: {col['type']} {null_constraint}{default_val}{pk_marker}")
            
            # Get row count
            self.cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = self.cursor.fetchone()['count']
            output.append(f"  Row Count: {count}")
            output.append("")
        
        return "\n".join(output)
    
    def _export_global_settings(self) -> str:
        """Export global shift planning settings"""
        output = []
        
        try:
            self.cursor.execute("SELECT * FROM GlobalSettings WHERE Id = 1")
            settings = self.cursor.fetchone()
            
            if settings:
                output.append("Global Shift Planning Configuration:")
                output.append(f"  Max Consecutive Shifts (weeks): {settings['MaxConsecutiveShifts']}")
                output.append(f"  Max Consecutive Night Shifts (weeks): {settings['MaxConsecutiveNightShifts']}")
                output.append(f"  Min Rest Hours Between Shifts: {settings['MinRestHoursBetweenShifts']}")
                if settings['ModifiedAt']:
                    output.append(f"  Last Modified: {settings['ModifiedAt']}")
                if settings['ModifiedBy']:
                    output.append(f"  Modified By: {settings['ModifiedBy']}")
                output.append("")
                output.append("NOTE: Max consecutive settings are DEPRECATED.")
                output.append("      Now configured per shift type (ShiftType.MaxConsecutiveDays)")
            else:
                output.append("No global settings found in database.")
        except Exception as e:
            output.append(f"Error loading global settings: {e}")
        
        return "\n".join(output)
    
    def _export_email_settings(self) -> str:
        """Export email/SMTP configuration"""
        output = []
        
        try:
            self.cursor.execute("SELECT * FROM EmailSettings WHERE Id = 1")
            settings = self.cursor.fetchone()
            
            if settings:
                output.append("Email/SMTP Configuration:")
                output.append(f"  Enabled: {'Yes' if settings['IsEnabled'] else 'No'}")
                output.append(f"  SMTP Host: {settings['SmtpHost'] or 'Not configured'}")
                output.append(f"  SMTP Port: {settings['SmtpPort']}")
                output.append(f"  Use SSL: {'Yes' if settings['UseSsl'] else 'No'}")
                output.append(f"  Requires Authentication: {'Yes' if settings['RequiresAuthentication'] else 'No'}")
                output.append(f"  Username: {settings['Username'] or 'Not set'}")
                output.append(f"  Password: {'***' if settings['Password'] else 'Not set'}")
                output.append(f"  Sender Email: {settings['SenderEmail'] or 'Not set'}")
                output.append(f"  Sender Name: {settings['SenderName'] or 'Not set'}")
                output.append(f"  Reply-To Email: {settings['ReplyToEmail'] or 'Not set'}")
            else:
                output.append("No email settings found in database.")
        except Exception as e:
            output.append(f"Error loading email settings: {e}")
        
        return "\n".join(output)
    
    def _export_shift_types(self) -> str:
        """Export all shift type configurations"""
        output = []
        
        self.cursor.execute("""
            SELECT * FROM ShiftTypes 
            ORDER BY Id
        """)
        shift_types = self.cursor.fetchall()
        
        output.append(f"Total Shift Types: {len(shift_types)}")
        output.append("")
        
        for st in shift_types:
            active_status = "ACTIVE" if st['IsActive'] else "INACTIVE"
            output.append(f"Shift Type [{st['Id']}]: {st['Name']} ({st['Code']}) - {active_status}")
            output.append(f"  Time: {st['StartTime']} - {st['EndTime']} ({st['DurationHours']}h)")
            output.append(f"  Color: {st['ColorCode'] or 'Not set'}")
            output.append(f"  Weekly Working Hours: {st['WeeklyWorkingHours']}h")
            
            # Work days
            work_days = []
            if st['WorksMonday']: work_days.append("Mo")
            if st['WorksTuesday']: work_days.append("Tu")
            if st['WorksWednesday']: work_days.append("We")
            if st['WorksThursday']: work_days.append("Th")
            if st['WorksFriday']: work_days.append("Fr")
            if st['WorksSaturday']: work_days.append("Sa")
            if st['WorksSunday']: work_days.append("Su")
            output.append(f"  Work Days: {', '.join(work_days)}")
            
            # Staffing requirements
            output.append(f"  Weekday Staff: Min {st['MinStaffWeekday']}, Max {st['MaxStaffWeekday']}")
            output.append(f"  Weekend Staff: Min {st['MinStaffWeekend']}, Max {st['MaxStaffWeekend']}")
            output.append(f"  Max Consecutive Days: {st['MaxConsecutiveDays']}")
            
            if st['CreatedAt']:
                output.append(f"  Created: {st['CreatedAt']}")
            output.append("")
        
        return "\n".join(output)
    
    def _export_teams(self) -> str:
        """Export all teams"""
        output = []
        
        self.cursor.execute("""
            SELECT * FROM Teams 
            ORDER BY Id
        """)
        teams = self.cursor.fetchall()
        
        output.append(f"Total Teams: {len(teams)}")
        output.append("")
        
        for team in teams:
            virtual_marker = " [VIRTUAL]" if team['IsVirtual'] else ""
            output.append(f"Team [{team['Id']}]: {team['Name']}{virtual_marker}")
            if team['Description']:
                output.append(f"  Description: {team['Description']}")
            if team['Email']:
                output.append(f"  Email: {team['Email']}")
            if team['RotationGroupId']:
                output.append(f"  Rotation Group ID: {team['RotationGroupId']}")
            
            # Count employees in team
            self.cursor.execute("SELECT COUNT(*) as count FROM Employees WHERE TeamId = ?", (team['Id'],))
            emp_count = self.cursor.fetchone()['count']
            output.append(f"  Employees: {emp_count}")
            output.append("")
        
        return "\n".join(output)
    
    def _export_employees(self) -> str:
        """Export all employees with details"""
        output = []
        
        self.cursor.execute("""
            SELECT e.*, t.Name as TeamName 
            FROM Employees e
            LEFT JOIN Teams t ON e.TeamId = t.Id
            ORDER BY e.TeamId, e.Name
        """)
        employees = self.cursor.fetchall()
        
        output.append(f"Total Employees: {len(employees)}")
        output.append("")
        
        current_team = None
        for emp in employees:
            team_name = emp['TeamName'] or "No Team"
            if current_team != team_name:
                current_team = team_name
                output.append(f"--- {team_name} ---")
                output.append("")
            
            active_status = "ACTIVE" if emp['IsActive'] else "INACTIVE"
            output.append(f"Employee [{emp['Id']}]: {emp['Vorname']} {emp['Name']} - {active_status}")
            output.append(f"  Personnel Number: {emp['Personalnummer']}")
            output.append(f"  Email: {emp['Email'] or 'Not set'}")
            if emp['Geburtsdatum']:
                output.append(f"  Birth Date: {emp['Geburtsdatum']}")
            if emp['Funktion']:
                output.append(f"  Function: {emp['Funktion']}")
            
            # Qualifications
            qualifications = []
            if emp['IsBrandmeldetechniker']:
                qualifications.append("BMT (Brandmeldetechniker)")
            if emp['IsBrandschutzbeauftragter']:
                qualifications.append("BSB (Brandschutzbeauftragter)")
            if emp['IsTdQualified']:
                qualifications.append("TD Qualified")
            if emp['IsTeamLeader']:
                qualifications.append("Team Leader")
            if emp['IsFerienjobber']:
                qualifications.append("Ferienjobber (Temporary)")
            if emp['IsSpringer']:
                qualifications.append("Springer (Substitute)")
            
            if qualifications:
                output.append(f"  Qualifications: {', '.join(qualifications)}")
            
            # Authentication info (without sensitive data)
            if emp['PasswordHash']:
                output.append(f"  Authentication: Configured")
            else:
                output.append(f"  Authentication: Not configured")
            
            if emp['LockoutEnd']:
                output.append(f"  Account Status: LOCKED until {emp['LockoutEnd']}")
            
            output.append("")
        
        return "\n".join(output)
    
    def _export_absences(self) -> str:
        """Export all absences"""
        output = []
        
        self.cursor.execute("""
            SELECT a.*, e.Vorname, e.Name, at.Code as AbsenceCode, at.Name as AbsenceName
            FROM Absences a
            JOIN Employees e ON a.EmployeeId = e.Id
            LEFT JOIN AbsenceTypes at ON a.AbsenceTypeId = at.Id
            ORDER BY a.StartDate DESC
        """)
        absences = self.cursor.fetchall()
        
        output.append(f"Total Absences: {len(absences)}")
        output.append("")
        
        # Group by employee
        emp_absences = {}
        for absence in absences:
            emp_name = f"{absence['Vorname']} {absence['Name']}"
            if emp_name not in emp_absences:
                emp_absences[emp_name] = []
            emp_absences[emp_name].append(absence)
        
        for emp_name, abs_list in emp_absences.items():
            output.append(f"{emp_name}: {len(abs_list)} absence(s)")
            for absence in abs_list:
                # Get absence type description
                if absence['AbsenceCode']:
                    absence_type = f"{absence['AbsenceCode']} - {absence['AbsenceName']}"
                else:
                    # Legacy type mapping
                    type_map = {1: "AU (Krank)", 2: "U (Urlaub)", 3: "L (Lehrgang)"}
                    absence_type = type_map.get(absence['Type'], f"Type {absence['Type']}")
                
                output.append(f"  [{absence['Id']}] {absence_type}: {absence['StartDate']} to {absence['EndDate']}")
                if absence['Notes']:
                    output.append(f"      Notes: {absence['Notes']}")
            output.append("")
        
        return "\n".join(output)
    
    def _export_absence_types(self) -> str:
        """Export absence type definitions"""
        output = []
        
        try:
            self.cursor.execute("""
                SELECT * FROM AbsenceTypes 
                ORDER BY IsSystemType DESC, Name
            """)
            absence_types = self.cursor.fetchall()
            
            output.append(f"Total Absence Types: {len(absence_types)}")
            output.append("")
            
            for at in absence_types:
                type_marker = "[SYSTEM]" if at['IsSystemType'] else "[CUSTOM]"
                output.append(f"{type_marker} {at['Name']} ({at['Code']})")
                output.append(f"  Color: {at['ColorCode']}")
                if at['CreatedAt']:
                    output.append(f"  Created: {at['CreatedAt']}")
                output.append("")
        except Exception as e:
            output.append(f"Absence types table not available: {e}")
        
        return "\n".join(output)
    
    def _export_vacation_requests(self) -> str:
        """Export vacation requests"""
        output = []
        
        self.cursor.execute("""
            SELECT vr.*, e.Vorname, e.Name
            FROM VacationRequests vr
            JOIN Employees e ON vr.EmployeeId = e.Id
            ORDER BY vr.CreatedAt DESC
        """)
        requests = self.cursor.fetchall()
        
        output.append(f"Total Vacation Requests: {len(requests)}")
        output.append("")
        
        # Group by status
        status_groups = {}
        for req in requests:
            status = req['Status']
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(req)
        
        for status, req_list in status_groups.items():
            output.append(f"Status: {status} ({len(req_list)})")
            for req in req_list:
                emp_name = f"{req['Vorname']} {req['Name']}"
                output.append(f"  [{req['Id']}] {emp_name}: {req['StartDate']} to {req['EndDate']}")
                if req['Notes']:
                    output.append(f"      Notes: {req['Notes']}")
                if req['DisponentResponse']:
                    output.append(f"      Response: {req['DisponentResponse']}")
                if req['ProcessedBy']:
                    output.append(f"      Processed by: {req['ProcessedBy']} at {req['ProcessedAt']}")
            output.append("")
        
        return "\n".join(output)
    
    def _export_vacation_periods(self) -> str:
        """Export vacation periods (Ferienzeiten)"""
        output = []
        
        try:
            self.cursor.execute("""
                SELECT * FROM VacationPeriods 
                ORDER BY StartDate
            """)
            periods = self.cursor.fetchall()
            
            output.append(f"Total Vacation Periods: {len(periods)}")
            output.append("")
            
            for period in periods:
                output.append(f"[{period['Id']}] {period['Name']}: {period['StartDate']} to {period['EndDate']}")
                if period['ColorCode']:
                    output.append(f"  Color: {period['ColorCode']}")
            output.append("")
        except Exception as e:
            output.append(f"Vacation periods table not available: {e}")
        
        return "\n".join(output)
    
    def _export_shift_assignments(self) -> str:
        """Export shift assignments with statistics"""
        output = []
        
        self.cursor.execute("""
            SELECT 
                sa.*,
                e.Vorname, e.Name,
                st.Code as ShiftCode, st.Name as ShiftName
            FROM ShiftAssignments sa
            JOIN Employees e ON sa.EmployeeId = e.Id
            JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
            ORDER BY sa.Date DESC, e.Name
            LIMIT 100
        """)
        assignments = self.cursor.fetchall()
        
        # Get total count
        self.cursor.execute("SELECT COUNT(*) as count FROM ShiftAssignments")
        total_count = self.cursor.fetchone()['count']
        
        output.append(f"Total Shift Assignments: {total_count}")
        output.append(f"Showing: Latest {min(100, total_count)} assignments")
        output.append("")
        
        # Show recent assignments
        current_date = None
        for assignment in assignments:
            if current_date != assignment['Date']:
                current_date = assignment['Date']
                output.append(f"Date: {current_date}")
            
            emp_name = f"{assignment['Vorname']} {assignment['Name']}"
            shift_info = f"{assignment['ShiftCode']} ({assignment['ShiftName']})"
            
            markers = []
            if assignment['IsManual']:
                markers.append("MANUAL")
            if assignment['IsFixed']:
                markers.append("FIXED")
            if assignment['IsSpringerAssignment']:
                markers.append("SPRINGER")
            
            marker_str = f" [{', '.join(markers)}]" if markers else ""
            
            output.append(f"  {emp_name} -> {shift_info}{marker_str}")
            if assignment['Notes']:
                output.append(f"    Notes: {assignment['Notes']}")
        
        output.append("")
        
        # Statistics by shift type
        output.append("Statistics by Shift Type:")
        self.cursor.execute("""
            SELECT 
                st.Code, st.Name,
                COUNT(*) as count
            FROM ShiftAssignments sa
            JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
            GROUP BY st.Id
            ORDER BY count DESC
        """)
        stats = self.cursor.fetchall()
        for stat in stats:
            output.append(f"  {stat['Code']} ({stat['Name']}): {stat['count']} assignments")
        
        return "\n".join(output)
    
    def _export_rotation_groups(self) -> str:
        """Export rotation groups and patterns"""
        output = []
        
        try:
            self.cursor.execute("""
                SELECT * FROM RotationGroups 
                WHERE IsActive = 1
                ORDER BY Id
            """)
            groups = self.cursor.fetchall()
            
            output.append(f"Total Active Rotation Groups: {len(groups)}")
            output.append("")
            
            for group in groups:
                output.append(f"Rotation Group [{group['Id']}]: {group['Name']}")
                if group['Description']:
                    output.append(f"  Description: {group['Description']}")
                
                # Get shifts in this rotation group
                self.cursor.execute("""
                    SELECT st.Code, st.Name, rgs.RotationOrder
                    FROM RotationGroupShifts rgs
                    JOIN ShiftTypes st ON st.Id = rgs.ShiftTypeId
                    WHERE rgs.RotationGroupId = ?
                    ORDER BY rgs.RotationOrder
                """, (group['Id'],))
                shifts = self.cursor.fetchall()
                
                if shifts:
                    shift_codes = [s['Code'] for s in shifts]
                    output.append(f"  Rotation Pattern: {' -> '.join(shift_codes)}")
                    output.append(f"  Shifts ({len(shifts)}):")
                    for shift in shifts:
                        output.append(f"    {shift['RotationOrder']}. {shift['Code']} - {shift['Name']}")
                else:
                    output.append(f"  No shifts configured")
                
                # Count teams using this rotation
                self.cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM Teams 
                    WHERE RotationGroupId = ?
                """, (group['Id'],))
                team_count = self.cursor.fetchone()['count']
                output.append(f"  Used by {team_count} team(s)")
                
                output.append("")
        except Exception as e:
            output.append(f"Rotation groups table not available: {e}")
        
        return "\n".join(output)
    
    def _export_team_shift_assignments(self) -> str:
        """Export which teams can work which shifts"""
        output = []
        
        try:
            self.cursor.execute("""
                SELECT t.Name as TeamName, st.Code as ShiftCode, st.Name as ShiftName
                FROM TeamShiftAssignments tsa
                JOIN Teams t ON tsa.TeamId = t.Id
                JOIN ShiftTypes st ON tsa.ShiftTypeId = st.Id
                ORDER BY t.Name, st.Code
            """)
            assignments = self.cursor.fetchall()
            
            output.append(f"Total Team-Shift Assignments: {len(assignments)}")
            output.append("")
            
            # Group by team
            team_shifts = {}
            for assignment in assignments:
                team_name = assignment['TeamName']
                if team_name not in team_shifts:
                    team_shifts[team_name] = []
                team_shifts[team_name].append(f"{assignment['ShiftCode']} ({assignment['ShiftName']})")
            
            for team_name, shifts in team_shifts.items():
                output.append(f"{team_name}:")
                output.append(f"  Allowed Shifts: {', '.join(shifts)}")
                output.append("")
        except Exception as e:
            output.append(f"Team shift assignments table not available: {e}")
        
        return "\n".join(output)
    
    def _export_shift_exchanges(self) -> str:
        """Export shift exchange offers"""
        output = []
        
        try:
            self.cursor.execute("""
                SELECT 
                    se.*,
                    e1.Vorname || ' ' || e1.Name as OfferingEmployee,
                    e2.Vorname || ' ' || e2.Name as RequestingEmployee,
                    sa.Date as ShiftDate,
                    st.Code as ShiftCode
                FROM ShiftExchanges se
                JOIN Employees e1 ON se.OfferingEmployeeId = e1.Id
                LEFT JOIN Employees e2 ON se.RequestingEmployeeId = e2.Id
                JOIN ShiftAssignments sa ON se.ShiftAssignmentId = sa.Id
                JOIN ShiftTypes st ON sa.ShiftTypeId = st.Id
                ORDER BY se.CreatedAt DESC
            """)
            exchanges = self.cursor.fetchall()
            
            output.append(f"Total Shift Exchanges: {len(exchanges)}")
            output.append("")
            
            # Group by status
            status_groups = {}
            for exchange in exchanges:
                status = exchange['Status']
                if status not in status_groups:
                    status_groups[status] = []
                status_groups[status].append(exchange)
            
            for status, exch_list in status_groups.items():
                output.append(f"Status: {status} ({len(exch_list)})")
                for exch in exch_list:
                    output.append(f"  [{exch['Id']}] {exch['OfferingEmployee']} offers {exch['ShiftCode']} on {exch['ShiftDate']}")
                    if exch['RequestingEmployee']:
                        output.append(f"      Requested by: {exch['RequestingEmployee']}")
                    if exch['OfferingReason']:
                        output.append(f"      Reason: {exch['OfferingReason']}")
                    if exch['DisponentNotes']:
                        output.append(f"      Admin Notes: {exch['DisponentNotes']}")
                output.append("")
        except Exception as e:
            output.append(f"Shift exchanges table not available: {e}")
        
        return "\n".join(output)
    
    def _export_statistics(self) -> str:
        """Export various statistics about the system"""
        output = []
        
        # Employee statistics
        self.cursor.execute("SELECT COUNT(*) as count FROM Employees WHERE IsActive = 1")
        active_employees = self.cursor.fetchone()['count']
        
        self.cursor.execute("SELECT COUNT(*) as count FROM Employees WHERE IsActive = 0")
        inactive_employees = self.cursor.fetchone()['count']
        
        output.append("Employee Statistics:")
        output.append(f"  Active Employees: {active_employees}")
        output.append(f"  Inactive Employees: {inactive_employees}")
        output.append(f"  Total: {active_employees + inactive_employees}")
        output.append("")
        
        # Team statistics
        self.cursor.execute("SELECT COUNT(*) as count FROM Teams WHERE IsVirtual = 0")
        regular_teams = self.cursor.fetchone()['count']
        
        self.cursor.execute("SELECT COUNT(*) as count FROM Teams WHERE IsVirtual = 1")
        virtual_teams = self.cursor.fetchone()['count']
        
        output.append("Team Statistics:")
        output.append(f"  Regular Teams: {regular_teams}")
        output.append(f"  Virtual Teams: {virtual_teams}")
        output.append(f"  Total: {regular_teams + virtual_teams}")
        output.append("")
        
        # Shift assignment statistics
        self.cursor.execute("""
            SELECT 
                MIN(Date) as earliest,
                MAX(Date) as latest,
                COUNT(*) as total
            FROM ShiftAssignments
        """)
        shift_stats = self.cursor.fetchone()
        
        output.append("Shift Assignment Statistics:")
        output.append(f"  Total Assignments: {shift_stats['total']}")
        if shift_stats['earliest']:
            output.append(f"  Date Range: {shift_stats['earliest']} to {shift_stats['latest']}")
        output.append("")
        
        # Absence statistics
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN StartDate <= date('now') AND EndDate >= date('now') THEN 1 ELSE 0 END) as current
            FROM Absences
        """)
        absence_stats = self.cursor.fetchone()
        
        output.append("Absence Statistics:")
        output.append(f"  Total Absences: {absence_stats['total']}")
        output.append(f"  Current Absences: {absence_stats['current']}")
        output.append("")
        
        # Vacation request statistics
        self.cursor.execute("""
            SELECT Status, COUNT(*) as count
            FROM VacationRequests
            GROUP BY Status
        """)
        vacation_stats = self.cursor.fetchall()
        
        output.append("Vacation Request Statistics:")
        for stat in vacation_stats:
            output.append(f"  {stat['Status']}: {stat['count']}")
        
        return "\n".join(output)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Export Dienstplan system information for analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export to console
  python export_system_info.py
  
  # Export to file
  python export_system_info.py --output system_info.txt
  
  # Use specific database
  python export_system_info.py --db /path/to/dienstplan.db --output info.txt
        """
    )
    
    parser.add_argument(
        "--db",
        type=str,
        default="dienstplan.db",
        help="Path to SQLite database (default: dienstplan.db)"
    )
    
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: print to console)"
    )
    
    args = parser.parse_args()
    
    # Check if database exists
    import os
    if not os.path.exists(args.db):
        print(f"Error: Database file not found: {args.db}", file=sys.stderr)
        print("", file=sys.stderr)
        print("To create a database with sample data:", file=sys.stderr)
        print(f"  python main.py init-db --db {args.db} --with-sample-data", file=sys.stderr)
        return 1
    
    # Export system information
    try:
        with SystemInfoExporter(args.db) as exporter:
            output = exporter.export_all()
        
        # Write output
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"System information exported to: {args.output}")
        else:
            print(output)
        
        return 0
    
    except Exception as e:
        print(f"Error exporting system information: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
