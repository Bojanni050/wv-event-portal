"""Backend regression tests for White Vision Portal.

Covers: auth, scope (customer/dj/admin), events, messages/pin/notifications,
music, timeline, files, invitations (incl public share), admin (customers/djs/
templates), WordPress integration. Uses only API; cleans up TEST_* resources.
"""
import io
import os
import uuid
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://my-event-1.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("bojan.vanderheide@gmail.com", "WhiteVision!2026")
DJ_BAS = ("bas@white-vision.nl", "Demo!2027")
DJ_THOMAS = ("thomas@white-vision.nl", "Demo!2027")
CUST_JEROEN = ("jeroen@example.nl", "Demo!2027")
CUST_SANNE = ("sanne@example.nl", "Demo!2027")

WP_API_KEY = "wWMOJEud8qmODhJgNvbNdx8r77c_xWd3"


def login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return s, r.json()


# ------------------- Fixtures -------------------
@pytest.fixture(scope="module")
def admin_sess():
    s, u = login(*ADMIN)
    return s, u


@pytest.fixture(scope="module")
def jeroen_sess():
    s, u = login(*CUST_JEROEN)
    return s, u


@pytest.fixture(scope="module")
def sanne_sess():
    s, u = login(*CUST_SANNE)
    return s, u


@pytest.fixture(scope="module")
def bas_sess():
    s, u = login(*DJ_BAS)
    return s, u


@pytest.fixture(scope="module")
def thomas_sess():
    s, u = login(*DJ_THOMAS)
    return s, u


@pytest.fixture(scope="module")
def jeroen_event(jeroen_sess):
    s, _ = jeroen_sess
    r = s.get(f"{API}/events", timeout=15)
    assert r.status_code == 200
    evs = r.json()
    assert len(evs) >= 1
    ev = [e for e in evs if "Jeroen" in e["title"]][0]
    return ev


# ------------------- Auth -------------------
class TestAuth:
    def test_login_success(self, admin_sess):
        s, u = admin_sess
        assert u["email"] == ADMIN[0]
        assert u["role"] == "admin"
        assert "access_token" in s.cookies

    def test_login_wrong_password(self):
        # Use a brand new TEST_ email so we don't lock out demo users
        email = f"TEST_nolock_{uuid.uuid4().hex[:8]}@example.nl"
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": "wrong"}, timeout=15)
        assert r.status_code == 401
        body = r.json()
        assert "Onjuist" in (body.get("detail") or "")

    def test_me(self, jeroen_sess):
        s, _ = jeroen_sess
        r = s.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 200
        assert r.json()["role"] == "customer"

    def test_refresh(self, jeroen_sess):
        s, _ = jeroen_sess
        r = s.post(f"{API}/auth/refresh", timeout=15)
        assert r.status_code == 200

    def test_me_unauthenticated(self):
        r = requests.get(f"{API}/auth/me", timeout=15)
        assert r.status_code == 401


# ------------------- Scope / RBAC -------------------
class TestScope:
    def test_customer_sees_only_own_event(self, jeroen_sess):
        s, _ = jeroen_sess
        r = s.get(f"{API}/events", timeout=15)
        assert r.status_code == 200
        evs = r.json()
        assert all("Jeroen" in e["title"] for e in evs)
        assert len(evs) == 1

    def test_dj_sees_only_assigned(self, bas_sess, thomas_sess):
        for sess, must_contain in [(bas_sess, "Jeroen"), (thomas_sess, "Sanne")]:
            s, _ = sess
            r = s.get(f"{API}/events", timeout=15)
            assert r.status_code == 200
            evs = r.json()
            assert len(evs) >= 1
            assert all(must_contain in e["title"] for e in evs)

    def test_dj_cannot_access_customers(self, bas_sess):
        s, _ = bas_sess
        # DJ IS staff — list_customers allows require_staff; so this returns 200.
        r = s.get(f"{API}/customers", timeout=15)
        assert r.status_code == 200
        # But DJ cannot CREATE customer (require_admin)
        r = s.post(f"{API}/customers", json={"name": "TEST_x"}, timeout=15)
        assert r.status_code == 403

    def test_dj_cannot_create_template(self, bas_sess):
        s, _ = bas_sess
        r = s.post(f"{API}/invitation-templates", json={"name": "TEST_tpl"}, timeout=15)
        assert r.status_code == 403

    def test_customer_cannot_list_customers(self, jeroen_sess):
        s, _ = jeroen_sess
        r = s.get(f"{API}/customers", timeout=15)
        assert r.status_code == 403


