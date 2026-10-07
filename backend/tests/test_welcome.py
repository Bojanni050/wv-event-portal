"""Tests for admin welcome-email flow (POST /api/customers?send_welcome=true & /customers/{id}/welcome)."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import pytest
import requests

from tests.helpers import (API, ADMIN, DJ_BAS, SANDBOX_EMAIL, add_reset_token, clear_login_attempts,
                           count_customers, delete_customer, delete_customer_by_id, delete_user,
                           get_user, list_reset_tokens, login)


def _now():
    return datetime.now(timezone.utc)


@pytest.fixture(scope="module")
def admin():
    return login(*ADMIN)[0]


@pytest.fixture(scope="module")
def dj():
    return login(*DJ_BAS)[0]


def _cleanup_sandbox():
    if get_user(SANDBOX_EMAIL):
        delete_user(SANDBOX_EMAIL)
    delete_customer(SANDBOX_EMAIL)


@pytest.fixture
def clean_sandbox():
    _cleanup_sandbox()
    yield
    _cleanup_sandbox()


def test_create_customer_with_welcome(admin, clean_sandbox):
    r = admin.post(f"{API}/customers",
                   json={"name": "TEST_Welkom", "email": SANDBOX_EMAIL, "send_welcome": True})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["has_login"] is True
    assert data["email"] == SANDBOX_EMAIL
    # user exists with role=customer, linked to customer_id
    user = get_user(SANDBOX_EMAIL)
    assert user and user["role"] == "customer"
    assert user["customer_id"] == data["id"]

    if data.get("welcome_error"):
        pytest.skip(f"Upstream email provider failed: {data['welcome_error']}")
    assert data.get("welcome_sent_at")

    # token row with purpose=welcome and ~7 day expiry
    toks = [t for t in list_reset_tokens(user["id"]) if t["purpose"] == "welcome"]
    assert toks
    tok = toks[-1]
    assert tok["used"] is False
    delta = tok["expires_at"] - tok["created_at"]
    assert timedelta(days=6, hours=23) < delta < timedelta(days=7, hours=1)


def test_welcome_requires_email(admin):
    r = admin.post(f"{API}/customers",
                   json={"name": "TEST_NoEmail", "send_welcome": True})
    # Backend accepts but sends no welcome (no email): 200, has_login False, no welcome_sent_at
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["has_login"] is False
    assert not data.get("welcome_sent_at")
    delete_customer_by_id(data["id"])


def test_create_welcome_duplicate_email_rolls_back(admin, clean_sandbox):
    # bas@example.nl already has an account (DJ)
    before = count_customers("bas@example.nl")
    r = admin.post(f"{API}/customers",
                   json={"name": "TEST_Dup", "email": "bas@example.nl", "send_welcome": True})
    assert r.status_code == 400, r.text
    assert "account" in r.json().get("detail", "").lower()
    after = count_customers("bas@example.nl")
    assert after == before  # no orphan customer


def test_resend_welcome_rate_limit(admin, clean_sandbox):
    """Avoid real email provider rate limits by seeding 3 fake welcome tokens, then calling resend."""
    r = admin.post(f"{API}/customers",
                   json={"name": "TEST_Rate", "email": SANDBOX_EMAIL,
                         "send_welcome": False, "password": "InitPass123"})
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    user = get_user(SANDBOX_EMAIL)
    # Seed 3 recent welcome tokens -> backend should hit 429 immediately on 4th
    for _ in range(3):
        add_reset_token(user["id"], secrets.token_hex(32), purpose="welcome",
                        created_at=_now() - timedelta(minutes=5), expires_at=_now() + timedelta(days=7))
    r4 = admin.post(f"{API}/customers/{cid}/welcome")
    assert r4.status_code == 429, r4.text
    assert "welkomstmail" in r4.json()["detail"].lower()


def test_dj_cannot_send_welcome(dj, admin, clean_sandbox):
    r = admin.post(f"{API}/customers",
                   json={"name": "TEST_Perm", "email": SANDBOX_EMAIL, "send_welcome": False,
                         "password": "InitPass123"})
    assert r.status_code == 200
    cid = r.json()["id"]
    rdj = dj.post(f"{API}/customers/{cid}/welcome")
    assert rdj.status_code == 403


def test_welcome_token_reset_flow(clean_sandbox):
    s = login(*ADMIN)[0]
    r = s.post(f"{API}/customers",
               json={"name": "TEST_Flow", "email": SANDBOX_EMAIL, "send_welcome": False,
                     "password": "TempPass123"})
    assert r.status_code == 200
    user = get_user(SANDBOX_EMAIL)
    raw = secrets.token_urlsafe(32)
    add_reset_token(user["id"], hashlib.sha256(raw.encode()).hexdigest(), purpose="welcome",
                    created_at=_now(), expires_at=_now() + timedelta(days=7))
    # reset password with raw token
    rr = requests.post(f"{API}/auth/reset-password",
                       json={"token": raw, "new_password": "NewPass!2026"}, timeout=30)
    assert rr.status_code == 200, rr.text
    # login with new password
    rl = requests.post(f"{API}/auth/login",
                       json={"email": SANDBOX_EMAIL, "password": "NewPass!2026"}, timeout=30)
    assert rl.status_code == 200, rl.text
    me = rl.json()
    assert me["role"] == "customer"


def test_regression_create_without_welcome_with_password(admin, clean_sandbox):
    r = admin.post(f"{API}/customers",
                   json={"name": "TEST_Classic", "email": SANDBOX_EMAIL,
                         "send_welcome": False, "password": "Secret!2026"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["has_login"] is True
    assert not data.get("welcome_sent_at")
    # user should be able to login immediately
    rl = requests.post(f"{API}/auth/login",
                       json={"email": SANDBOX_EMAIL, "password": "Secret!2026"}, timeout=30)
    assert rl.status_code == 200


def teardown_module(module):
    _cleanup_sandbox()
    clear_login_attempts()
