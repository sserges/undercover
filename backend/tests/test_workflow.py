def start(client, claim_id="CLM-1001"):
    return client.post(f"/api/claims/{claim_id}/start")


def decide(client, decision, payout, claim_id="CLM-1001"):
    return client.post(
        f"/api/claims/{claim_id}/decision",
        json={
            "decision": decision,
            "payout": payout,
            "reasons": "The reasons for the decision.",
            "policy_section": "3. Trip Delay",
        },
    )


def pay(client, amount, claim_id="CLM-1001"):
    return client.post(f"/api/claims/{claim_id}/payment", json={"amount": amount})


def sign_off(client, handler_id="HND-01", claim_id="CLM-1001"):
    return client.post(
        f"/api/claims/{claim_id}/sign-off", json={"handler_id": handler_id}
    )


def add_step(client, text, claim_id="CLM-1001"):
    return client.post(
        f"/api/claims/{claim_id}/steps",
        json={"thread_id": "thread-1", "kind": "message", "text": text},
    )


def status(client, claim_id="CLM-1001"):
    return client.get(f"/api/claims/{claim_id}").json()["status"]


def test_a_new_claim_has_no_decision_payment_or_sign_off(client):
    claim = client.get("/api/claims/CLM-1001").json()
    assert (claim["decision"], claim["payment"], claim["sign_off"]) == (
        None,
        None,
        None,
    )


def test_start_a_waiting_claim(client):
    response = start(client)
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_start_again_clears_the_earlier_steps(client):
    start(client)
    add_step(client, "First run")
    start(client)
    assert client.get("/api/claims/CLM-1001/steps").json() == []
    assert status(client) == "in_progress"


def test_start_a_decided_claim_is_refused(client):
    start(client)
    decide(client, "decline", 0)
    response = start(client)
    assert response.status_code == 409
    assert response.json()["detail"] == "Claim CLM-1001 is already decided."


def test_start_a_claim_waiting_for_sign_off_is_refused(client):
    start(client)
    decide(client, "approve", 3000)
    assert start(client).status_code == 409


def test_decide_a_claim_that_has_not_started_is_refused(client):
    response = decide(client, "decline", 0)
    assert response.status_code == 409
    assert "Only a claim in progress can be decided" in response.json()["detail"]


def test_decide_twice_is_refused(client):
    start(client)
    decide(client, "decline", 0)
    assert decide(client, "refer", 0).status_code == 409


def test_decline(client):
    start(client)
    claim = decide(client, "decline", 0).json()
    assert claim["status"] == "decided"
    assert claim["decision"]["decision"] == "decline"
    assert claim["decision"]["reasons"] == "The reasons for the decision."
    assert claim["decision"]["policy_section"] == "3. Trip Delay"


def test_refer(client):
    start(client)
    assert decide(client, "refer", 0).json()["status"] == "decided"


def test_payout_must_match_the_decision(client):
    start(client)
    for decision, payout in [("decline", 50), ("refer", -5), ("approve", 0)]:
        response = decide(client, decision, payout)
        assert response.status_code == 422, (decision, payout)
    assert status(client) == "in_progress"


def test_approve_and_pay(client):
    start(client)
    assert decide(client, "approve", 420).json()["status"] == "decided"
    response = pay(client, 420)
    assert response.status_code == 200
    assert response.json()["payment"]["amount"] == 420.0


def test_pay_twice_is_refused(client):
    start(client)
    decide(client, "approve", 420)
    pay(client, 420)
    response = pay(client, 420)
    assert response.status_code == 409
    assert response.json()["detail"] == "Claim CLM-1001 has already been paid."


def test_pay_the_wrong_amount_is_refused(client):
    start(client)
    decide(client, "approve", 420)
    response = pay(client, 400)
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "The payment must be the approved payout of $420.00."
    )
    assert client.get("/api/claims/CLM-1001").json()["payment"] is None


def test_a_payout_of_exactly_the_limit_goes_straight_through(client):
    start(client)
    assert decide(client, "approve", 1000).json()["status"] == "decided"
    assert pay(client, 1000).status_code == 200


def test_a_payout_over_the_limit_waits_for_sign_off(client):
    start(client)
    assert decide(client, "approve", 3000).json()["status"] == "waiting_for_sign_off"
    for amount in [3000, 900]:
        response = pay(client, amount)
        assert response.status_code == 403
        assert "a handler must sign off" in response.json()["detail"]
    assert client.get("/api/claims/CLM-1001").json()["payment"] is None


def test_sign_off_pays_the_held_payout(client):
    start(client)
    decide(client, "approve", 3000)
    claim = sign_off(client).json()
    assert claim["status"] == "decided"
    assert claim["payment"]["amount"] == 3000.0
    assert claim["sign_off"]["handler_id"] == "HND-01"
    assert claim["sign_off"]["handler_name"] == "Dana Whitfield"
    assert claim["sign_off"]["signed_off_at"]
    assert pay(client, 3000).status_code == 409


def test_sign_off_by_an_unknown_handler_is_refused(client):
    start(client)
    decide(client, "approve", 3000)
    response = sign_off(client, "HND-99")
    assert response.status_code == 404
    assert response.json()["detail"] == "Handler HND-99 was not found."


def test_sign_off_a_claim_not_waiting_for_sign_off_is_refused(client):
    start(client)
    decide(client, "approve", 420)
    response = sign_off(client)
    assert response.status_code == 409
    assert response.json()["detail"] == "Claim CLM-1001 is not waiting for sign-off."


def test_pay_a_declined_claim_is_refused(client):
    start(client)
    decide(client, "decline", 0)
    response = pay(client, 100)
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Claim CLM-1001 is not approved, so there is nothing to pay."
    )


def test_steps_are_listed_in_order(client):
    start(client)
    for text in ["Read the claim", "Read the policy", "Decided"]:
        assert add_step(client, text).status_code == 200
    steps = client.get("/api/claims/CLM-1001/steps").json()
    assert [s["text"] for s in steps] == [
        "Read the claim",
        "Read the policy",
        "Decided",
    ]
    assert {s["thread_id"] for s in steps} == {"thread-1"}
    assert {s["kind"] for s in steps} == {"message"}
    assert all(s["created_at"] for s in steps)


def test_steps_on_an_unknown_claim_are_not_found(client):
    assert add_step(client, "Hello", "CLM-9999").status_code == 404
    assert client.get("/api/claims/CLM-9999/steps").status_code == 404


def test_the_queue_shows_decisions(client):
    start(client)
    decide(client, "approve", 420)
    first = client.get("/api/claims").json()[0]
    assert (first["status"], first["decision"], first["payout"]) == (
        "decided",
        "approve",
        420.0,
    )