# ------------------- Events -------------------
class TestEvents:
    def test_customer_patch_allowed_fields(self, jeroen_sess, jeroen_event):
        s, _ = jeroen_sess
        r = s.patch(f"{API}/events/{jeroen_event['id']}", json={"guest_count": 141}, timeout=15)
        assert r.status_code == 200
        assert r.json()["guest_count"] == 141
        # revert
        s.patch(f"{API}/events/{jeroen_event['id']}", json={"guest_count": 140}, timeout=15)

    def test_customer_patch_blocked_date(self, jeroen_sess, jeroen_event):
        s, _ = jeroen_sess
        r = s.patch(f"{API}/events/{jeroen_event['id']}", json={"date": "2027-07-01"}, timeout=15)
        assert r.status_code == 403

    def test_customer_cannot_access_other_event(self, jeroen_sess, admin_sess):
        # get an event the customer doesn't own via admin
        admin_s, _ = admin_sess
        other = [e for e in admin_s.get(f"{API}/events", timeout=15).json() if "Jeroen" not in e["title"]][0]
        s, _ = jeroen_sess
        r = s.get(f"{API}/events/{other['id']}", timeout=15)
        assert r.status_code == 404

    def test_progress_structure(self, jeroen_event):
        assert "progress" in jeroen_event
        assert "overall" in jeroen_event["progress"]
        assert len(jeroen_event["progress"]["sections"]) == 5


# ------------------- Messages -------------------
class TestMessages:
    def test_send_and_pin(self, jeroen_sess, jeroen_event):
        s, _ = jeroen_sess
        eid = jeroen_event["id"]
        r = s.post(f"{API}/events/{eid}/messages", json={"text": "TEST_hello"}, timeout=15)
        assert r.status_code == 200
        msg = r.json()
        assert msg["sender_role"] == "customer"
        assert msg["read_by_customer"] is True
        assert msg["read_by_staff"] is False
        mid = msg["id"]
        # Pin
        r = s.patch(f"{API}/messages/{mid}", json={"pinned": True}, timeout=15)
        assert r.status_code == 200 and r.json()["pinned"] is True
        # Cleanup unpin (can't delete via API, but unpin at least)
        s.patch(f"{API}/messages/{mid}", json={"pinned": False}, timeout=15)

    def test_notifications_and_read(self, jeroen_sess, bas_sess, jeroen_event):
        js, _ = jeroen_sess
        bs, _ = bas_sess
        eid = jeroen_event["id"]
        # customer sends
        js.post(f"{API}/events/{eid}/messages", json={"text": "TEST_notif"}, timeout=15)
        # staff notifications should include unread
        notif = bs.get(f"{API}/notifications", timeout=15).json()
        assert notif["total"] >= 1
        # staff reads
        bs.get(f"{API}/events/{eid}/messages", timeout=15)
        notif2 = bs.get(f"{API}/notifications", timeout=15).json()
        assert notif2["total"] <= notif["total"]

    def test_empty_message_rejected(self, jeroen_sess, jeroen_event):
        s, _ = jeroen_sess
        r = s.post(f"{API}/events/{jeroen_event['id']}/messages", json={"text": "  "}, timeout=15)
        assert r.status_code == 400


# ------------------- Music -------------------
class TestMusic:
    def test_crud(self, jeroen_sess, jeroen_event):
        s, _ = jeroen_sess
        eid = jeroen_event["id"]
        r = s.post(f"{API}/events/{eid}/music",
                   json={"category": "must_play", "title": "TEST_Song", "artist": "TEST_Artist"}, timeout=15)
        assert r.status_code == 200
        mid = r.json()["id"]
        # Patch
        r = s.patch(f"{API}/music/{mid}", json={"category": "favorite"}, timeout=15)
        assert r.status_code == 200 and r.json()["category"] == "favorite"
        # Delete
        assert s.delete(f"{API}/music/{mid}", timeout=15).status_code == 200

    def test_invalid_category(self, jeroen_sess, jeroen_event):
        s, _ = jeroen_sess
        r = s.post(f"{API}/events/{jeroen_event['id']}/music",
                   json={"category": "bogus", "title": "x"}, timeout=15)
        assert r.status_code == 400


