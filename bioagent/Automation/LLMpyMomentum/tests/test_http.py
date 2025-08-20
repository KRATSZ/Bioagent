from fastapi.testclient import TestClient
from app.http_api import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_intent_endpoint():
    r = client.post("/intent", json={"text": "status"})
    assert r.status_code == 200
    assert r.json()["action"] == "status"

def test_chat_mock_status():
    r = client.post("/chat", json={"text": "status"})
    assert r.status_code == 200
    assert isinstance(r.json()["text"], str)

def test_chat_with_dry_run():
    r = client.post("/chat", json={"text": "start", "dry_run": True})
    assert r.status_code == 200
    # Should return something (mock will execute anyway in this case)
    assert isinstance(r.json()["text"], str)

def test_intent_run_process():
    r = client.post("/intent", json={"text": "run process Alpha variables: a=1"})
    assert r.status_code == 200
    data = r.json()
    assert data["action"] == "run_process"
    assert data["process_name"] == "Alpha"
    assert data["variables"] == {"a": 1}

