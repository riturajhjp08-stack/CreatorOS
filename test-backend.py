#!/usr/bin/env python3

"""
CreatorOS Backend Health Check & Testing Script
Tests all major functionality to ensure system is working correctly
"""

import requests
import json
import time
from datetime import datetime

# Configuration
API_URL = 'http://localhost:5000/api'
TEST_EMAIL = 'test@example.com'
TEST_PASSWORD = 'TestPassword123!'
TEST_NAME = 'Test User'

# Colors for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_test(name):
    print(f"\n{Colors.OKBLUE}▶ {name}{Colors.ENDC}")

def print_success(msg):
    print(f"{Colors.OKGREEN}✓ {msg}{Colors.ENDC}")

def print_error(msg):
    print(f"{Colors.FAIL}✗ {msg}{Colors.ENDC}")

def print_warning(msg):
    print(f"{Colors.WARNING}⚠ {msg}{Colors.ENDC}")

def print_header(title):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}")
    print(f"{title}")
    print(f"{'='*60}{Colors.ENDC}\n")

# Test functions
def test_health_check():
    """Test backend is running"""
    print_test("Health Check")
    try:
        response = requests.get('http://localhost:5000/health', timeout=5)
        if response.status_code == 200:
            print_success("Backend is running")
            return True
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error("Backend is not running on http://localhost:5000")
        print_error("Start it with: cd backend && python3 app.py")
        return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_user_registration():
    """Test user registration"""
    print_test("User Registration")
    try:
        payload = {
            'name': TEST_NAME,
            'email': TEST_EMAIL,
            'password': TEST_PASSWORD,
            'referral_code': ''
        }
        
        response = requests.post(
            f'{API_URL}/auth/register',
            json=payload,
            timeout=10
        )
        
        if response.status_code == 201:
            data = response.json()
            if 'access_token' in data and 'user' in data:
                print_success(f"User registered: {data['user']['email']}")
                print_success(f"Received JWT token: {data['access_token'][:50]}...")
                print_success(f"Credits: {data['user']['credits']}")
                return data['access_token'], data['user']['id']
            else:
                print_error("Missing token or user in response")
                return None, None
        elif response.status_code == 409:
            print_warning("User already exists, attempting login...")
            return test_user_login()
        else:
            print_error(f"Registration failed: {response.status_code}")
            print_error(response.json())
            return None, None
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return None, None

