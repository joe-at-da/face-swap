import pytest
from fastapi import status
from datetime import datetime, timedelta

from backend.tests.utils.users import create_test_user
from backend.db import models

@pytest.fixture
def test_capture(db_session):
    """Create a test capture session."""
    capture = models.CaptureSession(
        status="completed",
        user_id=1  # Will be replaced in tests
    )
    db_session.add(capture)
    db_session.commit()
    return capture

def test_create_clip(client, db_session, test_capture):
    # Create admin user
    admin = create_test_user(role="ADMIN", db=db_session)
    test_capture.user_id = admin.id
    db_session.commit()
    
    headers = {"Authorization": f"Bearer {admin.create_token()}"}
    
    # Create clip data
    now = datetime.utcnow()
    clip_data = {
        "title": "Test Clip",
        "description": "Test Description",
        "start_time": (now - timedelta(minutes=5)).isoformat(),
        "end_time": now.isoformat(),
        "capture_session_id": test_capture.id
    }
    
    # Create clip
    response = client.post("/api/v1/clips/", json=clip_data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["title"] == clip_data["title"]
    assert response.json()["status"] == "processing"

def test_get_clip(client, db_session, test_capture):
    # Create admin user and clip
    admin = create_test_user(role="ADMIN", db=db_session)
    headers = {"Authorization": f"Bearer {admin.create_token()}"}
    
    clip = models.VideoClip(
        title="Test Clip",
        description="Test Description",
        user_id=admin.id,
        capture_session_id=test_capture.id,
        status="ready",
        start_time=datetime.utcnow() - timedelta(minutes=5),
        end_time=datetime.utcnow()
    )
    db_session.add(clip)
    db_session.commit()
    
    # Get clip
    response = client.get(f"/api/v1/clips/{clip.id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["title"] == "Test Clip"
    assert response.json()["status"] == "ready"

def test_list_clips(client, db_session, test_capture):
    # Create admin user and clips
    admin = create_test_user(role="ADMIN", db=db_session)
    headers = {"Authorization": f"Bearer {admin.create_token()}"}
    
    # Create multiple clips
    clips = []
    for i in range(3):
        clip = models.VideoClip(
            title=f"Test Clip {i}",
            user_id=admin.id,
            capture_session_id=test_capture.id,
            status="ready",
            start_time=datetime.utcnow() - timedelta(minutes=5),
            end_time=datetime.utcnow()
        )
        clips.append(clip)
    
    db_session.add_all(clips)
    db_session.commit()
    
    # List clips
    response = client.get("/api/v1/clips/", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 3

def test_delete_clip(client, db_session, test_capture):
    # Create admin user and clip
    admin = create_test_user(role="ADMIN", db=db_session)
    headers = {"Authorization": f"Bearer {admin.create_token()}"}
    
    clip = models.VideoClip(
        title="Test Clip",
        user_id=admin.id,
        capture_session_id=test_capture.id,
        status="ready",
        start_time=datetime.utcnow() - timedelta(minutes=5),
        end_time=datetime.utcnow()
    )
    db_session.add(clip)
    db_session.commit()
    
    # Delete clip
    response = client.delete(f"/api/v1/clips/{clip.id}", headers=headers)
    assert response.status_code == status.HTTP_204_NO_CONTENT
    
    # Verify clip is deleted
    assert db_session.query(models.VideoClip).filter_by(id=clip.id).first() is None

def test_clip_permissions(client, db_session, test_capture):
    # Create admin and staff users
    admin = create_test_user(role="ADMIN", db=db_session)
    staff = create_test_user(role="STAFF", db=db_session)
    
    # Create clip as admin
    clip = models.VideoClip(
        title="Admin's Clip",
        user_id=admin.id,
        capture_session_id=test_capture.id,
        status="ready",
        start_time=datetime.utcnow() - timedelta(minutes=5),
        end_time=datetime.utcnow()
    )
    db_session.add(clip)
    db_session.commit()
    
    # Try to delete as staff
    staff_headers = {"Authorization": f"Bearer {staff.create_token()}"}
    response = client.delete(f"/api/v1/clips/{clip.id}", headers=staff_headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN
    
    # Verify clip still exists
    assert db_session.query(models.VideoClip).filter_by(id=clip.id).first() is not None
