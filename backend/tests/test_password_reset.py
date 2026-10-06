"""Password reset flow tests (forgot-password, reset-password).

Uses a TEST customer created via admin API with email delivered@resend.dev
for forgot-password/rate-limit tests. Uses sanne account for the end-to-end
reset flow with a token inserted directly into Mongo (restores password at
the end).
"""
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://my-event-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("bojan.vanderheide@gmail.com", "WhiteVision!2026")
SANNE_EMAIL = "sanne@example.nl"
SANNE_PASSWORD = "Demo!2027"

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"


def _hash_token(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def _now():
    return datetime.now(timezone.utc)


@pytest.fixture(scope="module")
def db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def admin_sess():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN[0], "password": ADMIN[1]}, timeout=15)
    assert r.status_code == 200, r.text
    return s


@pytest.fixture(scope="module")
def test_customer(admin_sess, db):
    # Create TEST customer with safe sandbox email
    payload = {"name": "TEST_Reset", "email": "delivered@resend.dev", "password": "TestPass123"}
    r = admin_sess.post(f"{API}/customers", json=payload, timeout=20)
    assert r.status_code in (200, 201), r.text
    cid = r.json().get("id") or r.json().get("_id")
    u = db.users.find_one({"email": payload["email"]})
    assert u, "customer user not created"
    uid = str(u["_id"])
    yield cid, uid, payload["email"], payload["password"]
    # Cleanup
    try:
        admin_sess.delete(f"{API}/customers/{cid}", timeout=15)
    except Exception:
        pass
    db.password_reset_tokens.delete_many({})
    db.login_attempts.delete_many({})


