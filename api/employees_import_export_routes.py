"""Employee and team CSV import/export API routes."""

import logging
from datetime import datetime

from fastapi import APIRouter, Request, Depends, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse

from .shared import get_db, require_role, check_csrf

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get('/api/employees/export/csv', dependencies=[Depends(require_role('Admin'))])
def export_employees_csv(request: Request):
    """
    Export all employees to CSV format.
    
    Returns a CSV file with all employee data for backup or migration.
    """
    import csv
    from io import StringIO
    
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get all employees with their data
        cursor.execute("""
            SELECT Vorname, Name, Personalnummer, Email, Geburtsdatum, Funktion,
                   TeamId, IsFerienjobber, IsBrandmeldetechniker,
                   IsBrandschutzbeauftragter, IsTdQualified, IsTeamLeader, IsActive
            FROM Employees
            WHERE Id > 1
            ORDER BY TeamId, Name
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Vorname', 'Name', 'Personalnummer', 'Email', 'Geburtsdatum', 'Funktion',
            'TeamId', 'IsFerienjobber', 'IsBrandmeldetechniker',
            'IsBrandschutzbeauftragter', 'IsTdQualified', 'IsTeamLeader', 'IsActive'
        ])
        
        # Write data
        for row in rows:
            writer.writerow(row)
        
        # Prepare response
        output.seek(0)
        from io import BytesIO
        output_bytes = BytesIO(output.getvalue().encode('utf-8-sig'))  # UTF-8 with BOM for Excel
        output_bytes.seek(0)
        
        return StreamingResponse(
            output_bytes,
            media_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename=employees_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
        )
        
    except Exception as e:
        logger.error(f"Export employees error: {str(e)}")
        return JSONResponse(content={'error': str(e)}, status_code=500)


@router.get('/api/teams/export/csv', dependencies=[Depends(require_role('Admin'))])
def export_teams_csv(request: Request):
    """
    Export all teams to CSV format.
    
    Returns a CSV file with all team data for backup or migration.
    """
    import csv
    from io import StringIO
    
    try:
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Get all teams
        cursor.execute("""
            SELECT Name, Description, Email
            FROM Teams
            ORDER BY Name
        """)
        
        rows = cursor.fetchall()
        conn.close()
        
        # Create CSV in memory
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Name', 'Description', 'Email'])
        
        # Write data
        for row in rows:
            writer.writerow(row)
        
        # Prepare response
        output.seek(0)
        from io import BytesIO
        output_bytes = BytesIO(output.getvalue().encode('utf-8-sig'))  # UTF-8 with BOM for Excel
        output_bytes.seek(0)
        
        return StreamingResponse(
            output_bytes,
            media_type='text/csv',
            headers={'Content-Disposition': f'attachment; filename=teams_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'}
        )
        
    except Exception as e:
        logger.error(f"Export teams error: {str(e)}")
        return JSONResponse(content={'error': str(e)}, status_code=500)


@router.post('/api/employees/import/csv', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def import_employees_csv(request: Request, file: UploadFile = File(...)):
    """
    Import employees from CSV file.
    
    Supports conflict resolution:
    - overwrite: Replace existing employees (matched by Personalnummer)
    - skip: Skip existing employees, only add new ones
    
    Query parameters:
    - conflict_mode: 'overwrite' or 'skip' (default: 'skip')
    """
    import csv
    from io import StringIO
    
    try:
        if file.filename == '':
            return JSONResponse(content={'error': 'No file selected'}, status_code=400)
        
        # Get conflict mode from query parameter
        conflict_mode = request.query_params.get('conflict_mode', 'skip')
        if conflict_mode not in ['overwrite', 'skip']:
            return JSONResponse(content={'error': 'Invalid conflict_mode. Use "overwrite" or "skip"'}, status_code=400)
        
        # Read CSV file
        # Try to detect encoding (UTF-8 with BOM, UTF-8, or Latin-1)
        content = file.file.read()
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                text = content.decode('latin-1')
        
        csv_file = StringIO(text)
        reader = csv.DictReader(csv_file)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        imported_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        total_rows = 0
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
            total_rows += 1
            try:
                # Validate required fields
                required_fields = ['Vorname', 'Name', 'Personalnummer']
                missing_fields = [field for field in required_fields if field not in row or not row[field]]
                if missing_fields:
                    errors.append(f"Row {row_num}: Missing required fields: {', '.join(missing_fields)}")
                    continue  # Skip to next row
                
                # Check if employee already exists
                cursor.execute("""
                    SELECT Id FROM Employees WHERE Personalnummer = ?
                """, (row['Personalnummer'],))
                
                existing = cursor.fetchone()
                
                # Prepare values with defaults for optional fields
                values = {
                    'Vorname': row['Vorname'],
                    'Name': row['Name'],
                    'Personalnummer': row['Personalnummer'],
                    'Email': row.get('Email', ''),
                    'Geburtsdatum': row.get('Geburtsdatum', None),
                    'Funktion': row.get('Funktion', ''),
                    'TeamId': int(row['TeamId']) if row.get('TeamId') and row['TeamId'].strip() else None,
                    'IsFerienjobber': int(row.get('IsFerienjobber', 0)),
                    'IsBrandmeldetechniker': int(row.get('IsBrandmeldetechniker', 0)),
                    'IsBrandschutzbeauftragter': int(row.get('IsBrandschutzbeauftragter', 0)),
                    'IsTdQualified': int(row.get('IsTdQualified', 0)),
                    'IsTeamLeader': int(row.get('IsTeamLeader', 0)),
                    'IsActive': int(row.get('IsActive', 1))
                }
                
                if existing:
                    if conflict_mode == 'overwrite':
                        # Update existing employee
                        cursor.execute("""
                            UPDATE Employees
                            SET Vorname = ?, Name = ?, Email = ?, Geburtsdatum = ?,
                                Funktion = ?, TeamId = ?, IsFerienjobber = ?,
                                IsBrandmeldetechniker = ?, IsBrandschutzbeauftragter = ?,
                                IsTdQualified = ?, IsTeamLeader = ?, IsActive = ?
                            WHERE Personalnummer = ?
                        """, (
                            values['Vorname'], values['Name'], values['Email'],
                            values['Geburtsdatum'], values['Funktion'], values['TeamId'],
                            values['IsFerienjobber'],
                            values['IsBrandmeldetechniker'], values['IsBrandschutzbeauftragter'],
                            values['IsTdQualified'], values['IsTeamLeader'], values['IsActive'],
                            values['Personalnummer']
                        ))
                        updated_count += 1
                    else:
                        # Skip existing employee
                        skipped_count += 1
                else:
                    # Insert new employee
                    cursor.execute("""
                        INSERT INTO Employees
                        (Vorname, Name, Personalnummer, Email, Geburtsdatum, Funktion,
                         TeamId, IsFerienjobber, IsBrandmeldetechniker,
                         IsBrandschutzbeauftragter, IsTdQualified, IsTeamLeader, IsActive)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        values['Vorname'], values['Name'], values['Personalnummer'],
                        values['Email'], values['Geburtsdatum'], values['Funktion'],
                        values['TeamId'], values['IsFerienjobber'],
                        values['IsBrandmeldetechniker'], values['IsBrandschutzbeauftragter'],
                        values['IsTdQualified'], values['IsTeamLeader'], values['IsActive']
                    ))
                    imported_count += 1
                    
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'total': total_rows,
            'imported': imported_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"Import employees error: {str(e)}")
        return JSONResponse(content={'error': str(e)}, status_code=500)


