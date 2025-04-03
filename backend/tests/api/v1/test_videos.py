import pytest
from fastapi import status
from datetime import datetime, timedelta

from backend.db import models
from backend.tests.utils.users import create_test_user
from backend.tests.utils.videos import create_test_clip

@pytest.fixture
def test_mp():
    return create_test_user(role="MP")

@pytest.fixture
def test_admin():
    return create_test_user(role="ADMIN")

@pytest.fixture
def test_staff():
    return create_test_user(role="STAFF")

@pytest.fixture
def test_clip(test_mp, db):
    return create_test_clip(
        user_id=test_mp.id,
        title="Test Clip",
        description="Test Description",
        source_url="https://parliamentlive.tv/test",
        start_time=datetime.now(),
        end_time=datetime.now() + timedelta(minutes=5),
        db=db
    )

def test_list_clips(client, test_mp, test_clip):
    """Test listing video clips."""
    response = client.get(
        "/api/v1/videos/",
        headers={"Authorization": f"Bearer {test_mp.create_token()}"}
    )
    assert response.status_code == status.HTTP_200_OK
    clips = response.json()
    assert len(clips) >= 1
    assert clips[0]["title"] == "Test Clip"

def test_create_clip_as_mp(client, test_mp):
    """Test creating a video clip as an MP."""
    clip_data = {
        "title": "New Test Clip",
        "description": "New Description",
        "source_url": "https://parliamentlive.tv/new",
        "start_time": datetime.now().isoformat(),
        "end_time": (datetime.now() + timedelta(minutes=5)).isoformat()
    }
    response = client.post(
        "/api/v1/videos/",
        json=clip_data,
        headers={"Authorization": f"Bearer {test_mp.create_token()}"}
    )
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["title"] == "New Test Clip"

def test_create_clip_as_staff_fails(client, test_staff):
    """Test that staff cannot create clips."""
    clip_data = {
        "title": "Staff Clip",
        "description": "Should Fail",
        "source_url": "https://parliamentlive.tv/staff",
        "start_time": datetime.now().isoformat(),
        "end_time": (datetime.now() + timedelta(minutes=5)).isoformat()
    }
    response = client.post(
        "/api/v1/videos/",
        json=clip_data,
        headers={"Authorization": f"Bearer {test_staff.create_token()}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_get_clip(client, test_mp, test_clip):
    """Test getting a specific clip."""
    response = client.get(
        f"/api/v1/videos/{test_clip.id}",
        headers={"Authorization": f"Bearer {test_mp.create_token()}"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == test_clip.id

def test_get_nonexistent_clip(client, test_mp):
    """Test getting a clip that doesn't exist."""
    response = client.get(
        "/api/v1/videos/99999",
        headers={"Authorization": f"Bearer {test_mp.create_token()}"}
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_update_own_clip(client, test_mp, test_clip):
    """Test updating own clip."""
    update_data = {
        "title": "Updated Title",
        "description": "Updated Description"
    }
    response = client.put(
        f"/api/v1/videos/{test_clip.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {test_mp.create_token()}"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["title"] == "Updated Title"

def test_update_others_clip_as_staff_fails(client, test_staff, test_clip):
    """Test that staff cannot update others' clips."""
    update_data = {
        "title": "Staff Update",
        "description": "Should Fail"
    }
    response = client.put(
        f"/api/v1/videos/{test_clip.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {test_staff.create_token()}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_admin_can_update_any_clip(client, test_admin, test_clip):
    """Test that admin can update any clip."""
    update_data = {
        "title": "Admin Update",
        "description": "Should Work"
    }
    response = client.put(
        f"/api/v1/videos/{test_clip.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {test_admin.create_token()}"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["title"] == "Admin Update"

def test_delete_own_clip(client, test_mp, test_clip):
    """Test deleting own clip."""
    response = client.delete(
        f"/api/v1/videos/{test_clip.id}",
        headers={"Authorization": f"Bearer {test_mp.create_token()}"}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

def test_delete_others_clip_as_staff_fails(client, test_staff, test_clip):
    """Test that staff cannot delete others' clips."""
    response = client.delete(
        f"/api/v1/videos/{test_clip.id}",
        headers={"Authorization": f"Bearer {test_staff.create_token()}"}
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_admin_can_delete_any_clip(client, test_admin, test_clip):
    """Test that admin can delete any clip."""
    response = client.delete(
        f"/api/v1/videos/{test_clip.id}",
        headers={"Authorization": f"Bearer {test_admin.create_token()}"}
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

def test_get_clip_status(client, test_mp, test_clip):
    """Test getting clip processing status."""
    response = client.get(
        f"/api/v1/videos/{test_clip.id}/status",
        headers={"Authorization": f"Bearer {test_mp.create_token()}"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert "status" in response.json()
    assert "progress" in response.json()
