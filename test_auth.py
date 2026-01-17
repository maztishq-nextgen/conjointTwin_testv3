#!/usr/bin/env python3
"""Test JWT authentication system."""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_signup():
    """Test user registration."""
    print("\n" + "=" * 80)
    print("🔐 TEST: User Signup")
    print("=" * 80)
    
    response = requests.post(
        f"{BASE_URL}/auth/signup",
        json={
            "email": f"test{int(time.time())}@example.com",
            "password": "testpassword123",
            "name": "Test User"
        }
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        user = response.json()
        print(f"✅ User created: {user['id']}")
        print(f"   Email: {user['email']}")
        print(f"   Name: {user['name']}")
        return user
    else:
        print(f"❌ Error: {response.text}")
        return None

def test_login(email: str, password: str):
    """Test user login."""
    print("\n" + "=" * 80)
    print("🔑 TEST: User Login")
    print("=" * 80)
    
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": email,
            "password": password
        }
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        tokens = response.json()
        print(f"✅ Login successful")
        print(f"   Access token: {tokens['access_token'][:50]}...")
        print(f"   Refresh token: {tokens['refresh_token'][:50]}...")
        print(f"   Token type: {tokens['token_type']}")
        return tokens
    else:
        print(f"❌ Error: {response.text}")
        return None

def test_get_me(access_token: str):
    """Test getting current user."""
    print("\n" + "=" * 80)
    print("👤 TEST: Get Current User")
    print("=" * 80)
    
    response = requests.get(
        f"{BASE_URL}/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        user = response.json()
        print(f"✅ Got user: {user['id']}")
        print(f"   Email: {user['email']}")
        print(f"   Name: {user['name']}")
        print(f"   Total tokens: {user['total_tokens']}")
        print(f"   Total cost: ${user['total_cost']:.4f}")
        print(f"   Request count: {user['request_count']}")
        return user
    else:
        print(f"❌ Error: {response.text}")
        return None

def test_refresh_token(refresh_token: str):
    """Test token refresh."""
    print("\n" + "=" * 80)
    print("🔄 TEST: Refresh Token")
    print("=" * 80)
    
    response = requests.post(
        f"{BASE_URL}/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        tokens = response.json()
        print(f"✅ Token refreshed")
        print(f"   New access token: {tokens['access_token'][:50]}...")
        return tokens
    else:
        print(f"❌ Error: {response.text}")
        return None

def test_invalid_token():
    """Test invalid token handling."""
    print("\n" + "=" * 80)
    print("🚫 TEST: Invalid Token")
    print("=" * 80)
    
    response = requests.get(
        f"{BASE_URL}/auth/me",
        headers={"Authorization": "Bearer invalid_token_here"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 401:
        print(f"✅ Correctly rejected invalid token")
        return True
    else:
        print(f"❌ Unexpected response: {response.text}")
        return False

def test_duplicate_signup(email: str):
    """Test duplicate email rejection."""
    print("\n" + "=" * 80)
    print("📧 TEST: Duplicate Email Rejection")
    print("=" * 80)
    
    response = requests.post(
        f"{BASE_URL}/auth/signup",
        json={
            "email": email,
            "password": "anotherpassword",
            "name": "Another User"
        }
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 400:
        print(f"✅ Correctly rejected duplicate email")
        return True
    else:
        print(f"❌ Unexpected response: {response.text}")
        return False

def test_wrong_password(email: str):
    """Test wrong password rejection."""
    print("\n" + "=" * 80)
    print("🔒 TEST: Wrong Password Rejection")
    print("=" * 80)
    
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={
            "email": email,
            "password": "wrongpassword"
        }
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 401:
        print(f"✅ Correctly rejected wrong password")
        return True
    else:
        print(f"❌ Unexpected response: {response.text}")
        return False

def main():
    print("=" * 80)
    print("🧪 JWT AUTHENTICATION SYSTEM TEST")
    print("=" * 80)
    
    # Test signup
    user = test_signup()
    if not user:
        print("\n❌ Signup failed, stopping tests")
        return
    
    email = user["email"]
    password = "testpassword123"
    
    # Test duplicate signup
    test_duplicate_signup(email)
    
    # Test wrong password
    test_wrong_password(email)
    
    # Test login
    tokens = test_login(email, password)
    if not tokens:
        print("\n❌ Login failed, stopping tests")
        return
    
    # Test get me
    test_get_me(tokens["access_token"])
    
    # Test invalid token
    test_invalid_token()
    
    # Test token refresh
    new_tokens = test_refresh_token(tokens["refresh_token"])
    
    # Test new token works
    if new_tokens:
        print("\n" + "=" * 80)
        print("🔄 TEST: Using Refreshed Token")
        print("=" * 80)
        test_get_me(new_tokens["access_token"])
    
    print("\n" + "=" * 80)
    print("✅ ALL AUTHENTICATION TESTS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
