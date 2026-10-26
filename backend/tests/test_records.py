from pathlib import Path

from fastapi.testclient import TestClient

from backend import db
from backend.main import app

COUNTS = """SELECT (SELECT COUNT(*) FROM claims), (SELECT COUNT(*) FROM policies),
(SELECT COUNT(*) FROM customers), (SELECT COUNT(*) FROM handlers)"""


def test_startup_creates_and_seeds_the_database(tmp_path, monkeypatch):
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "new.db"))
    with TestClient(app):
        pass
    assert (tmp_path / "new.db").exists()
    with db.connect() as conn:
        assert list(conn.execute(COUNTS).fetchone().values()) == [25, 50, 49, 3]


def test_startup_keeps_existing_data(client):
    with db.connect() as conn:
        conn.execute("UPDATE claims SET status = 'decided' WHERE claim_id = 'CLM-1001'")
    with TestClient(app):
        pass
    assert client.get("/api/claims/CLM-1001").json()["status"] == "decided"


def test_reset_brings_back_the_queue(client):
    with db.connect() as conn:
        conn.execute("UPDATE claims SET status = 'decided'")
        conn.execute("DELETE FROM customers")
    db.reset()
    claims = client.get("/api/claims").json()
    assert len(claims) == 25
    assert {claim["status"] for claim in claims} == {"waiting"}


def test_list_claims(client):
    claims = client.get("/api/claims").json()
    assert len(claims) == 25
    assert claims[0] == {
        "claim_id": "CLM-1001",
        "customer_name": "Maya Patel",
        "claim_type": "trip_delay",
        "summary": "Flight home canceled by the airline, rebooked the next morning",
        "amount_claimed": 420.0,
        "submitted_on": "2026-06-24",
        "status": "waiting",
        "decision": None,
        "payout": None,
    }


def test_get_claim(client):
    claim = client.get("/api/claims/CLM-1001").json()
    assert claim["customer_id"] == "CUS-3001"
    assert claim["story"].startswith("My flight home from Rome")
    assert len(claim["items"]) == 3
    assert len(claim["documents"]) == 4
    assert claim["status"] == "waiting"


def test_get_policy(client):
    policy = client.get("/api/policies/POL-2001").json()
    assert policy["plan"] == "premium"
    assert policy["plan_details"]["name"] == "UnderCover Premium"
    assert policy["plan_details"]["deductible"] == 50.0
    assert policy["plan_details"]["per_item_limit"] == 300.0
    assert policy["travelers"] == ["Maya Patel"]


def test_get_customer(client):
    customer = client.get("/api/customers/CUS-3001").json()
    assert customer["name"] == "Maya Patel"
    assert [c["claim_id"] for c in customer["previous_claims"]] == ["CLM-0412"]


def test_list_handlers(client):
    names = [h["name"] for h in client.get("/api/handlers").json()]
    assert names == ["Dana Whitfield", "Marcus Oyelaran", "Priya Raman"]


def test_get_policy_wording(client):
    wording = client.get("/api/policy-wording").json()
    assert wording["version"] == "2026.1"
    assert wording["text"].startswith("# UnderCover Travel Insurance: Policy Wording")


def test_get_instructions(client):
    instructions = client.get("/api/instructions").json()
    assert instructions["text"] == Path("backend/instructions.md").read_text(
        encoding="utf-8"
    )
    assert instructions["text"].startswith("# The UnderCover Agent")


def test_unknown_records_are_not_found(client):
    for path, detail in [
        ("/api/claims/CLM-9999", "Claim CLM-9999 was not found."),
        ("/api/policies/POL-9999", "Policy POL-9999 was not found."),
        ("/api/customers/CUS-9999", "Customer CUS-9999 was not found."),
    ]:
        response = client.get(path)
        assert response.status_code == 404
        assert response.json() == {"detail": detail}