@router.post('/api/teams/import/csv', dependencies=[Depends(require_role('Admin')), Depends(check_csrf)])
def import_teams_csv(request: Request, file: UploadFile = File(...)):
    """
    Import teams from CSV file.
    
    Supports conflict resolution:
    - overwrite: Replace existing teams (matched by Name)
    - skip: Skip existing teams, only add new ones
    
    Query parameters:
    - conflict_mode: 'overwrite' or 'skip' (default: 'skip')
    """
    import csv
    from io import StringIO
    
    try:
        if file.filename == '':
            return JSONResponse(content={'error': 'No file selected'}, status_code=400)
        
        # Get conflict mode from query parameter
        conflict_mode = request.query_params.get('conflict_mode', 'skip')
        if conflict_mode not in ['overwrite', 'skip']:
            return JSONResponse(content={'error': 'Invalid conflict_mode. Use "overwrite" or "skip"'}, status_code=400)
        
        # Read CSV file
        content = file.file.read()
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                text = content.decode('utf-8')
            except UnicodeDecodeError:
                text = content.decode('latin-1')
        
        csv_file = StringIO(text)
        reader = csv.DictReader(csv_file)
        
        db = get_db()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        imported_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        total_rows = 0
        
        for row_num, row in enumerate(reader, start=2):
            total_rows += 1
            try:
                # Validate required fields
                if 'Name' not in row or not row['Name']:
                    errors.append(f"Row {row_num}: Missing required field 'Name'")
                    continue
                
                # Check if team already exists
                cursor.execute("""
                    SELECT Id FROM Teams WHERE Name = ?
                """, (row['Name'],))
                
                existing = cursor.fetchone()
                
                # Prepare values
                values = {
                    'Name': row['Name'],
                    'Description': row.get('Description', ''),
                    'Email': row.get('Email', ''),
                    
                }
                
                if existing:
                    if conflict_mode == 'overwrite':
                        # Update existing team
                        cursor.execute("""
                            UPDATE Teams
                            SET Description = ?, Email = ?
                            WHERE Name = ?
                        """, (
                            values['Description'], values['Email'],
                            values['Name']
                        ))
                        updated_count += 1
                    else:
                        # Skip existing team
                        skipped_count += 1
                else:
                    # Insert new team
                    cursor.execute("""
                        INSERT INTO Teams (Name, Description, Email)
                        VALUES (?, ?, ?)
                    """, (
                        values['Name'], values['Description'],
                        values['Email']
                    ))
                    imported_count += 1
                    
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'total': total_rows,
            'imported': imported_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'errors': errors
        }
        
    except Exception as e:
        logger.error(f"Import teams error: {str(e)}")
        return JSONResponse(content={'error': str(e)}, status_code=500)
