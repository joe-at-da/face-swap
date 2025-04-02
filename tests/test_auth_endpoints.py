import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.core.security import get_password_hash
from backend.db.models import User
from backend.schemas.auth import UserRole
from backend.db.session import get_db

@pytest.fixture
def test_client():
    with TestClient(app) as client:
        yield client

@pytest.fixture
def db():
    """Get a database session for each test"""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()

def test_setup(test_client):
    """Test that the test client is properly initialized"""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_login_success(test_client, db, clean_db):
    # Create test admin user
    admin = create_test_admin(db)
    
    # Test login
    response = test_client.post(
        "/api/v1/auth/login",
        data={"username": "admin@parliament.uk", "password": "adminpass"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_wrong_password(test_client, db, clean_db):
    response = test_client.post(
        "/api/v1/auth/login",
        data={"username": "admin@parliament.uk", "password": "wrongpass"}
    )
    assert response.status_code == 401

def test_register_user(test_client, db, clean_db):
    # Create test admin user
    admin = create_test_admin(db)
    
    # Login as admin
    login_response = test_client.post(
        "/api/v1/auth/login",
        data={"username": "admin@parliament.uk", "password": "adminpass"}
    )
    token = login_response.json()["access_token"]
    
    # Register new user
    response = test_client.post(
        "/api/v1/auth/register",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "staff@parliament.uk",
            "password": "staffpass",
            "full_name": "Staff User",
            "role": "STAFF"
        }
    )
    assert response.status_code == 200
    assert response.json()["email"] == "staff@parliament.uk"
    assert response.json()["role"] == "STAFF"

def test_register_unauthorized(test_client, db, clean_db):
    # Try to register without admin token
    response = test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "unauthorized@parliament.uk",
            "password": "pass",
            "full_name": "Unauthorized User",
            "role": "STAFF"
        }
    )
    assert response.status_code == 401

def test_me_endpoint(test_client, db, clean_db):
    # Create test MP user
    mp = create_test_mp(db)
    
    # Login as MP
    login_response = test_client.post(
        "/api/v1/auth/login",
        data={"username": "mp@parliament.uk", "password": "mppass"}
    )
    token = login_response.json()["access_token"]
    
    # Get current user info
    response = test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "mp@parliament.uk"
    assert response.json()["role"] == "MP"

def test_update_me(test_client, db, clean_db):
    # Create test MP user
    mp = create_test_mp(db)
    
    # Login as MP
    login_response = test_client.post(
        "/api/v1/auth/login",
        data={"username": "mp@parliament.uk", "password": "mppass"}
    )
    token = login_response.json()["access_token"]
    
    # Update user info
    response = test_client.put(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": "Updated MP Name"
        }
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Updated MP Name"

def test_list_users(test_client, db, clean_db):
    # Create test admin user
    admin = create_test_admin(db)
    
    # Login as admin
    login_response = test_client.post(
        "/api/v1/auth/login",
        data={"username": "admin@parliament.uk", "password": "adminpass"}
    )
    token = login_response.json()["access_token"]
    
    # List users
    response = test_client.get(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0

def create_test_admin(db: Session) -> User:
    try:
        # First, try to delete any existing admin user
        db.query(User).filter(User.email == "admin@parliament.uk").delete()
        db.commit()

        admin = User(
            email="admin@parliament.uk",
            hashed_password=get_password_hash("adminpass"),
            full_name="Admin User",
            role=UserRole.ADMIN,
            is_active=True
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return admin
    except Exception as e:
        db.rollback()
        raise e

def create_test_mp(db: Session) -> User:
    try:
        # First, try to delete any existing MP user
        db.query(User).filter(User.email == "mp@parliament.uk").delete()
        db.commit()

        mp = User(
            email="mp@parliament.uk",
            hashed_password=get_password_hash("mppass"),
            full_name="MP User",
            role=UserRole.MP,
            is_active=True
        )
        db.add(mp)
        db.commit()
        db.refresh(mp)
        return mp
    except Exception as e:
        db.rollback()
        raise e
