"""Tests for admin welcome-email flow (POST /api/customers?send_welcome=true & /customers/{id}/welcome)."""
import hashlib
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://my-event-1.preview.emergentagent.com").rstrip("/")
ADMIN = {"email": "bojan.vanderheide@gmail.com", "password": "WhiteVision!2026"}
DJ_CRED = {"email": "bas@white-vision.nl", "password": "Demo!2027"}
SANDBOX_EMAIL = "delivered@resend.dev"

mongo = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
db = mongo[os.environ.get("DB_NAME", "test_database")]


def _login(cred):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json=cred, timeout=30)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def dj():
    return _login(DJ_CRED)


def _cleanup_sandbox():
    # delete any existing TEST customer/user with sandbox email
    user = db.users.find_one({"email": SANDBOX_EMAIL})
    if user:
        db.password_reset_tokens.delete_many({"user_id": str(user["_id"])})
        db.users.delete_one({"_id": user["_id"]})
    db.customers.delete_many({"email": SANDBOX_EMAIL})


@pytest.fixture
def clean_sandbox():
    _cleanup_sandbox()
    yield
    _cleanup_sandbox()


def test_create_customer_with_welcome(admin, clean_sandbox):
    r = admin.post(f"{BASE_URL}/api/customers",
                   json={"name": "TEST_Welkom", "email": SANDBOX_EMAIL, "send_welcome": True})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["has_login"] is True
    assert data["email"] == SANDBOX_EMAIL
    # user exists with role=customer, linked to customer_id
    user = db.users.find_one({"email": SANDBOX_EMAIL})
    assert user and user["role"] == "customer"
    assert user.get("customer_id") == data["id"]

    if data.get("welcome_error"):
        pytest.skip(f"Upstream email provider failed: {data['welcome_error']}")
    assert data.get("welcome_sent_at")

    # token doc with purpose=welcome and ~7 day expiry
    tok = db.password_reset_tokens.find_one({"user_id": str(user["_id"]), "purpose": "welcome"})
    assert tok is not None
    assert tok["used"] is False
    delta = tok["expires_at"] - tok["created_at"]
    assert timedelta(days=6, hours=23) < delta < timedelta(days=7, hours=1)


def test_welcome_requires_email(admin):
    r = admin.post(f"{BASE_URL}/api/customers",
                   json={"name": "TEST_NoEmail", "send_welcome": True})
    # frontend blocks this; backend accepts but welcome_error set OR customer saved without welcome
    # Our backend: send_welcome && email is False -> no welcome sent, no error (returns normal)
    # So this test is a smoke: should 200 with has_login False and no welcome_sent_at
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["has_login"] is False
    assert not data.get("welcome_sent_at")
    db.customers.delete_one({"_id": __import__("bson").ObjectId(data["id"])})


def test_create_welcome_duplicate_email_rolls_back(admin, clean_sandbox):
    # bas@white-vision.nl already has an account (DJ)
    before = db.customers.count_documents({"email": "bas@white-vision.nl"})
    r = admin.post(f"{BASE_URL}/api/customers",
                   json={"name": "TEST_Dup", "email": "bas@white-vision.nl", "send_welcome": True})
    assert r.status_code == 400, r.text
    assert "account" in r.json().get("detail", "").lower()
    after = db.customers.count_documents({"email": "bas@white-vision.nl"})
    assert after == before  # no orphan customer


def test_resend_welcome_rate_limit(admin, clean_sandbox):
    """Avoid real email provider rate limits by seeding 3 fake welcome tokens, then calling resend."""
    # Create customer without welcome (no real email sent)
    r = admin.post(f"{BASE_URL}/api/customers",
                   json={"name": "TEST_Rate", "email": SANDBOX_EMAIL,
                         "send_welcome": False, "password": "InitPass123"})
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    user = db.users.find_one({"email": SANDBOX_EMAIL})
    # Seed 3 recent welcome tokens -> backend should hit 429 immediately on 4th
    now = datetime.now(timezone.utc)
    for _ in range(3):
        db.password_reset_tokens.insert_one({
            "user_id": str(user["_id"]), "token_hash": secrets.token_hex(32),
            "used": False, "purpose": "welcome",
            "created_at": now - timedelta(minutes=5),
            "expires_at": now + timedelta(days=7),
        })
    r4 = admin.post(f"{BASE_URL}/api/customers/{cid}/welcome")
    assert r4.status_code == 429, r4.text
    assert "welkomstmail" in r4.json()["detail"].lower()


def test_dj_cannot_send_welcome(dj, admin, clean_sandbox):
    r = admin.post(f"{BASE_URL}/api/customers",
                   json={"name": "TEST_Perm", "email": SANDBOX_EMAIL, "send_welcome": False,
                         "password": "InitPass123"})
    assert r.status_code == 200
    cid = r.json()["id"]
    rdj = dj.post(f"{BASE_URL}/api/customers/{cid}/welcome")
    assert rdj.status_code == 403


def test_welcome_token_reset_flow(clean_sandbox):
    # create customer+user via mongo-less path: via admin API without welcome, then inject token
    s = _login(ADMIN)
    r = s.post(f"{BASE_URL}/api/customers",
               json={"name": "TEST_Flow", "email": SANDBOX_EMAIL, "send_welcome": False,
                     "password": "TempPass123"})
    assert r.status_code == 200
    user = db.users.find_one({"email": SANDBOX_EMAIL})
    raw = secrets.token_urlsafe(32)
    db.password_reset_tokens.insert_one({
        "user_id": str(user["_id"]),
        "token_hash": hashlib.sha256(raw.encode()).hexdigest(),
        "used": False, "purpose": "welcome",
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(days=7),
    })
    # reset password with raw token
    rr = requests.post(f"{BASE_URL}/api/auth/reset-password",
                       json={"token": raw, "new_password": "NewPass!2026"}, timeout=30)
    assert rr.status_code == 200, rr.text
    # login with new password
    rl = requests.post(f"{BASE_URL}/api/auth/login",
                       json={"email": SANDBOX_EMAIL, "password": "NewPass!2026"}, timeout=30)
    assert rl.status_code == 200, rl.text
    me = rl.json()
    assert me["role"] == "customer"


def test_regression_create_without_welcome_with_password(admin, clean_sandbox):
    r = admin.post(f"{BASE_URL}/api/customers",
                   json={"name": "TEST_Classic", "email": SANDBOX_EMAIL,
                         "send_welcome": False, "password": "Secret!2026"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["has_login"] is True
    assert not data.get("welcome_sent_at")
    # user should be able to login immediately
    rl = requests.post(f"{BASE_URL}/api/auth/login",
                       json={"email": SANDBOX_EMAIL, "password": "Secret!2026"}, timeout=30)
    assert rl.status_code == 200


def teardown_module(module):
    _cleanup_sandbox()
    db.login_attempts.delete_many({})
