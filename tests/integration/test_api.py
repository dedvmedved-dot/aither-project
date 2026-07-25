"""Integration tests for Aither BFF API."""
import pytest
import requests

BASE = "https://fb1.spb.ru:443/api/v1"
ADMIN = {"username": "admin", "password": "admin"}


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.verify = False
    r = s.post(f"{BASE}/auth/login", json=ADMIN)
    assert r.status_code == 200, f"Login failed: {r.text}"
    return s


@pytest.fixture(scope="module")
def beta_token(session):
    r = session.post(f"{BASE}/tokens", json={
        "name": "integration-test",
        "scopes": ["model:14b:chat", "model:32b:chat-adapter"]
    })
    assert r.status_code == 200, f"Token creation failed: {r.text}"
    return r.json()


class TestAuth:
    def test_login_success(self, session):
        r = requests.post(f"{BASE}/auth/login", json=ADMIN)
        assert r.status_code == 200

    def test_login_invalid(self):
        r = requests.post(f"{BASE}/auth/login",
                         json={"username": "wrong", "password": "wrong"})
        assert r.status_code == 401

    def test_models_no_auth(self):
        r = requests.get(f"{BASE}/models")
        assert r.status_code == 401


class TestModels:
    def test_list_models(self, session):
        r = session.get(f"{BASE}/models")
        assert r.status_code == 200
        data = r.json()
        assert "models" in data
        model_ids = [m["id"] for m in data["models"]]
        assert "14b" in model_ids or "qwen-14b" in str(data)
        assert "32b" in model_ids or "qwen-32b-base" in str(data)


class TestChat:
    def test_chat_14b(self, session):
        r = session.post(f"{BASE}/chat", json={
            "model": "14b",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10
        })
        assert r.status_code == 200
        data = r.json()
        assert "choices" in data
        assert len(data["choices"]) > 0

    def test_chat_32b(self, session):
        r = session.post(f"{BASE}/chat", json={
            "model": "32b",
            "messages": [{"role": "user", "content": "Continue: Once upon"}],
            "max_tokens": 10
        })
        assert r.status_code == 200


class TestKeyLifecycle:
    def test_create_and_use(self, beta_token):
        assert "token" in beta_token
        assert beta_token["token"].startswith("athr_")

        # Use the token
        r = requests.get(f"{BASE}/models",
                        headers={"Authorization": f"Bearer {beta_token['token']}"})
        assert r.status_code == 200

    def test_revoke(self, session, beta_token):
        tid = beta_token["token_id"]
        r = session.delete(f"{BASE}/tokens/{tid}")
        assert r.status_code == 200

        # Verify revoked
        r = requests.get(f"{BASE}/models",
                        headers={"Authorization": f"Bearer {beta_token['token']}"})
        assert r.status_code == 401


class TestEndpoints:
    def test_internet_endpoint(self):
        r = requests.get("https://localhost:443/")
        assert r.status_code == 200

    def test_testzone_endpoint(self):
        r = requests.get("http://10.129.13.78:30080/")
        assert r.status_code == 200