# ------------------- Timeline -------------------
class TestTimeline:
    def test_suggest_edit_delete(self, jeroen_sess, jeroen_event):
        s, _ = jeroen_sess
        eid = jeroen_event["id"]
        r = s.post(f"{API}/events/{eid}/timeline",
                   json={"time": "23:00", "title": "TEST_moment"}, timeout=15)
        assert r.status_code == 200
        item = r.json()
        assert item["status"] == "suggested"
        tid = item["id"]
        # edit
        r = s.patch(f"{API}/timeline/{tid}", json={"time": "23:15"}, timeout=15)
        assert r.status_code == 200 and r.json()["time"] == "23:15"
        # customer cannot confirm
        r = s.patch(f"{API}/timeline/{tid}", json={"status": "confirmed"}, timeout=15)
        assert r.status_code == 403
        # cleanup
        assert s.delete(f"{API}/timeline/{tid}", timeout=15).status_code == 200

    def test_staff_confirm(self, bas_sess, jeroen_sess, jeroen_event):
        cs, _ = jeroen_sess
        bs, _ = bas_sess
        eid = jeroen_event["id"]
        r = cs.post(f"{API}/events/{eid}/timeline",
                    json={"time": "23:30", "title": "TEST_staff_confirm"}, timeout=15)
        tid = r.json()["id"]
        r = bs.patch(f"{API}/timeline/{tid}", json={"status": "confirmed"}, timeout=15)
        assert r.status_code == 200 and r.json()["status"] == "confirmed"
        # customer can't edit confirmed
        r = cs.patch(f"{API}/timeline/{tid}", json={"time": "23:45"}, timeout=15)
        assert r.status_code == 403
        # staff cleanup
        assert bs.delete(f"{API}/timeline/{tid}", timeout=15).status_code == 200

    def test_bad_time(self, jeroen_sess, jeroen_event):
        s, _ = jeroen_sess
        r = s.post(f"{API}/events/{jeroen_event['id']}/timeline",
                   json={"time": "25:99", "title": "x"}, timeout=15)
        assert r.status_code == 400


# ------------------- Files -------------------
PNG_BYTES = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
             b"\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x8d\x07\x8c\x00\x00\x00\x00IEND\xaeB`\x82")


class TestFiles:
    def test_upload_list_delete(self, jeroen_sess, jeroen_event):
        s, _ = jeroen_sess
        eid = jeroen_event["id"]
        r = s.post(f"{API}/events/{eid}/files",
                   files={"file": ("TEST_pic.png", io.BytesIO(PNG_BYTES), "image/png")},
                   data={"category": "image"}, timeout=20)
        assert r.status_code == 200
        fid = r.json()["id"]
        # list contains
        files = s.get(f"{API}/events/{eid}/files", timeout=15).json()
        assert any(f["id"] == fid for f in files)
        # delete own
        assert s.delete(f"{API}/files/{fid}", timeout=15).status_code == 200

    def test_customer_cannot_delete_staff_file(self, bas_sess, jeroen_sess, jeroen_event):
        bs, _ = bas_sess
        cs, _ = jeroen_sess
        eid = jeroen_event["id"]
        r = bs.post(f"{API}/events/{eid}/files",
                    files={"file": ("TEST_staff.png", io.BytesIO(PNG_BYTES), "image/png")},
                    data={"category": "image"}, timeout=20)
        fid = r.json()["id"]
        r = cs.delete(f"{API}/files/{fid}", timeout=15)
        assert r.status_code == 403
        # staff cleanup
        assert bs.delete(f"{API}/files/{fid}", timeout=15).status_code == 200


