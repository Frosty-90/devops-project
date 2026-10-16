import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
if os.path.exists("test.db"):
    os.remove("test.db")  # fresh test database every run, never the real PostgreSQL

from fastapi.testclient import TestClient
from app.db import Base, engine
from app.main import app

Base.metadata.create_all(bind=engine)

client = TestClient(app)

def test_health():
    assert client.get("/health").json() == {"status": "UP"}

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "TaskBoard API"

def test_create_task_validation():
    response = client.post("/api/tasks", json={"title": "Deploy application", "priority": "HIGH", "assignee": "Student"})
    assert response.status_code == 201
    assert response.json()["title"] == "Deploy application"

def test_create_task_rejects_invalid_priority():
    response = client.post("/api/tasks", json={"title": "Bad", "priority": "URGENT"})
    assert response.status_code == 422

def test_update_task():
    task_id = client.post("/api/tasks", json={"title": "Write Helm chart"}).json()["id"]
    response = client.put(f"/api/tasks/{task_id}", json={"status": "DONE"})
    assert response.status_code == 200
    assert response.json()["status"] == "DONE"
    assert response.json()["title"] == "Write Helm chart"

def test_delete_task():
    task_id = client.post("/api/tasks", json={"title": "Temporary"}).json()["id"]
    assert client.delete(f"/api/tasks/{task_id}").status_code == 204
    assert client.get(f"/api/tasks/{task_id}").status_code == 404

def test_get_missing_task_returns_404():
    assert client.get("/api/tasks/999999").status_code == 404

def test_stats_counts_by_status():
    before = client.get("/api/tasks/stats").json()
    client.post("/api/tasks", json={"title": "In flight", "status": "IN_PROGRESS"})
    after = client.get("/api/tasks/stats").json()
    assert after["total"] == before["total"] + 1
    assert after["inProgress"] == before["inProgress"] + 1

def test_list_tasks():
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
