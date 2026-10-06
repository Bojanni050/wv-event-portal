"""Backend tests for customer account page: GET/PATCH /api/account and POST /api/auth/password.

Uses sanne@example.nl for password changes (restored at end). Also sanity-checks jeroen
profile update then restores. Cleans up login_attempts to avoid lockout.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def jeroen():
    s = _login("jeroen@example.nl", "Demo!2027")
    yield s


@pytest.fixture(scope="module")
def sanne():
    s = _login("sanne@example.nl", "Demo!2027")
    yield s


# --- /api/account auth guard ---
def test_account_requires_auth():
    r = requests.get(f"{API}/account")
    assert r.status_code == 401
    r2 = requests.patch(f"{API}/account", json={"name": "x", "email": "x@y.nl"})
    assert r2.status_code == 401


# --- GET /api/account ---
def test_get_account_prefill(jeroen):
    r = jeroen.get(f"{API}/account")
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "jeroen@example.nl"
    assert data["name"] == "Jeroen & Mark"
    assert "phone" in data
    assert data["role"] == "customer"


# --- PATCH /api/account: update + persistence (then restore) ---
def test_patch_account_persistence(jeroen):
    orig = jeroen.get(f"{API}/account").json()
    try:
        payload = {"name": "Jeroen & Mark TEST", "email": "jeroen@example.nl", "phone": "06 12345678"}
        r = jeroen.patch(f"{API}/account", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["name"] == payload["name"]
        assert body["phone"] == payload["phone"]
        # verify persistence
        r2 = jeroen.get(f"{API}/account")
        assert r2.json()["name"] == payload["name"]
        assert r2.json()["phone"] == payload["phone"]
    finally:
        jeroen.patch(f"{API}/account", json={
            "name": orig["name"], "email": orig["email"],
            "phone": orig.get("phone") or "06 00000010",
        })


# --- Email already in use -> 400 ---
def test_patch_account_email_conflict(jeroen):
    r = jeroen.patch(f"{API}/account", json={
        "name": "Jeroen & Mark", "email": "bas@white-vision.nl", "phone": "06 00000010"})
    assert r.status_code == 400
    assert "in gebruik" in r.json()["detail"].lower()


def test_patch_account_invalid_email(jeroen):
    r = jeroen.patch(f"{API}/account", json={
        "name": "Jeroen & Mark", "email": "not-an-email", "phone": None})
    assert r.status_code == 400


# --- Password change ---
def test_password_wrong_current(sanne):
    r = sanne.post(f"{API}/auth/password",
                   json={"current_password": "wrong-pass", "new_password": "whatever12"})
    assert r.status_code == 400
    assert "klopt niet" in r.json()["detail"].lower()


def test_password_too_short(sanne):
    r = sanne.post(f"{API}/auth/password",
                   json={"current_password": "Demo!2027", "new_password": "short"})
    assert r.status_code == 400


def test_password_change_and_login_flow():
    """Change sanne's password, log in with new, old fails, then restore."""
    s = _login("sanne@example.nl", "Demo!2027")
    new_pw = "NewPass!2028"
    try:
        r = s.post(f"{API}/auth/password",
                   json={"current_password": "Demo!2027", "new_password": new_pw})
        assert r.status_code == 200
        # Old password login should fail
        r_old = requests.post(f"{API}/auth/login",
                              json={"email": "sanne@example.nl", "password": "Demo!2027"})
        assert r_old.status_code == 401
        # New password login succeeds
        r_new = requests.post(f"{API}/auth/login",
                              json={"email": "sanne@example.nl", "password": new_pw})
        assert r_new.status_code == 200
    finally:
        # restore via the authenticated session (new pw now valid)
        s2 = _login("sanne@example.nl", new_pw)
        rr = s2.post(f"{API}/auth/password",
                     json={"current_password": new_pw, "new_password": "Demo!2027"})
        assert rr.status_code == 200
        # Clear any login_attempts for sanne to avoid lockouts
        try:
            import pymongo
            mongo_url = os.environ.get("MONGO_URL")
            db_name = os.environ.get("DB_NAME")
            if mongo_url and db_name:
                client = pymongo.MongoClient(mongo_url)
                client[db_name].login_attempts.delete_many({"identifier": {"$regex": "sanne@example.nl"}})
                client[db_name].login_attempts.delete_many({"identifier": {"$regex": "jeroen@example.nl"}})
        except Exception:
            pass


# --- Regression: dashboard & chat still return 200 ---
def test_regression_events_list(jeroen):
    r = jeroen.get(f"{API}/events")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