# ------------------- Invitations -------------------
class TestInvitations:
    def test_templates_visibility(self, admin_sess, jeroen_sess):
        a_s, _ = admin_sess
        c_s, _ = jeroen_sess
        # Create hidden template
        r = a_s.post(f"{API}/invitation-templates",
                     json={"name": "TEST_hidden", "active": False}, timeout=15)
        assert r.status_code == 200
        tid = r.json()["id"]
        try:
            admin_tpls = a_s.get(f"{API}/invitation-templates", timeout=15).json()
            cust_tpls = c_s.get(f"{API}/invitation-templates", timeout=15).json()
            assert any(t["id"] == tid for t in admin_tpls)
            assert not any(t["id"] == tid for t in cust_tpls)
        finally:
            a_s.delete(f"{API}/invitation-templates/{tid}", timeout=15)

    def test_save_and_share(self, jeroen_sess, jeroen_event):
        s, _ = jeroen_sess
        eid = jeroen_event["id"]
        r = s.put(f"{API}/events/{eid}/invitation",
                  json={"title": "TEST_Save the date", "subtitle": "TEST"}, timeout=15)
        assert r.status_code == 200
        r = s.post(f"{API}/events/{eid}/invitation/share", timeout=15)
        assert r.status_code == 200
        token = r.json()["share_token"]
        # public (no auth)
        r = requests.get(f"{API}/public/invitations/{token}", timeout=15)
        assert r.status_code == 200
        assert r.json()["title"] == "TEST_Save the date"
        # Check progress invitation=100
        ev = s.get(f"{API}/events/{eid}", timeout=15).json()
        inv_sec = [sec for sec in ev["progress"]["sections"] if sec["key"] == "invitation"][0]
        assert inv_sec["percent"] == 100


# ------------------- Admin / Create customer-with-login -------------------
class TestAdmin:
    def test_overview(self, admin_sess):
        s, _ = admin_sess
        r = s.get(f"{API}/admin/overview", timeout=15)
        assert r.status_code == 200
        data = r.json()
        for k in ("upcoming", "attention", "unread", "incomplete"):
            assert k in data["counts"]

    def test_create_customer_with_login_and_authenticate(self, admin_sess):
        s, _ = admin_sess
        email = f"test_c_{uuid.uuid4().hex[:8]}@example.nl"
        pw = "TempPass123!"
        r = s.post(f"{API}/customers",
                   json={"name": "TEST_Customer", "email": email, "password": pw}, timeout=15)
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        assert r.json()["has_login"] is True
        try:
            # login as new customer
            cs, me = login(email, pw)
            assert me["role"] == "customer"
            # customer has no event, so /events empty
            evs = cs.get(f"{API}/events", timeout=15).json()
            assert evs == []
        finally:
            # cleanup user then customer
            s.delete(f"{API}/customers/{cid}", timeout=15)

    def test_create_dj(self, admin_sess):
        s, _ = admin_sess
        r = s.post(f"{API}/djs", json={"name": "TEST_DJ"}, timeout=15)
        assert r.status_code == 200
        # No delete endpoint for djs; leave as-is but will remain. mark TEST_ for cleanup elsewhere.

    def test_event_status_change(self, admin_sess):
        s, _ = admin_sess
        evs = s.get(f"{API}/events", timeout=15).json()
        ev = [e for e in evs if "Jeroen" in e["title"]][0]
        orig = ev["status"]
        r = s.patch(f"{API}/events/{ev['id']}", json={"status": "ready"}, timeout=15)
        assert r.status_code == 200 and r.json()["status"] == "ready"
        # revert
        s.patch(f"{API}/events/{ev['id']}", json={"status": orig}, timeout=15)


# ------------------- WordPress integration -------------------
class TestWordPress:
    def test_wrong_key(self):
        r = requests.post(f"{API}/integrations/wordpress/sync",
                          json={"customer": {"external_id": "x", "name": "x"}},
                          headers={"X-API-Key": "wrong"}, timeout=15)
        assert r.status_code == 401

    def test_sync_upsert(self, admin_sess):
        ext = f"TEST_{uuid.uuid4().hex[:6]}"
        payload = {"customer": {"external_id": ext, "name": "TEST_WP_Customer",
                                "email": f"{ext}@example.nl"},
                   "event": {"external_id": ext + "_e", "title": "TEST_WP_Event",
                             "date": "2027-10-01"}}
        r = requests.post(f"{API}/integrations/wordpress/sync", json=payload,
                          headers={"X-API-Key": WP_API_KEY}, timeout=15)
        assert r.status_code == 200, r.text
        cid = r.json()["customer_id"]
        eid = r.json()["event_id"]
        assert cid and eid
        # Upsert again: same ids
        r2 = requests.post(f"{API}/integrations/wordpress/sync", json=payload,
                           headers={"X-API-Key": WP_API_KEY}, timeout=15)
        assert r2.json()["customer_id"] == cid
        assert r2.json()["event_id"] == eid
        # cleanup via admin
        s, _ = admin_sess
        s.delete(f"{API}/events/{eid}", timeout=15)
        s.delete(f"{API}/customers/{cid}", timeout=15)