# --- forgot-password generic response ---
def test_forgot_password_unknown_email_generic_200():
    r = requests.post(f"{API}/auth/forgot-password", json={"email": "no-such-user-xyz@example.nl"}, timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "bekend" in data["message"].lower()


def test_forgot_password_known_user_generic_200_and_token_stored(test_customer, db):
    cid, uid, email, _pw = test_customer
    r = requests.post(f"{API}/auth/forgot-password", json={"email": email}, timeout=25)
    assert r.status_code == 200
    assert r.json()["ok"] is True
    # token row created
    tokens = list(db.password_reset_tokens.find({"user_id": uid}))
    assert len(tokens) >= 1
    t = tokens[-1]
    assert t["used"] is False
    assert t["expires_at"] > _now().replace(tzinfo=None) if t["expires_at"].tzinfo is None else t["expires_at"] > _now()
    # token_hash is a 64-char hex (sha256)
    assert len(t["token_hash"]) == 64


def test_forgot_password_rate_limit(test_customer, db):
    cid, uid, email, _ = test_customer
    before = db.password_reset_tokens.count_documents({"user_id": uid})
    for _ in range(max(0, 3 - before)):
        r = requests.post(f"{API}/auth/forgot-password", json={"email": email}, timeout=25)
        assert r.status_code == 200
    at_three = db.password_reset_tokens.count_documents({"user_id": uid})
    assert at_three >= 3, f"expected >=3 tokens, got {at_three}"
    # 4th request → still generic 200, no new token
    r = requests.post(f"{API}/auth/forgot-password", json={"email": email}, timeout=25)
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert db.password_reset_tokens.count_documents({"user_id": uid}) == at_three


# --- reset-password flow against sanne ---
@pytest.fixture(scope="module")
def sanne_user(db):
    u = db.users.find_one({"email": SANNE_EMAIL})
    assert u, "sanne user missing"
    yield u
    # restore password at end of module
    requests.post(f"{API}/auth/login", json={"email": SANNE_EMAIL, "password": SANNE_PASSWORD}, timeout=15)
    # cleanup collections
    db.password_reset_tokens.delete_many({})
    db.login_attempts.delete_many({})


def test_reset_password_happy_path_and_single_use(sanne_user, db):
    user_id = str(sanne_user["_id"])
    db.password_reset_tokens.delete_many({"user_id": user_id})
    raw = secrets.token_urlsafe(32)
    db.password_reset_tokens.insert_one({
        "user_id": user_id, "token_hash": _hash_token(raw), "used": False,
        "created_at": _now(), "expires_at": _now() + timedelta(hours=1)
    })
    new_pw = "NewSannePW!2026"
    r = requests.post(f"{API}/auth/reset-password", json={"token": raw, "new_password": new_pw}, timeout=20)
    assert r.status_code == 200, r.text

    # Login with new password works
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": SANNE_EMAIL, "password": new_pw}, timeout=15)
    assert r.status_code == 200, r.text

    # Same token reused → 400
    r = requests.post(f"{API}/auth/reset-password", json={"token": raw, "new_password": "AnotherPW!2026"}, timeout=20)
    assert r.status_code == 400
    assert "ongeldig" in r.text.lower() or "verlopen" in r.text.lower()

    # Restore sanne original password via another reset token
    raw2 = secrets.token_urlsafe(32)
    db.password_reset_tokens.insert_one({
        "user_id": user_id, "token_hash": _hash_token(raw2), "used": False,
        "created_at": _now(), "expires_at": _now() + timedelta(hours=1)
    })
    r = requests.post(f"{API}/auth/reset-password", json={"token": raw2, "new_password": SANNE_PASSWORD}, timeout=20)
    assert r.status_code == 200
    r = requests.post(f"{API}/auth/login", json={"email": SANNE_EMAIL, "password": SANNE_PASSWORD}, timeout=15)
    assert r.status_code == 200, "sanne password NOT restored"


def test_reset_password_expired_token(sanne_user, db):
    user_id = str(sanne_user["_id"])
    raw = secrets.token_urlsafe(32)
    db.password_reset_tokens.insert_one({
        "user_id": user_id, "token_hash": _hash_token(raw), "used": False,
        "created_at": _now() - timedelta(hours=2), "expires_at": _now() - timedelta(hours=1)
    })
    r = requests.post(f"{API}/auth/reset-password", json={"token": raw, "new_password": "Whatever!2026"}, timeout=20)
    assert r.status_code == 400


def test_reset_password_short_password_400(sanne_user, db):
    user_id = str(sanne_user["_id"])
    raw = secrets.token_urlsafe(32)
    db.password_reset_tokens.insert_one({
        "user_id": user_id, "token_hash": _hash_token(raw), "used": False,
        "created_at": _now(), "expires_at": _now() + timedelta(hours=1)
    })
    r = requests.post(f"{API}/auth/reset-password", json={"token": raw, "new_password": "short"}, timeout=20)
    assert r.status_code == 400


def test_other_outstanding_tokens_marked_used(sanne_user, db):
    user_id = str(sanne_user["_id"])
    db.password_reset_tokens.delete_many({"user_id": user_id})
    # Insert 2 outstanding tokens, use one, other must be marked used
    raw_use = secrets.token_urlsafe(32)
    raw_other = secrets.token_urlsafe(32)
    for raw in (raw_use, raw_other):
        db.password_reset_tokens.insert_one({
            "user_id": user_id, "token_hash": _hash_token(raw), "used": False,
            "created_at": _now(), "expires_at": _now() + timedelta(hours=1)
        })
    tmp_pw = "TempPW!2026"
    r = requests.post(f"{API}/auth/reset-password", json={"token": raw_use, "new_password": tmp_pw}, timeout=20)
    assert r.status_code == 200
    other = db.password_reset_tokens.find_one({"token_hash": _hash_token(raw_other)})
    assert other["used"] is True

    # restore sanne
    raw_restore = secrets.token_urlsafe(32)
    db.password_reset_tokens.insert_one({
        "user_id": user_id, "token_hash": _hash_token(raw_restore), "used": False,
        "created_at": _now(), "expires_at": _now() + timedelta(hours=1)
    })
    r = requests.post(f"{API}/auth/reset-password", json={"token": raw_restore, "new_password": SANNE_PASSWORD}, timeout=20)
    assert r.status_code == 200


def test_regression_normal_login_still_works():
    r = requests.post(f"{API}/auth/login", json={"email": SANNE_EMAIL, "password": SANNE_PASSWORD}, timeout=15)
    assert r.status_code == 200
