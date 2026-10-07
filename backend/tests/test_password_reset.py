"""Password reset flow tests (forgot-password, reset-password).

Uses a TEST customer created via admin API with email delivered@resend.dev
for forgot-password/rate-limit tests. Uses sanne account for the end-to-end
reset flow with a token inserted directly into Postgres (restores password at
the end).
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import pytest
import requests

from tests.helpers import (API, ADMIN, DEMO_PASSWORD, SANDBOX_EMAIL, add_reset_token, clear_login_attempts,
                           count_reset_tokens, delete_reset_tokens, get_reset_token_by_hash, get_user,
                           list_reset_tokens, login)

SANNE_EMAIL = "sanne@example.nl"
SANNE_PASSWORD = DEMO_PASSWORD


def _hash_token(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def _now():
    return datetime.now(timezone.utc)


@pytest.fixture(scope="module")
def admin_sess():
    return login(*ADMIN)[0]


@pytest.fixture(scope="module")
def test_customer(admin_sess):
    payload = {"name": "TEST_Reset", "email": SANDBOX_EMAIL, "password": "TestPass123"}
    r = admin_sess.post(f"{API}/customers", json=payload, timeout=20)
    assert r.status_code in (200, 201), r.text
    cid = r.json()["id"]
    u = get_user(SANDBOX_EMAIL)
    assert u, "customer user not created"
    yield cid, u["id"], payload["email"], payload["password"]
    # Cleanup
    try:
        admin_sess.delete(f"{API}/customers/{cid}", timeout=15)
    except Exception:
        pass
    delete_reset_tokens()
    clear_login_attempts()


# --- forgot-password generic response ---
def test_forgot_password_unknown_email_generic_200():
    r = requests.post(f"{API}/auth/forgot-password", json={"email": "no-such-user-xyz@example.nl"}, timeout=20)
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "bekend" in data["message"].lower()


def test_forgot_password_known_user_generic_200_and_token_stored(test_customer):
    cid, uid, email, _pw = test_customer
    r = requests.post(f"{API}/auth/forgot-password", json={"email": email}, timeout=25)
    assert r.status_code == 200
    assert r.json()["ok"] is True
    # token row created
    tokens = list_reset_tokens(uid)
    assert len(tokens) >= 1
    t = tokens[-1]
    assert t["used"] is False
    assert t["expires_at"] > _now()
    # token_hash is a 64-char hex (sha256)
    assert len(t["token_hash"]) == 64


def test_forgot_password_rate_limit(test_customer):
    cid, uid, email, _ = test_customer
    before = count_reset_tokens(uid)
    for _ in range(max(0, 3 - before)):
        r = requests.post(f"{API}/auth/forgot-password", json={"email": email}, timeout=25)
        assert r.status_code == 200
    at_three = count_reset_tokens(uid)
    assert at_three >= 3, f"expected >=3 tokens, got {at_three}"
    # 4th request -> still generic 200, no new token
    r = requests.post(f"{API}/auth/forgot-password", json={"email": email}, timeout=25)
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert count_reset_tokens(uid) == at_three


# --- reset-password flow against sanne ---
@pytest.fixture(scope="module")
def sanne_user():
    u = get_user(SANNE_EMAIL)
    assert u, "sanne user missing"
    yield u
    # restore password at end of module
    requests.post(f"{API}/auth/login", json={"email": SANNE_EMAIL, "password": SANNE_PASSWORD}, timeout=15)
    delete_reset_tokens()
    clear_login_attempts()


def test_reset_password_happy_path_and_single_use(sanne_user):
    user_id = sanne_user["id"]
    delete_reset_tokens(user_id)
    raw = secrets.token_urlsafe(32)
    add_reset_token(user_id, _hash_token(raw), created_at=_now(), expires_at=_now() + timedelta(hours=1))
    new_pw = "NewSannePW!2026"
    r = requests.post(f"{API}/auth/reset-password", json={"token": raw, "new_password": new_pw}, timeout=20)
    assert r.status_code == 200, r.text

    # Login with new password works
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": SANNE_EMAIL, "password": new_pw}, timeout=15)
    assert r.status_code == 200, r.text

    # Same token reused -> 400
    r = requests.post(f"{API}/auth/reset-password", json={"token": raw, "new_password": "AnotherPW!2026"}, timeout=20)
    assert r.status_code == 400
    assert "ongeldig" in r.text.lower() or "verlopen" in r.text.lower()

    # Restore sanne original password via another reset token
    raw2 = secrets.token_urlsafe(32)
    add_reset_token(user_id, _hash_token(raw2), created_at=_now(), expires_at=_now() + timedelta(hours=1))
    r = requests.post(f"{API}/auth/reset-password", json={"token": raw2, "new_password": SANNE_PASSWORD}, timeout=20)
    assert r.status_code == 200
    r = requests.post(f"{API}/auth/login", json={"email": SANNE_EMAIL, "password": SANNE_PASSWORD}, timeout=15)
    assert r.status_code == 200, "sanne password NOT restored"


def test_reset_password_expired_token(sanne_user):
    user_id = sanne_user["id"]
    raw = secrets.token_urlsafe(32)
    add_reset_token(user_id, _hash_token(raw), created_at=_now() - timedelta(hours=2),
                    expires_at=_now() - timedelta(hours=1))
    r = requests.post(f"{API}/auth/reset-password", json={"token": raw, "new_password": "Whatever!2026"}, timeout=20)
    assert r.status_code == 400


def test_reset_password_short_password_400(sanne_user):
    user_id = sanne_user["id"]
    raw = secrets.token_urlsafe(32)
    add_reset_token(user_id, _hash_token(raw), created_at=_now(), expires_at=_now() + timedelta(hours=1))
    r = requests.post(f"{API}/auth/reset-password", json={"token": raw, "new_password": "short"}, timeout=20)
    assert r.status_code == 400


def test_other_outstanding_tokens_marked_used(sanne_user):
    user_id = sanne_user["id"]
    delete_reset_tokens(user_id)
    # Insert 2 outstanding tokens, use one, other must be marked used
    raw_use = secrets.token_urlsafe(32)
    raw_other = secrets.token_urlsafe(32)
    for raw in (raw_use, raw_other):
        add_reset_token(user_id, _hash_token(raw), created_at=_now(), expires_at=_now() + timedelta(hours=1))
    tmp_pw = "TempPW!2026"
    r = requests.post(f"{API}/auth/reset-password", json={"token": raw_use, "new_password": tmp_pw}, timeout=20)
    assert r.status_code == 200
    other = get_reset_token_by_hash(_hash_token(raw_other))
    assert other["used"] is True

    # restore sanne
    raw_restore = secrets.token_urlsafe(32)
    add_reset_token(user_id, _hash_token(raw_restore), created_at=_now(), expires_at=_now() + timedelta(hours=1))
    r = requests.post(f"{API}/auth/reset-password", json={"token": raw_restore, "new_password": SANNE_PASSWORD}, timeout=20)
    assert r.status_code == 200


def test_regression_normal_login_still_works():
    r = requests.post(f"{API}/auth/login", json={"email": SANNE_EMAIL, "password": SANNE_PASSWORD}, timeout=15)
    assert r.status_code == 200
