#!/usr/bin/env python
"""
API Test Script - Copy this to your project root and run: python test_api.py
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    YELLOW = '\033[93m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{Colors.END}")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.YELLOW}ℹ {text}{Colors.END}")

def print_response(response):
    print(f"  Status: {response.status_code}")
    try:
        data = response.json()
        print(f"  Response: {json.dumps(data, indent=2)[:500]}")
    except:
        print(f"  Response: {response.text[:500]}")

def test_registration():
    """Test user registration"""
    print_header("TEST 1: User Registration")
    
    user_data = {
        "username": f"testuser_{int(datetime.now().timestamp())}",
        "email": f"test_{int(datetime.now().timestamp())}@example.com",
        "first_name": "Test",
        "last_name": "User",
        "password": "TestPassword123!",
        "password2": "TestPassword123!",
        "bio": "Test account"
    }
    
    response = requests.post(f"{BASE_URL}/users/", json=user_data)
    
    if response.status_code == 201:
        print_success("User registered successfully")
        user = response.json()
        return user['username'], "TestPassword123!", user['id']
    else:
        print_error("Registration failed")
        print_response(response)
        return None, None, None

def test_get_profile(username, password):
    """Test getting user profile"""
    print_header("TEST 2: Get User Profile (Authenticated)")
    
    auth = (username, password)
    response = requests.get(f"{BASE_URL}/users/me/", auth=auth)
    
    if response.status_code == 200:
        print_success("Profile retrieved successfully")
        profile = response.json()
        print(f"  User: {profile['email']}")
        print(f"  Verified: {profile['is_verified']}")
        print(f"  Active: {profile['is_active']}")
    else:
        print_error("Failed to get profile")
        print_response(response)

def test_list_users(username, password):
    """Test listing users"""
    print_header("TEST 3: List All Users")
    
    auth = (username, password)
    response = requests.get(f"{BASE_URL}/users/", auth=auth)
    
    if response.status_code == 200:
        data = response.json()
        print_success(f"Retrieved {data['count']} users")
        print(f"  Page size: {len(data['results'])}")
        if data['results']:
            print(f"  First user: {data['results'][0]['email']}")
    else:
        print_error("Failed to list users")
        print_response(response)

def test_create_role(username, password):
    """Test creating a role"""
    print_header("TEST 4: Create Role")
    
    auth = (username, password)
    role_data = {
        "role_name": f"Role_{int(datetime.now().timestamp())}"
    }
    
    response = requests.post(f"{BASE_URL}/roles/", json=role_data, auth=auth)
    
    if response.status_code == 201:
        print_success("Role created successfully")
        role = response.json()
        print(f"  Role: {role['role_name']}")
        return role['id']
    else:
        print_error("Failed to create role")
        print_response(response)
        return None

def test_list_roles(username, password):
    """Test listing roles"""
    print_header("TEST 5: List Roles")
    
    auth = (username, password)
    response = requests.get(f"{BASE_URL}/roles/", auth=auth)
    
    if response.status_code == 200:
        data = response.json()
        print_success(f"Retrieved {data['count']} roles")
        for role in data['results'][:3]:
            print(f"  - {role['role_name']}")
    else:
        print_error("Failed to list roles")
        print_response(response)

def test_assign_role(username, password, user_id, role_id):
    """Test assigning role to user"""
    print_header("TEST 6: Assign Role to User")
    
    if role_id is None:
        print_info("Skipping: No role created")
        return
    
    auth = (username, password)
    data = {"role_id": role_id}
    
    response = requests.post(f"{BASE_URL}/users/{user_id}/set-role/", json=data, auth=auth)
    
    if response.status_code == 200:
        print_success("Role assigned successfully")
        user = response.json()
        print(f"  User: {user['email']}")
        print(f"  Role: {user['role']['role_name']}")
    else:
        print_error("Failed to assign role")
        print_response(response)

def test_search_users(username, password, search_term):
    """Test searching users"""
    print_header(f"TEST 7: Search Users ('{search_term}')")
    
    auth = (username, password)
    response = requests.get(f"{BASE_URL}/users/?search={search_term}", auth=auth)
    
    if response.status_code == 200:
        data = response.json()
        print_success(f"Search returned {data['count']} results")
        for user in data['results'][:3]:
            print(f"  - {user['username']} ({user['email']})")
    else:
        print_error("Search failed")
        print_response(response)

def test_change_password(username, password):
    """Test changing password"""
    print_header("TEST 8: Change Password")
    
    auth = (username, password)
    data = {
        "old_password": password,
        "new_password": "NewPassword456!",
        "new_password2": "NewPassword456!"
    }
    
    response = requests.post(f"{BASE_URL}/users/change-password/", json=data, auth=auth)
    
    if response.status_code == 200:
        print_success("Password changed successfully")
        print_info("Note: Use new password for further tests")
        return "NewPassword456!"
    else:
        print_error("Failed to change password")
        print_response(response)
        return password

def test_list_tokens(username, password):
    """Test listing refresh tokens"""
    print_header("TEST 9: List Refresh Tokens")
    
    auth = (username, password)
    response = requests.get(f"{BASE_URL}/refresh-tokens/", auth=auth)
    
    if response.status_code == 200:
        data = response.json()
        print_success(f"Retrieved {data['count']} tokens")
        for token in data['results'][:3]:
            print(f"  - Device: {token['device_name'] or 'Unknown'}, IP: {token['ip_address']}")
    else:
        print_error("Failed to list tokens")
        print_response(response)

def test_update_profile(username, password, user_id):
    """Test updating user profile"""
    print_header("TEST 10: Update User Profile")
    
    auth = (username, password)
    data = {
        "first_name": "Updated",
        "bio": "Updated bio"
    }
    
    response = requests.patch(f"{BASE_URL}/users/{user_id}/", json=data, auth=auth)
    
    if response.status_code == 200:
        print_success("Profile updated successfully")
        user = response.json()
        print(f"  First name: {user['first_name']}")
        print(f"  Bio: {user['bio']}")
    else:
        print_error("Failed to update profile")
        print_response(response)

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  USER API TEST SUITE")
    print("="*60)
    
    # Make sure server is running
    try:
        response = requests.get(f"{BASE_URL}/users/", timeout=2)
    except requests.exceptions.ConnectionError:
        print_error("Cannot connect to server!")
        print_info("Make sure Django server is running:")
        print_info("  python manage.py runserver")
        return
    except Exception as e:
        print_error(f"Error: {e}")
        return
    
    # Run tests
    username, password, user_id = test_registration()
    
    if not username:
        print_error("Cannot proceed - registration failed")
        return
    
    test_get_profile(username, password)
    test_list_users(username, password)
    role_id = test_create_role(username, password)
    test_list_roles(username, password)
    test_assign_role(username, password, user_id, role_id)
    test_search_users(username, password, username[:3])
    password = test_change_password(username, password)
    test_list_tokens(username, password)
    test_update_profile(username, password, user_id)
    
    print("\n" + "="*60)
    print("  TEST SUITE COMPLETED")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
