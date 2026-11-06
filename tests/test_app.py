from fastapi.testclient import TestClient
from app.main import app

def test_home():
    with TestClient(app) as client:
        r=client.get('/')
        assert r.status_code==200
        assert 'THẠNH PHÚ' in r.text

def test_login_form():
    with TestClient(app) as client:
        assert client.get('/login').status_code==200

def test_requires_auth():
    with TestClient(app) as client:
        assert client.get('/admin').status_code==401
