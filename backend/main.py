"""The UnderCover backend."""

import json
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException

from backend import db
from backend.models import (
    Claim,
    ClaimSummary,
    Customer,
    DecisionIn,
    Handler,
    PaymentIn,
    Policy,
    PolicyWording,
    SignOffIn,
    Step,
    StepIn,
)

LIMIT: float = db.COMPANY["payout_approval_limit"]

CLAIM_ROWS = """SELECT c.status, c.data, d.decision, d.payout,
    json_extract(u.data, '$.name') AS customer_name
FROM claims c
JOIN customers u ON u.customer_id = json_extract(c.data, '$.customer_id')
LEFT JOIN decisions d ON d.claim_id = c.claim_id
ORDER BY c.claim_id"""

SIGN_OFF = """SELECT s.handler_id, json_extract(h.data, '$.name') AS handler_name,
    s.signed_off_at
FROM sign_offs s JOIN handlers h ON h.handler_id = s.handler_id
WHERE s.claim_id = ?"""


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    db.init()
    yield


app = FastAPI(title="UnderCover", lifespan=lifespan)


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def money(amount: float) -> str:
    return f"${amount:,.2f}"


def record(conn: sqlite3.Connection, query: str, key: str, what: str) -> dict[str, Any]:
    """Return the record the query finds for the key, or raise a 404."""
    row = conn.execute(query, (key,)).fetchone()
    if row is None:
        raise HTTPException(404, f"{what} {key} was not found.")
    return json.loads(row["data"])


def load_claim(conn: sqlite3.Connection, claim_id: str) -> Claim:
    """Return a claim with its status, decision, payment and sign-off, or a 404."""
    query = """SELECT json_set(data, '$.status', status) AS data
        FROM claims WHERE claim_id = ?"""
    claim = record(conn, query, claim_id, "Claim")
    key = (claim_id,)
    decision = conn.execute("SELECT * FROM decisions WHERE claim_id = ?", key)
    payment = conn.execute("SELECT * FROM payments WHERE claim_id = ?", key)
    sign_off = conn.execute(SIGN_OFF, key)
    return Claim.model_validate(
        {
            **claim,
            "decision": decision.fetchone(),
            "payment": payment.fetchone(),
            "sign_off": sign_off.fetchone(),
        }
    )


def set_status(conn: sqlite3.Connection, claim_id: str, status: str) -> None:
    conn.execute("UPDATE claims SET status = ? WHERE claim_id = ?", (status, claim_id))


