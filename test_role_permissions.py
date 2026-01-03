"""
Test script for role-based access control.
Verifies that Admin and Mitarbeiter roles have correct permissions.
"""

import requests
import json
import sys

BASE_URL = "http://localhost:5000/api"

def test_admin_access():
    """Test Admin role has full access"""
    print("\n" + "=" * 60)
    print("TESTING ADMIN ROLE ACCESS")
    print("=" * 60)
    
    session = requests.Session()
    
    # Login as admin
    print("\n1. Login as Admin...")
    response = session.post(f"{BASE_URL}/auth/login", json={
        "email": "admin@fritzwinter.de",
        "password": "Admin123!"
    })
    
    if response.status_code != 200:
        print(f"✗ Admin login failed: {response.status_code}")
        return False
    
    print("✓ Admin login successful")
    
    # Test read operations
    print("\n2. Testing Admin read operations...")
    endpoints = [
        "/employees",
        "/teams",
        "/shifts/schedule?startDate=2025-01-01&view=week",
        "/users",
        "/roles",
        "/vacationrequests",
        "/shiftexchanges/available"
    ]
    
    all_passed = True
    for endpoint in endpoints:
        response = session.get(f"{BASE_URL}{endpoint}")
        if response.status_code == 200:
            print(f"  ✓ GET {endpoint}")
        else:
            print(f"  ✗ GET {endpoint} - {response.status_code}")
            all_passed = False
    
    # Test write operations
    print("\n3. Testing Admin write operations...")
    
    # Create user
    response = session.post(f"{BASE_URL}/users", json={
        "email": "admin.test@example.com",
        "password": "Test123!",
        "fullName": "Admin Test User",
        "roles": ["Mitarbeiter"]
    })
    if response.status_code == 201:
        print("  ✓ POST /users (create user)")
        test_user_id = response.json()['userId']
        
        # Delete user
        response = session.delete(f"{BASE_URL}/users/{test_user_id}")
        if response.status_code == 200:
            print("  ✓ DELETE /users/:id (delete user)")
        else:
            print(f"  ✗ DELETE /users/:id - {response.status_code}")
            all_passed = False
    else:
        print(f"  ✗ POST /users - {response.status_code}")
        all_passed = False
    
    return all_passed

def test_mitarbeiter_access():
    """Test Mitarbeiter role has correct restricted access"""
    print("\n" + "=" * 60)
    print("TESTING MITARBEITER ROLE ACCESS")
    print("=" * 60)
    
    # First create a Mitarbeiter user as admin
    admin_session = requests.Session()
    response = admin_session.post(f"{BASE_URL}/auth/login", json={
        "email": "admin@fritzwinter.de",
        "password": "Admin123!"
    })
    
    if response.status_code != 200:
        print("✗ Admin login failed, cannot create test user")
        return False
    
    # Create Mitarbeiter user
    print("\n1. Creating Mitarbeiter test user...")
    response = admin_session.post(f"{BASE_URL}/users", json={
        "email": "mitarbeiter.test@example.com",
        "password": "Test123!",
        "fullName": "Mitarbeiter Test User",
        "roles": ["Mitarbeiter"]
    })
    
    if response.status_code != 201:
        print(f"✗ Failed to create Mitarbeiter user: {response.status_code}")
        print(f"  Response: {response.text}")
        return False
    
    test_user_id = response.json()['userId']
    print(f"✓ Created Mitarbeiter user (ID: {test_user_id})")
    
    # Login as Mitarbeiter
    mitarbeiter_session = requests.Session()
    print("\n2. Login as Mitarbeiter...")
    response = mitarbeiter_session.post(f"{BASE_URL}/auth/login", json={
        "email": "mitarbeiter.test@example.com",
        "password": "Test123!"
    })
    
    if response.status_code != 200:
        print(f"✗ Mitarbeiter login failed: {response.status_code}")
        admin_session.delete(f"{BASE_URL}/users/{test_user_id}")
        return False
    
    print("✓ Mitarbeiter login successful")
    
    # Test read operations (should work)
    print("\n3. Testing Mitarbeiter READ operations (should work)...")
    read_endpoints = [
        "/employees",
        "/teams",
        "/shifts/schedule?startDate=2025-01-01&view=week",
        "/vacationrequests",
        "/shiftexchanges/available"
    ]
    
    all_passed = True
    for endpoint in read_endpoints:
        response = mitarbeiter_session.get(f"{BASE_URL}{endpoint}")
        if response.status_code == 200:
            print(f"  ✓ GET {endpoint}")
        else:
            print(f"  ✗ GET {endpoint} - Expected 200, got {response.status_code}")
            all_passed = False
    
    # Test allowed write operations (should work)
    print("\n4. Testing Mitarbeiter WRITE operations (should work)...")
    
    # Get an employee to use for vacation request
    response = mitarbeiter_session.get(f"{BASE_URL}/employees")
    if response.status_code == 200 and len(response.json()) > 0:
        employee_id = response.json()[0]['id']
        
        # Create vacation request
        response = mitarbeiter_session.post(f"{BASE_URL}/vacationrequests", json={
            "employeeId": employee_id,
            "startDate": "2025-06-01",
            "endDate": "2025-06-14",
            "notes": "Test vacation request"
        })
        if response.status_code == 201:
            print("  ✓ POST /vacationrequests (create vacation request)")
        else:
            print(f"  ✗ POST /vacationrequests - Expected 201, got {response.status_code}")
            all_passed = False
    
    # Test forbidden operations (should fail with 403)
    print("\n5. Testing Mitarbeiter FORBIDDEN operations (should fail)...")
    
    forbidden_tests = [
        ("GET", "/users", 403),
        ("POST", "/users", 403),
        ("POST", "/employees", 403),
        ("POST", "/teams", 403),
        ("POST", "/shifts/plan?startDate=2025-01-01&endDate=2025-01-31", 403),
        ("POST", "/absences", 403),
    ]
    
    for method, endpoint, expected_code in forbidden_tests:
        if method == "GET":
            response = mitarbeiter_session.get(f"{BASE_URL}{endpoint}")
        elif method == "POST":
            response = mitarbeiter_session.post(f"{BASE_URL}{endpoint}", json={})
        
        if response.status_code == expected_code:
            print(f"  ✓ {method} {endpoint} (correctly denied)")
        else:
            print(f"  ✗ {method} {endpoint} - Expected {expected_code}, got {response.status_code}")
            all_passed = False
    
    # Cleanup - delete test user
    print("\n6. Cleanup...")
    response = admin_session.delete(f"{BASE_URL}/users/{test_user_id}")
    if response.status_code == 200:
        print("  ✓ Test user deleted")
    else:
        print(f"  ⚠ Failed to delete test user: {response.status_code}")
    
    return all_passed

def main():
    """Run all role-based access control tests"""
    print("=" * 60)
    print("ROLE-BASED ACCESS CONTROL TESTS")
    print("=" * 60)
    print("\nMake sure the server is running on http://localhost:5000")
    print("  python main.py serve --db test_db.db")
    print()
    
    admin_passed = test_admin_access()
    mitarbeiter_passed = test_mitarbeiter_access()
    
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print(f"Admin role tests: {'✓ PASSED' if admin_passed else '✗ FAILED'}")
    print(f"Mitarbeiter role tests: {'✓ PASSED' if mitarbeiter_passed else '✗ FAILED'}")
    print("=" * 60)
    
    return 0 if (admin_passed and mitarbeiter_passed) else 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
