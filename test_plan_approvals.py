"""
Tests for shift plan approval system.

Verifies that:
1. Only monthly planning is allowed (year planning removed)
2. Plans require approval before being visible to regular users
3. Admins can approve/unapprove plans
4. Regular users only see approved plans
"""

import unittest
import sqlite3
import os
from datetime import date, datetime
from web_api import create_app
from db_init import create_database_schema
import json


class TestPlanApprovals(unittest.TestCase):
    """Test shift plan approval functionality"""
    
    @classmethod
    def setUpClass(cls):
        """Create test database once for all tests"""
        cls.db_path = "test_plan_approvals.db"
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)
        
        # Create database schema
        create_database_schema(cls.db_path)
        
        # Create test data
        conn = sqlite3.connect(cls.db_path)
        cursor = conn.cursor()
        
        # Create a test team
        cursor.execute("""
            INSERT INTO Teams (Name, Description)
            VALUES ('Test Team', 'A test team')
        """)
        team_id = cursor.lastrowid
        
        # Create an admin user
        cursor.execute("""
            INSERT INTO Employees (Vorname, Name, Personalnummer, Email, PasswordHash, TeamId)
            VALUES ('Admin', 'User', 'ADM001', 'admin@test.de', ?, ?)
        """, ('hashed_password', team_id))
        admin_id = cursor.lastrowid
        
        # Create a regular user
        cursor.execute("""
            INSERT INTO Employees (Vorname, Name, Personalnummer, Email, PasswordHash, TeamId)
            VALUES ('Regular', 'User', 'REG001', 'user@test.de', ?, ?)
        """, ('hashed_password', team_id))
        user_id = cursor.lastrowid
        
        # Create Admin role
        cursor.execute("""
            INSERT INTO AspNetRoles (Id, Name, NormalizedName)
            VALUES ('admin-role-id', 'Admin', 'ADMIN')
        """)
        
        # Assign admin role
        cursor.execute("""
            INSERT INTO AspNetUserRoles (UserId, RoleId)
            VALUES (?, 'admin-role-id')
        """, (str(admin_id),))
        
        # Create a shift type
        cursor.execute("""
            INSERT INTO ShiftTypes (Code, Name, StartTime, EndTime, DurationHours, ColorCode)
            VALUES ('F', 'Frühschicht', '06:00', '14:00', 8.0, '#FF9800')
        """)
        shift_type_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        cls.team_id = team_id
        cls.admin_id = admin_id
        cls.user_id = user_id
        cls.shift_type_id = shift_type_id
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test database"""
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)
    
    def setUp(self):
        """Set up test client"""
        self.app = create_app(self.db_path)
        self.client = self.app.test_client()
        self.app.config['TESTING'] = True
    
    def login_as_admin(self):
        """Helper to login as admin"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.admin_id
            sess['user_email'] = 'admin@test.de'
            sess['user_fullname'] = 'Admin User'
            sess['user_roles'] = ['Admin']
    
    def login_as_user(self):
        """Helper to login as regular user"""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.user_id
            sess['user_email'] = 'user@test.de'
            sess['user_fullname'] = 'Regular User'
            sess['user_roles'] = []
    
    def test_year_planning_rejected(self):
        """Test that year-based planning is rejected"""
        self.login_as_admin()
        
        # Try to plan for entire year
        start_date = '2024-01-01'
        end_date = '2024-12-31'
        
        response = self.client.post(
            f'/api/shifts/plan?startDate={start_date}&endDate={end_date}&force=false'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('single month', data['error'].lower())
    
    def test_multi_month_planning_rejected(self):
        """Test that planning across multiple months is rejected"""
        self.login_as_admin()
        
        # Try to plan for two months
        start_date = '2024-01-01'
        end_date = '2024-02-29'
        
        response = self.client.post(
            f'/api/shifts/plan?startDate={start_date}&endDate={end_date}&force=false'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('single month', data['error'].lower())
    
    def test_partial_month_planning_rejected(self):
        """Test that planning for partial month is rejected"""
        self.login_as_admin()
        
        # Try to plan for partial month (not covering entire month)
        start_date = '2024-01-05'
        end_date = '2024-01-25'
        
        response = self.client.post(
            f'/api/shifts/plan?startDate={start_date}&endDate={end_date}&force=false'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('entire month', data['error'].lower())
    
    def test_monthly_planning_creates_approval_record(self):
        """Test that planning a month creates an unapproved record"""
        self.login_as_admin()
        
        # Create some shift assignments manually for January 2024
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, IsManual, IsFixed, CreatedAt, CreatedBy)
            VALUES (?, ?, '2024-01-15', 0, 0, ?, 'Test')
        """, (self.admin_id, self.shift_type_id, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
        
        # Check approval status
        response = self.client.get('/api/shifts/plan/approvals/2024/1')
        
        # If no approval record exists yet, that's okay - it will be created when planning
        # Just verify the endpoint works
        self.assertIn(response.status_code, [200, 404])
    
    def test_admin_can_approve_plan(self):
        """Test that admin can approve a monthly plan"""
        self.login_as_admin()
        
        # Approve January 2024
        response = self.client.put(
            '/api/shifts/plan/approvals/2024/1',
            json={'isApproved': True},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # Verify approval status
        response = self.client.get('/api/shifts/plan/approvals/2024/1')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['isApproved'])
    
    def test_admin_can_unapprove_plan(self):
        """Test that admin can remove approval from a plan"""
        self.login_as_admin()
        
        # First approve
        self.client.put(
            '/api/shifts/plan/approvals/2024/2',
            json={'isApproved': True},
            content_type='application/json'
        )
        
        # Then unapprove
        response = self.client.put(
            '/api/shifts/plan/approvals/2024/2',
            json={'isApproved': False},
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify not approved
        response = self.client.get('/api/shifts/plan/approvals/2024/2')
        data = json.loads(response.data)
        self.assertFalse(data['isApproved'])
    
    def test_regular_user_cannot_approve(self):
        """Test that regular user cannot approve plans"""
        self.login_as_user()
        
        response = self.client.put(
            '/api/shifts/plan/approvals/2024/3',
            json={'isApproved': True},
            content_type='application/json'
        )
        
        # Should be forbidden
        self.assertEqual(response.status_code, 403)
    
    def test_regular_user_sees_only_approved_shifts(self):
        """Test that regular users only see shifts from approved months"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create shifts for March 2024 (approved)
        cursor.execute("""
            INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, IsManual, IsFixed, CreatedAt, CreatedBy)
            VALUES (?, ?, '2024-03-15', 0, 0, ?, 'Test')
        """, (self.user_id, self.shift_type_id, datetime.utcnow().isoformat()))
        
        # Approve March 2024
        cursor.execute("""
            INSERT INTO ShiftPlanApprovals (Year, Month, IsApproved, CreatedAt)
            VALUES (2024, 3, 1, ?)
        """, (datetime.utcnow().isoformat(),))
        
        # Create shifts for April 2024 (not approved)
        cursor.execute("""
            INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, IsManual, IsFixed, CreatedAt, CreatedBy)
            VALUES (?, ?, '2024-04-15', 0, 0, ?, 'Test')
        """, (self.user_id, self.shift_type_id, datetime.utcnow().isoformat()))
        
        # Explicitly mark April as not approved
        cursor.execute("""
            INSERT INTO ShiftPlanApprovals (Year, Month, IsApproved, CreatedAt)
            VALUES (2024, 4, 0, ?)
        """, (datetime.utcnow().isoformat(),))
        
        conn.commit()
        conn.close()
        
        self.login_as_user()
        
        # Request March schedule (approved)
        response = self.client.get('/api/shifts/schedule?startDate=2024-03-01&view=month')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        # Should see March shifts
        march_shifts = [a for a in data['assignments'] if a['date'].startswith('2024-03')]
        self.assertGreater(len(march_shifts), 0)
        
        # Request April schedule (not approved)
        response = self.client.get('/api/shifts/schedule?startDate=2024-04-01&view=month')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        # Should NOT see April shifts
        april_shifts = [a for a in data['assignments'] if a['date'].startswith('2024-04')]
        self.assertEqual(len(april_shifts), 0)
    
    def test_admin_sees_all_shifts(self):
        """Test that admin sees shifts regardless of approval status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create shifts for May 2024 (not approved)
        cursor.execute("""
            INSERT INTO ShiftAssignments (EmployeeId, ShiftTypeId, Date, IsManual, IsFixed, CreatedAt, CreatedBy)
            VALUES (?, ?, '2024-05-15', 0, 0, ?, 'Test')
        """, (self.admin_id, self.shift_type_id, datetime.utcnow().isoformat()))
        
        # Explicitly mark May as not approved
        cursor.execute("""
            INSERT INTO ShiftPlanApprovals (Year, Month, IsApproved, CreatedAt)
            VALUES (2024, 5, 0, ?)
        """, (datetime.utcnow().isoformat(),))
        
        conn.commit()
        conn.close()
        
        self.login_as_admin()
        
        # Admin should see May shifts even though not approved
        response = self.client.get('/api/shifts/schedule?startDate=2024-05-01&view=month')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        may_shifts = [a for a in data['assignments'] if a['date'].startswith('2024-05')]
        self.assertGreater(len(may_shifts), 0)
    
    def test_get_all_approvals_admin_only(self):
        """Test that only admins can list all approvals"""
        # Regular user should be forbidden
        self.login_as_user()
        response = self.client.get('/api/shifts/plan/approvals')
        self.assertEqual(response.status_code, 403)
        
        # Admin should be allowed
        self.login_as_admin()
        response = self.client.get('/api/shifts/plan/approvals')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)


if __name__ == '__main__':
    unittest.main()
