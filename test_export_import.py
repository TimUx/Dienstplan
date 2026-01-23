"""
Test script for export/import functionality.
"""

import requests
import csv
from io import StringIO

# Note: This assumes the web server is NOT running
# We'll test by directly calling the functions

def test_export_import():
    """Test export/import functionality using the database directly"""
    import sqlite3
    from io import BytesIO
    
    db_path = "dienstplan.db"
    
    print("="*60)
    print("TESTING EXPORT/IMPORT FUNCTIONALITY")
    print("="*60)
    
    # Test 1: Export employees
    print("\n1. Testing employee export...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT Vorname, Name, Personalnummer, Email, Geburtsdatum, Funktion,
               TeamId, IsSpringer, IsFerienjobber, IsBrandmeldetechniker,
               IsBrandschutzbeauftragter, IsTdQualified, IsTeamLeader, IsActive
        FROM Employees
        WHERE Id > 1
        ORDER BY TeamId, Name
    """)
    
    employees = cursor.fetchall()
    print(f"   Found {len(employees)} employees")
    
    # Create CSV in memory
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Vorname', 'Name', 'Personalnummer', 'Email', 'Geburtsdatum', 'Funktion',
        'TeamId', 'IsSpringer', 'IsFerienjobber', 'IsBrandmeldetechniker',
        'IsBrandschutzbeauftragter', 'IsTdQualified', 'IsTeamLeader', 'IsActive'
    ])
    for row in employees:
        writer.writerow(row)
    
    csv_content = output.getvalue()
    print(f"   Generated CSV with {len(csv_content)} bytes")
    print(f"   First 200 chars: {csv_content[:200]}...")
    
    # Test 2: Export teams
    print("\n2. Testing team export...")
    cursor.execute("""
        SELECT Name, Description, Email, IsVirtual
        FROM Teams
        ORDER BY Name
    """)
    
    teams = cursor.fetchall()
    print(f"   Found {len(teams)} teams")
    
    output2 = StringIO()
    writer2 = csv.writer(output2)
    writer2.writerow(['Name', 'Description', 'Email', 'IsVirtual'])
    for row in teams:
        writer2.writerow(row)
    
    teams_csv = output2.getvalue()
    print(f"   Generated CSV with {len(teams_csv)} bytes")
    print(f"   Content:\n{teams_csv}")
    
    # Test 3: Import teams (test data)
    print("\n3. Testing team import (skip mode)...")
    test_teams_csv = """Name,Description,Email,IsVirtual
Team Delta,Fourth test team,delta@test.com,0
Team Alpha,Updated description,alpha-updated@test.com,0
"""
    
    # Parse CSV
    csv_file = StringIO(test_teams_csv)
    reader = csv.DictReader(csv_file)
    
    imported = 0
    updated = 0
    skipped = 0
    
    for row in reader:
        cursor.execute("SELECT Id FROM Teams WHERE Name = ?", (row['Name'],))
        existing = cursor.fetchone()
        
        if existing:
            print(f"   Team '{row['Name']}' exists - skipping")
            skipped += 1
        else:
            cursor.execute("""
                INSERT INTO Teams (Name, Description, Email, IsVirtual)
                VALUES (?, ?, ?, ?)
            """, (row['Name'], row['Description'], row['Email'], int(row['IsVirtual'])))
            print(f"   Imported team '{row['Name']}'")
            imported += 1
    
    conn.commit()
    
    print(f"   Result: imported={imported}, skipped={skipped}")
    
    # Test 4: Import employees (test data)
    print("\n4. Testing employee import (skip mode)...")
    test_employees_csv = """Vorname,Name,Personalnummer,Email,Geburtsdatum,Funktion,TeamId,IsSpringer,IsFerienjobber,IsBrandmeldetechniker,IsBrandschutzbeauftragter,IsTdQualified,IsTeamLeader,IsActive
John,Doe,9999,john.doe@test.com,1990-01-01,Tester,7,0,0,0,0,0,0,1
Max,Müller,1001,max.mueller@test.com,1985-05-15,Updated,7,0,0,1,0,1,0,1
"""
    
    csv_file2 = StringIO(test_employees_csv)
    reader2 = csv.DictReader(csv_file2)
    
    imported2 = 0
    skipped2 = 0
    
    for row in reader2:
        cursor.execute("SELECT Id FROM Employees WHERE Personalnummer = ?", (row['Personalnummer'],))
        existing = cursor.fetchone()
        
        if existing:
            print(f"   Employee {row['Personalnummer']} ({row['Vorname']} {row['Name']}) exists - skipping")
            skipped2 += 1
        else:
            cursor.execute("""
                INSERT INTO Employees
                (Vorname, Name, Personalnummer, Email, Geburtsdatum, Funktion,
                 TeamId, IsSpringer, IsFerienjobber, IsBrandmeldetechniker,
                 IsBrandschutzbeauftragter, IsTdQualified, IsTeamLeader, IsActive)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['Vorname'], row['Name'], row['Personalnummer'],
                row.get('Email', ''), row.get('Geburtsdatum', None), row.get('Funktion', ''),
                int(row['TeamId']) if row.get('TeamId') and row['TeamId'].strip() else None,
                int(row.get('IsSpringer', 0)), int(row.get('IsFerienjobber', 0)),
                int(row.get('IsBrandmeldetechniker', 0)), int(row.get('IsBrandschutzbeauftragter', 0)),
                int(row.get('IsTdQualified', 0)), int(row.get('IsTeamLeader', 0)),
                int(row.get('IsActive', 1))
            ))
            print(f"   Imported employee {row['Personalnummer']} ({row['Vorname']} {row['Name']})")
            imported2 += 1
    
    conn.commit()
    conn.close()
    
    print(f"   Result: imported={imported2}, skipped={skipped2}")
    
    print("\n" + "="*60)
    print("✓ EXPORT/IMPORT TESTS COMPLETED")
    print("="*60)
    

if __name__ == "__main__":
    test_export_import()