@app.get("/api/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the backend is running."""
    return {"status": "ok"}


@app.get("/api/claims", operation_id="list_claims")
def list_claims() -> list[ClaimSummary]:
    """List every claim in the queue with where it stands and its decision."""
    with db.connect() as conn:
        rows = conn.execute(CLAIM_ROWS).fetchall()
    return [
        ClaimSummary.model_validate(
            {
                **json.loads(row["data"]),
                "status": row["status"],
                "customer_name": row["customer_name"],
                "decision": row["decision"],
                "payout": row["payout"],
            }
        )
        for row in rows
    ]


@app.get("/api/claims/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str) -> Claim:
    """Get a claim in full, with its status, decision, payment and sign-off."""
    with db.connect() as conn:
        return load_claim(conn, claim_id)


@app.get("/api/policies/{policy_id}", operation_id="get_policy")
def get_policy(policy_id: str) -> Policy:
    """Get a policy with its plan's limits, its add-ons, its trip and its travelers."""
    with db.connect() as conn:
        policy = record(
            conn, "SELECT data FROM policies WHERE policy_id = ?", policy_id, "Policy"
        )
    return Policy.model_validate({**policy, "plan_details": db.PLANS[policy["plan"]]})


@app.get("/api/customers/{customer_id}", operation_id="get_customer")
def get_customer(customer_id: str) -> Customer:
    """Get a customer's details and their claim history."""
    query = "SELECT data FROM customers WHERE customer_id = ?"
    with db.connect() as conn:
        return Customer.model_validate(record(conn, query, customer_id, "Customer"))


@app.get("/api/handlers", operation_id="list_handlers")
def list_handlers() -> list[Handler]:
    """List the claims handlers."""
    with db.connect() as conn:
        rows = conn.execute("SELECT data FROM handlers ORDER BY handler_id").fetchall()
    return [Handler.model_validate_json(row["data"]) for row in rows]


@app.get("/api/policy-wording", operation_id="get_policy_wording")
def get_policy_wording() -> PolicyWording:
    """Get the policy wording that decisions follow."""
    return PolicyWording(
        version=db.COMPANY["policy_wording_version"], text=db.POLICY_WORDING
    )


@app.post("/api/claims/{claim_id}/start", operation_id="start_claim")
def start_claim(claim_id: str) -> Claim:
    """Start work on a waiting claim, or start again on a claim in progress."""
    with db.connect() as conn:
        status = load_claim(conn, claim_id).status
        if status not in {"waiting", "in_progress"}:
            raise HTTPException(
                409, f"Claim {claim_id} is already {status.replace('_', ' ')}."
            )
        conn.execute("DELETE FROM steps WHERE claim_id = ?", (claim_id,))
        set_status(conn, claim_id, "in_progress")
        return load_claim(conn, claim_id)


@app.post("/api/claims/{claim_id}/steps", operation_id="add_step")
def add_step(claim_id: str, step: StepIn) -> Step:
    """Record a step the agent takes while it works on a claim."""
    with db.connect() as conn:
        load_claim(conn, claim_id)
        row = conn.execute(
            """INSERT INTO steps (claim_id, thread_id, kind, text, created_at)
            VALUES (?, ?, ?, ?, ?) RETURNING *""",
            (claim_id, step.thread_id, step.kind, step.text, now()),
        ).fetchone()
        return Step.model_validate(row)


@app.get("/api/claims/{claim_id}/steps", operation_id="list_steps")
def list_steps(claim_id: str) -> list[Step]:
    """List the steps the agent has taken on a claim, in order."""
    with db.connect() as conn:
        load_claim(conn, claim_id)
        rows = conn.execute(
            "SELECT * FROM steps WHERE claim_id = ? ORDER BY step_id", (claim_id,)
        ).fetchall()
    return [Step.model_validate(row) for row in rows]


@app.post("/api/claims/{claim_id}/decision", operation_id="decide_claim")
def decide_claim(claim_id: str, decision: DecisionIn) -> Claim:
    """Approve a claim with a payout, or decline or refer it with a payout of $0."""
    with db.connect() as conn:
        status = load_claim(conn, claim_id).status
        if status != "in_progress":
            raise HTTPException(
                409,
                f"Claim {claim_id} is {status.replace('_', ' ')}. "
                "Only a claim in progress can be decided.",
            )
        approve = decision.decision == "approve"
        if (approve and decision.payout <= 0) or (not approve and decision.payout != 0):
            raise HTTPException(
                422,
                "An approval needs a payout above $0, and a decline or a "
                "referral has a payout of $0.",
            )
        conn.execute(
            "INSERT INTO decisions VALUES (?, ?, ?, ?, ?, ?)",
            (
                claim_id,
                decision.decision,
                round(decision.payout, 2),
                decision.reasons,
                decision.policy_section,
                now(),
            ),
        )
        over_limit = decision.payout > LIMIT
        set_status(conn, claim_id, "waiting_for_sign_off" if over_limit else "decided")
        return load_claim(conn, claim_id)


@app.post("/api/claims/{claim_id}/payment", operation_id="pay_claim")
def pay_claim(claim_id: str, payment: PaymentIn) -> Claim:
    """Pay an approved claim its payout, unless the payout waits for sign-off."""
    with db.connect() as conn:
        claim = load_claim(conn, claim_id)
        approved = claim.decision
        if approved is None or approved.decision != "approve":
            raise HTTPException(
                409, f"Claim {claim_id} is not approved, so there is nothing to pay."
            )
        if claim.payment is not None:
            raise HTTPException(409, f"Claim {claim_id} has already been paid.")
        if approved.payout > LIMIT and claim.sign_off is None:
            raise HTTPException(
                403,
                f"The payout of {money(approved.payout)} is over the "
                f"{money(LIMIT)} approval limit, so a handler must sign off "
                "before it is paid. The payment is held until then.",
            )
        if round(payment.amount, 2) != approved.payout:
            raise HTTPException(
                409,
                f"The payment must be the approved payout of {money(approved.payout)}.",
            )
        conn.execute(
            "INSERT INTO payments VALUES (?, ?, ?)", (claim_id, approved.payout, now())
        )
        return load_claim(conn, claim_id)


@app.post("/api/claims/{claim_id}/sign-off", operation_id="sign_off_claim")
def sign_off_claim(claim_id: str, sign_off: SignOffIn) -> Claim:
    """Sign off a payout over the approval limit as a handler, which pays it."""
    query = "SELECT data FROM handlers WHERE handler_id = ?"
    with db.connect() as conn:
        claim = load_claim(conn, claim_id)
        record(conn, query, sign_off.handler_id, "Handler")
        if claim.status != "waiting_for_sign_off":
            raise HTTPException(409, f"Claim {claim_id} is not waiting for sign-off.")
        payout = conn.execute(
            "SELECT payout FROM decisions WHERE claim_id = ?", (claim_id,)
        ).fetchone()["payout"]
        conn.execute(
            "INSERT INTO sign_offs VALUES (?, ?, ?)",
            (claim_id, sign_off.handler_id, now()),
        )
        conn.execute("INSERT INTO payments VALUES (?, ?, ?)", (claim_id, payout, now()))
        set_status(conn, claim_id, "decided")
        return load_claim(conn, claim_id)
