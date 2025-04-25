import pytest
from fastapi import status
from datetime import datetime

from backend.tests.utils.users import create_test_user

def test_start_capture(client, db_session):
    # Create admin user
    admin = create_test_user(role="admin", db=db_session)
    headers = {"Authorization": f"Bearer {admin.create_token()}"}
    
    # Start capture
    response = client.post("/api/v1/capture/start", headers=headers)
    print(f"Start capture response: {response.json()}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "started"
    assert "capture_id" in response.json()
    assert "task_id" in response.json()

def test_stop_capture(client, db_session):
    # Create admin user
    admin = create_test_user(role="admin", db=db_session)
    headers = {"Authorization": f"Bearer {admin.create_token()}"}
    
    # Start capture first
    client.post("/api/v1/capture/start", headers=headers)
    
    # Stop capture
    response = client.post("/api/v1/capture/stop", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["status"] == "stopped"
    assert "capture_id" in response.json()

def test_get_capture_status(client, db_session):
    # Create admin user
    admin = create_test_user(role="admin", db=db_session)
    headers = {"Authorization": f"Bearer {admin.create_token()}"}
    
    # Check status (no active capture)
    response = client.get("/api/v1/capture/status", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["is_capturing"] is False
    
    # Start capture and manually create an active capture session
    response = client.post("/api/v1/capture/start", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    
    # Check status again
    response = client.get("/api/v1/capture/status", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["is_capturing"] is True
    assert "capture_id" in response.json()
    assert "start_time" in response.json()

def test_unauthorized_access(client):
    # Try without authentication
    response = client.post("/api/v1/capture/start")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    # Create non-admin user
    staff = create_test_user(role="STAFF")
    headers = {"Authorization": f"Bearer {staff.create_token()}"}
    
    # Try with unauthorized user
    response = client.post("/api/v1/capture/start", headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
