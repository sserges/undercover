"""The UnderCover backend."""

import json
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException

from backend import db
from backend.models import (
    Claim,
    ClaimSummary,
    Customer,
    Handler,
    Policy,
    PolicyWording,
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    db.init()
    yield


app = FastAPI(title="UnderCover", lifespan=lifespan)


def record(conn: sqlite3.Connection, query: str, key: str, what: str) -> dict[str, Any]:
    """Return the record the query finds for the key, or raise a 404."""
    row = conn.execute(query, (key,)).fetchone()
    if row is None:
        raise HTTPException(404, f"{what} {key} was not found.")
    return json.loads(row["data"])


def claim_record(conn: sqlite3.Connection, claim_id: str) -> dict[str, Any]:
    """Return a claim with its status, or raise a 404."""
    query = """SELECT json_set(data, '$.status', status) AS data
        FROM claims WHERE claim_id = ?"""
    return record(conn, query, claim_id, "Claim")


@app.get("/api/health", operation_id="health")
def health() -> dict[str, str]:
    """Check that the backend is running."""
    return {"status": "ok"}


@app.get("/api/claims", operation_id="list_claims")
def list_claims() -> list[ClaimSummary]:
    """List every claim in the queue with where it stands."""
    with db.connect() as conn:
        rows = conn.execute(
            """SELECT c.status, c.data, json_extract(u.data, '$.name') AS customer_name
            FROM claims c
            JOIN customers u ON u.customer_id = json_extract(c.data, '$.customer_id')
            ORDER BY c.claim_id"""
        ).fetchall()
    return [
        ClaimSummary.model_validate(
            {
                **json.loads(row["data"]),
                "status": row["status"],
                "customer_name": row["customer_name"],
            }
        )
        for row in rows
    ]


@app.get("/api/claims/{claim_id}", operation_id="get_claim")
def get_claim(claim_id: str) -> Claim:
    """Get a claim in full: the story, the items, the documents and its status."""
    with db.connect() as conn:
        return Claim.model_validate(claim_record(conn, claim_id))


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
    with db.connect() as conn:
        return Customer.model_validate(
            record(
                conn,
                "SELECT data FROM customers WHERE customer_id = ?",
                customer_id,
                "Customer",
            )
        )


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
