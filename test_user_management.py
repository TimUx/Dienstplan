"""
Test script for user management API endpoints.
"""

import requests
import json
import sys

BASE_URL = "http://localhost:5000/api"
session = requests.Session()

def test_login():
    """Test login with admin credentials"""
    print("\n1. Testing Login...")
    response = session.post(f"{BASE_URL}/auth/login", json={
        "email": "admin@fritzwinter.de",
        "password": "Admin123!"
    })
    
    if response.status_code == 200:
        print("✓ Login successful")
        data = response.json()
        print(f"  User: {data['user']['fullName']}")
        print(f"  Roles: {', '.join(data['user']['roles'])}")
        return True
    else:
        print(f"✗ Login failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return False

def test_get_users():
    """Test getting all users"""
    print("\n2. Testing Get All Users...")
    response = session.get(f"{BASE_URL}/users")
    
    if response.status_code == 200:
        users = response.json()
        print(f"✓ Retrieved {len(users)} users")
        for user in users:
            print(f"  - {user['email']} ({', '.join(user['roles'])}) - "
                  f"Employee: {user.get('employeeName', 'None')}")
        return True
    else:
        print(f"✗ Get users failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return False

def test_get_roles():
    """Test getting all roles"""
    print("\n3. Testing Get All Roles...")
    response = session.get(f"{BASE_URL}/roles")
    
    if response.status_code == 200:
        roles = response.json()
        print(f"✓ Retrieved {len(roles)} roles")
        for role in roles:
            print(f"  - {role['name']}")
        return True
    else:
        print(f"✗ Get roles failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return False

def test_get_employees():
    """Test getting all employees with user account info"""
    print("\n4. Testing Get All Employees (with user account info)...")
    response = session.get(f"{BASE_URL}/employees")
    
    if response.status_code == 200:
        employees = response.json()
        print(f"✓ Retrieved {len(employees)} employees")
        for emp in employees[:5]:  # Show first 5
            has_user = "✓" if emp.get('hasUserAccount') else "✗"
            print(f"  {has_user} {emp['fullName']} ({emp['personalnummer']}) - "
                  f"User: {emp.get('userEmail', 'None')}")
        return True
    else:
        print(f"✗ Get employees failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return False

def test_create_user():
    """Test creating a new user"""
    print("\n5. Testing Create User...")
    
    # First, get an employee to link
    response = session.get(f"{BASE_URL}/employees")
    if response.status_code != 200:
        print("✗ Could not get employees")
        return False
    
    employees = response.json()
    # Find an employee without a user account
    employee_to_link = None
    for emp in employees:
        if not emp.get('hasUserAccount'):
            employee_to_link = emp
            break
    
    if not employee_to_link:
        print("  ⚠ No employees without user accounts found, creating user without employee link")
        employee_id = None
    else:
        employee_id = employee_to_link['id']
        print(f"  Linking to employee: {employee_to_link['fullName']}")
    
    response = session.post(f"{BASE_URL}/users", json={
        "email": "test.user@fritzwinter.de",
        "password": "Test123!",
        "fullName": "Test User",
        "roles": ["Mitarbeiter"],
        "employeeId": employee_id
    })
    
    if response.status_code == 201:
        data = response.json()
        print(f"✓ User created successfully")
        print(f"  User ID: {data['userId']}")
        return data['userId']
    else:
        print(f"✗ Create user failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return None

def test_update_user(user_id):
    """Test updating a user"""
    print(f"\n6. Testing Update User (ID: {user_id})...")
    
    response = session.put(f"{BASE_URL}/users/{user_id}", json={
        "email": "test.user@fritzwinter.de",
        "fullName": "Test User Updated",
        "roles": ["Disponent"],
        "employeeId": None  # Unlink employee
    })
    
    if response.status_code == 200:
        print("✓ User updated successfully")
        return True
    else:
        print(f"✗ Update user failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return False

def test_get_user(user_id):
    """Test getting a single user"""
    print(f"\n7. Testing Get Single User (ID: {user_id})...")
    
    response = session.get(f"{BASE_URL}/users/{user_id}")
    
    if response.status_code == 200:
        user = response.json()
        print(f"✓ Retrieved user: {user['email']}")
        print(f"  Full Name: {user['fullName']}")
        print(f"  Roles: {', '.join(user['roles'])}")
        print(f"  Linked Employee: {user.get('employeeName', 'None')}")
        return True
    else:
        print(f"✗ Get user failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return False

def test_delete_user(user_id):
    """Test deleting a user"""
    print(f"\n8. Testing Delete User (ID: {user_id})...")
    
    response = session.delete(f"{BASE_URL}/users/{user_id}")
    
    if response.status_code == 200:
        print("✓ User deleted successfully")
        return True
    else:
        print(f"✗ Delete user failed: {response.status_code}")
        print(f"  Response: {response.text}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("USER MANAGEMENT API TESTS")
    print("=" * 60)
    print("\nMake sure the server is running on http://localhost:5000")
    print("  python main.py serve --db test_db.db")
    print()
    
    # Test login
    if not test_login():
        print("\n❌ Tests aborted: Login failed")
        return 1
    
    # Test get users
    test_get_users()
    
    # Test get roles
    test_get_roles()
    
    # Test get employees
    test_get_employees()
    
    # Test create user
    new_user_id = test_create_user()
    
    if new_user_id:
        # Test update user
        test_update_user(new_user_id)
        
        # Test get single user
        test_get_user(new_user_id)
        
        # Test delete user
        test_delete_user(new_user_id)
    
    print("\n" + "=" * 60)
    print("TESTS COMPLETED")
    print("=" * 60)
    
    return 0

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
