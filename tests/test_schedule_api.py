"""
Test schedule API endpoints
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from backend.api.main import app

client = TestClient(app)


def test_get_schedule():
    """Test GET /api/schedule"""
    response = client.get("/api/schedule")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    assert "cron" in data["data"]
    assert "enabled" in data["data"]
    print("✓ GET /api/schedule works")


def test_update_schedule():
    """Test PUT /api/schedule"""
    schedule_data = {
        "enabled": True,
        "cron": "0 10 * * *",
        "window_days": 2,
        "top_k": 15,
        "description": "Test schedule"
    }
    
    response = client.put("/api/schedule", json=schedule_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    print("✓ PUT /api/schedule works")


def test_get_cron_examples():
    """Test GET /api/schedule/cron-examples"""
    response = client.get("/api/schedule/cron-examples")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    assert len(data["data"]) > 0
    print("✓ GET /api/schedule/cron-examples works")


def test_get_config():
    """Test GET /api/config"""
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "data" in data
    print("✓ GET /api/config works")


if __name__ == "__main__":
    print("Testing Schedule API endpoints...")
    print()
    
    try:
        test_get_schedule()
        test_update_schedule()
        test_get_cron_examples()
        test_get_config()
        print()
        print("All tests passed! ✓")
    except AssertionError as e:
        print()
        print(f"Test failed: {e} ✗")
        sys.exit(1)
    except Exception as e:
        print()
        print(f"Error: {e} ✗")
        sys.exit(1)