def test_user_login():
    """Test user login"""
    print_test("User Login")
    try:
        payload = {
            'email': TEST_EMAIL,
            'password': TEST_PASSWORD
        }
        
        response = requests.post(
            f'{API_URL}/auth/login',
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'access_token' in data and 'user' in data:
                print_success(f"User logged in: {data['user']['email']}")
                print_success(f"JWT token: {data['access_token'][:50]}...")
                return data['access_token'], data['user']['id']
            else:
                print_error("Missing token in response")
                return None, None
        else:
            print_error(f"Login failed: {response.status_code}")
            print_error(response.json())
            return None, None
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return None, None

def test_get_profile(token):
    """Test getting user profile"""
    print_test("Get User Profile")
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(
            f'{API_URL}/user/profile',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Name: {data.get('name')}")
            print_success(f"Email: {data.get('email')}")
            print_success(f"Credits: {data.get('credits')}")
            print_success(f"Created: {data.get('created_at')}")
            return True
        else:
            print_error(f"Failed to get profile: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_verify_token(token):
    """Test token verification"""
    print_test("Verify JWT Token")
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(
            f'{API_URL}/auth/verify-token',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('valid'):
                print_success("Token is valid")
                print_success(f"User: {data['user']['email']}")
                return True
            else:
                print_error("Token is invalid")
                return False
        else:
            print_error(f"Verification failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_connected_platforms(token):
    """Test getting connected platforms"""
    print_test("Get Connected Platforms")
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(
            f'{API_URL}/platforms/connected',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            platforms = data.get('platforms', [])
            if platforms:
                print_success(f"Found {len(platforms)} connected platforms:")
                for p in platforms:
                    print(f"  - {p.get('platform')}: {p.get('platform_display_name')}")
            else:
                print_success("No platforms connected yet")
            return True
        else:
            print_error(f"Failed to get platforms: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_analytics_dashboard(token):
    """Test getting analytics dashboard"""
    print_test("Get Analytics Dashboard")
    try:
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.get(
            f'{API_URL}/analytics/dashboard',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            summary = data.get('summary', {})
            print_success("Dashboard analytics loaded:")
            print(f"  - Total Posts: {summary.get('total_posts', 0)}")
            print(f"  - Total Views: {summary.get('total_views', 0):,}")
            print(f"  - Total Followers: {summary.get('total_followers', 0):,}")
            print(f"  - Total Engagement: {summary.get('total_engagement', 0):,}")
            return True
        else:
            print_error(f"Failed to get analytics: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_update_profile(token):
    """Test updating profile"""
    print_test("Update User Profile")
    try:
        headers = {'Authorization': f'Bearer {token}'}
        payload = {
            'name': 'Updated Test User',
            'bio': 'This is a test bio'
        }
        
        response = requests.put(
            f'{API_URL}/user/profile',
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Profile updated successfully")
            print_success(f"New name: {data['user'].get('name')}")
            print_success(f"New bio: {data['user'].get('bio')}")
            return True
        else:
            print_error(f"Failed to update profile: {response.status_code}")
            print_error(response.json())
            return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def test_database_connection():
    """Test database connectivity"""
    print_test("Database Connection")
    try:
        # Try to register a new test user to verify DB works
        import uuid
        unique_email = f"dbtest-{uuid.uuid4().hex[:8]}@test.com"
        payload = {
            'name': 'DB Test User',
            'email': unique_email,
            'password': TEST_PASSWORD
        }
        
        response = requests.post(
            f'{API_URL}/auth/register',
            json=payload,
            timeout=10
        )
        
        if response.status_code == 201:
            print_success("Database is accessible and working")
            return True
        else:
            print_error(f"Database test failed: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Error: {str(e)}")
        return False

def run_all_tests():
    """Run all tests"""
    print_header("CREATOROROS BACKEND TEST SUITE")
    print(f"Testing: {API_URL}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    results = {
        'passed': 0,
        'failed': 0
    }
    
    # Test 1: Health check
    if not test_health_check():
        print_error("\nBackend is not running. Cannot continue tests.")
        print_error("Start the backend with: cd backend && python3 app.py")
        return
    results['passed'] += 1
    
    # Test 2: Database
    if test_database_connection():
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 3: Registration / Login
    token, user_id = test_user_registration()
    if token and user_id:
        results['passed'] += 1
    else:
        token, user_id = test_user_login()
        if token and user_id:
            results['passed'] += 1
        else:
            results['failed'] += 1
            print_error("\nCannot continue without authentication token")
            return
    
    # Test 4: Verify token
    if test_verify_token(token):
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 5: Get profile
    if test_get_profile(token):
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 6: Update profile
    if test_update_profile(token):
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 7: Get platforms
    if test_connected_platforms(token):
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Test 8: Get analytics
    if test_analytics_dashboard(token):
        results['passed'] += 1
    else:
        results['failed'] += 1
    
    # Summary
    print_header("TEST SUMMARY")
    print(f"✓ Passed: {Colors.OKGREEN}{results['passed']}{Colors.ENDC}")
    print(f"✗ Failed: {Colors.FAIL}{results['failed']}{Colors.ENDC}")
    print(f"Total:  {results['passed'] + results['failed']}")
    print(f"Success Rate: {Colors.OKGREEN}{(results['passed']/(results['passed']+results['failed'])*100):.1f}%{Colors.ENDC}")
    
    if results['failed'] == 0:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}✓ ALL TESTS PASSED!{Colors.ENDC}")
        print("Your CreatorOS backend is fully functional!")
    else:
        print(f"\n{Colors.FAIL}Some tests failed. Check logs above for details.{Colors.ENDC}")
    
    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

if __name__ == '__main__':
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Tests interrupted by user{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {str(e)}{Colors.ENDC}")
