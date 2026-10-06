"""RSVP & invitation PDF export regression tests."""
import os
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("bojan.vanderheide@gmail.com", "WhiteVision!2026")
DJ_BAS = ("bas@white-vision.nl", "Demo!2027")
CUST_JEROEN = ("jeroen@example.nl", "Demo!2027")
CUST_SANNE = ("sanne@example.nl", "Demo!2027")


def login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login {email} failed: {r.status_code} {r.text}"
    return s, r.json()


@pytest.fixture(scope="module")
def jeroen():
    s, u = login(*CUST_JEROEN)
    r = s.get(f"{API}/events", timeout=15)
    ev = [e for e in r.json() if "Jeroen" in e["title"]][0]
    return s, ev


@pytest.fixture(scope="module")
def admin():
    return login(*ADMIN)


@pytest.fixture(scope="module")
def bas():
    return login(*DJ_BAS)


@pytest.fixture(scope="module")
def sanne():
    return login(*CUST_SANNE)


@pytest.fixture(scope="module")
def shared_invitation(jeroen):
    """Save invitation with rsvp_enabled & share it. Yields (session, event, token). Cleans invitation+rsvps."""
    s, ev = jeroen
    eid = ev["id"]
    body = {
        "title": "TEST_Jeroen & Mark", "subtitle": "TEST", "rsvp_enabled": True,
        "rsvp_deadline": "15 mei 2027", "background_color": "#09090B",
        "text_color": "#F4F4F5", "accent_color": "#D4AF37", "font": "playfair", "layout": "classic",
    }
    r = s.put(f"{API}/events/{eid}/invitation", json=body, timeout=15)
    assert r.status_code == 200
    assert r.json()["rsvp_enabled"] is True
    assert r.json()["rsvp_deadline"] == "15 mei 2027"
    r = s.post(f"{API}/events/{eid}/invitation/share", timeout=15)
    token = r.json()["share_token"]
    yield s, ev, token
    # cleanup: delete all rsvps for this event + invitation document (as test instructions require)
    rsvps = s.get(f"{API}/events/{eid}/rsvps", timeout=15).json()
    for r in rsvps:
        s.delete(f"{API}/rsvps/{r['id']}", timeout=15)


class TestRsvpSave:
    def test_rsvp_fields_persist(self, jeroen):
        s, ev = jeroen
        body = {"title": "TEST_persist", "rsvp_enabled": False, "rsvp_deadline": None,
                "background_color": "#09090B", "text_color": "#F4F4F5", "accent_color": "#D4AF37",
                "font": "playfair", "layout": "classic"}
        r = s.put(f"{API}/events/{ev['id']}/invitation", json=body, timeout=15)
        assert r.status_code == 200
        assert r.json()["rsvp_enabled"] is False
        # Re-fetch
        inv = s.get(f"{API}/events/{ev['id']}/invitation", timeout=15).json()
        assert inv["rsvp_enabled"] is False


class TestPublicRsvp:
    def test_public_invitation_has_rsvp_fields(self, shared_invitation):
        _, _, token = shared_invitation
        r = requests.get(f"{API}/public/invitations/{token}", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["rsvp_enabled"] is True
        assert data["rsvp_deadline"] == "15 mei 2027"
        # event_id must be stripped
        assert "event_id" not in data

    def test_submit_rsvp_yes(self, shared_invitation):
        _, _, token = shared_invitation
        r = requests.post(f"{API}/public/invitations/{token}/rsvp",
                          json={"name": "TEST_Alice", "email": "alice@example.nl",
                                "attending": "yes", "guests": 2, "dietary": "vega",
                                "message": "Blij!"}, timeout=15)
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert r.json()["attending"] == "yes"

    def test_submit_rsvp_no_sets_guests_zero(self, shared_invitation):
        _, ev, token = shared_invitation
        r = requests.post(f"{API}/public/invitations/{token}/rsvp",
                          json={"name": "TEST_Bob", "attending": "no", "guests": 3}, timeout=15)
        assert r.status_code == 200
        # verify via owner list
        s = shared_invitation[0]
        rows = s.get(f"{API}/events/{ev['id']}/rsvps", timeout=15).json()
        bob = [r for r in rows if r["name"] == "TEST_Bob"][0]
        assert bob["guests"] == 0

    def test_submit_rsvp_maybe(self, shared_invitation):
        _, _, token = shared_invitation
        r = requests.post(f"{API}/public/invitations/{token}/rsvp",
                          json={"name": "TEST_Carol", "attending": "maybe", "guests": 1}, timeout=15)
        assert r.status_code == 200

    def test_bad_token_404(self):
        r = requests.post(f"{API}/public/invitations/does-not-exist/rsvp",
                          json={"name": "x", "attending": "yes"}, timeout=15)
        assert r.status_code == 404

    def test_bad_attending(self, shared_invitation):
        _, _, token = shared_invitation
        r = requests.post(f"{API}/public/invitations/{token}/rsvp",
                          json={"name": "TEST_X", "attending": "later"}, timeout=15)
        assert r.status_code == 400

    def test_rsvp_disabled_returns_400(self, jeroen, shared_invitation):
        s, ev, token = shared_invitation
        # disable
        inv = s.get(f"{API}/events/{ev['id']}/invitation", timeout=15).json()
        inv_body = {k: inv.get(k) for k in ("title", "subtitle", "date_text", "time_text",
                     "location", "description", "photo_url", "photo_file_id",
                     "background_color", "text_color", "accent_color", "font", "layout",
                     "rsvp_deadline", "template_id")}
        inv_body["rsvp_enabled"] = False
        s.put(f"{API}/events/{ev['id']}/invitation", json=inv_body, timeout=15)
        r = requests.post(f"{API}/public/invitations/{token}/rsvp",
                          json={"name": "TEST_late", "attending": "yes"}, timeout=15)
        assert r.status_code == 400
        # restore
        inv_body["rsvp_enabled"] = True
        s.put(f"{API}/events/{ev['id']}/invitation", json=inv_body, timeout=15)


class TestRsvpList:
    def test_customer_lists_rsvps(self, shared_invitation):
        s, ev, _ = shared_invitation
        r = s.get(f"{API}/events/{ev['id']}/rsvps", timeout=15)
        assert r.status_code == 200
        rows = r.json()
        names = {r["name"] for r in rows}
        assert "TEST_Alice" in names

    def test_admin_sees_rsvps(self, admin, shared_invitation):
        a_s, _ = admin
        _, ev, _ = shared_invitation
        r = a_s.get(f"{API}/events/{ev['id']}/rsvps", timeout=15)
        assert r.status_code == 200
        assert any(r["name"] == "TEST_Alice" for r in r.json())

    def test_dj_assigned_sees_rsvps(self, bas, shared_invitation):
        b_s, _ = bas
        _, ev, _ = shared_invitation
        r = b_s.get(f"{API}/events/{ev['id']}/rsvps", timeout=15)
        assert r.status_code == 200

    def test_other_customer_cannot_list(self, sanne, shared_invitation):
        o_s, _ = sanne
        _, ev, _ = shared_invitation
        r = o_s.get(f"{API}/events/{ev['id']}/rsvps", timeout=15)
        assert r.status_code == 404

    def test_rsvp_in_stats(self, shared_invitation):
        s, ev, _ = shared_invitation
        data = s.get(f"{API}/events/{ev['id']}", timeout=15).json()
        rsvp_stats = data["stats"]["rsvp"]
        # 3 submissions above: Alice yes 2, Bob no, Carol maybe 1
        assert rsvp_stats["responses"] >= 3
        assert rsvp_stats["attending_guests"] >= 2
        assert rsvp_stats["declined"] >= 1
        assert rsvp_stats["maybe"] >= 1

    def test_delete_rsvp(self, shared_invitation):
        s, ev, _ = shared_invitation
        rows = s.get(f"{API}/events/{ev['id']}/rsvps", timeout=15).json()
        # Delete Carol
        carol = [r for r in rows if r["name"] == "TEST_Carol"][0]
        r = s.delete(f"{API}/rsvps/{carol['id']}", timeout=15)
        assert r.status_code == 200
        rows2 = s.get(f"{API}/events/{ev['id']}/rsvps", timeout=15).json()
        assert not any(r["name"] == "TEST_Carol" for r in rows2)
