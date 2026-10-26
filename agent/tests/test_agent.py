from pathlib import Path

from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, BaseMessage

from agent import main
from agent.__main__ import main as work_queue
from backend.main import app

INSTRUCTIONS = Path("backend/instructions.md").read_text(encoding="utf-8")


class StubModel(GenericFakeChatModel):
    """A chat model that gives scripted replies and keeps the prompts it was sent."""

    prompts: list[list[BaseMessage]] = []

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.prompts.append(messages)
        return super()._generate(messages, stop, run_manager, **kwargs)


def calls(*tool_calls, text=""):
    """A scripted reply that calls tools, each given as (name, args)."""
    return AIMessage(
        content=text,
        tool_calls=[
            {"name": name, "args": args, "id": str(i)}
            for i, (name, args) in enumerate(tool_calls)
        ],
    )


def decision(payout):
    return {
        "claim_id": "CLM-1001",
        "decision": "approve",
        "payout": payout,
        "reasons": "The flight was canceled for a crew problem. Covered.",
        "policy_section": "3. Trip Delay",
    }


def stub(*replies):
    return StubModel(messages=iter(replies))


def claim(claim_id="CLM-1001"):
    return TestClient(app).get(f"/api/claims/{claim_id}").json()


def steps(claim_id="CLM-1001"):
    return TestClient(app).get(f"/api/claims/{claim_id}/steps").json()


def test_run_reads_decides_and_pays():
    model = stub(
        calls(("get_claim", {"claim_id": "CLM-1001"})),
        calls(
            ("get_policy", {"policy_id": "POL-2001"}),
            ("get_customer", {"customer_id": "CUS-3001"}),
        ),
        calls(("get_policy_wording", {})),
        calls(("decide_claim", decision(420)), text="Covered under section 3."),
        calls(("pay_claim", {"claim_id": "CLM-1001", "amount": 420})),
        AIMessage(content="Approved and paid $420.00."),
    )
    assert main.run("CLM-1001", "thread-1", model) == "Approved and paid $420.00."
    assert claim()["status"] == "decided"
    assert claim()["payment"]["amount"] == 420.0
    recorded = steps()
    call, result, message = "tool_call", "tool_result", "message"
    assert [s["kind"] for s in recorded] == [
        *(call, result),
        *(call, call, result, result),
        *(call, result),
        *(message, call, result),
        *(call, result),
        message,
    ]
    assert [s["text"].split("(")[0] for s in recorded if s["kind"] == call] == [
        "get_claim",
        "get_policy",
        "get_customer",
        "get_policy_wording",
        "decide_claim",
        "pay_claim",
    ]
    assert recorded[0]["text"] == 'get_claim(claim_id="CLM-1001")'
    assert recorded[8]["text"] == "Covered under section 3."
    assert recorded[-1]["text"] == "Approved and paid $420.00."
    assert '"story":"My flight home from Rome' in recorded[1]["text"]
    results = [s["text"] for s in recorded if s["kind"] == result]
    assert any('"name":"Maya Patel","email"' in text for text in results)
    assert {s["thread_id"] for s in recorded} == {"thread-1"}


def test_a_payout_over_the_limit_is_held_for_sign_off():
    model = stub(
        calls(("decide_claim", decision(3000))),
        calls(("pay_claim", {"claim_id": "CLM-1001", "amount": 3000})),
        AIMessage(content="Approved $3,000.00, waiting for sign-off."),
    )
    main.run("CLM-1001", "thread-1", model)
    assert claim()["status"] == "waiting_for_sign_off"
    assert claim()["payment"] is None
    refusal = steps()[-2]["text"]
    assert refusal.startswith("Refused (403): The payout of $3,000.00 is over")


def test_the_model_is_given_the_instructions_from_the_backend():
    model = stub(AIMessage(content="Nothing to do."))
    main.run("CLM-1001", "thread-1", model)
    system, user = model.prompts[0]
    assert system.content == INSTRUCTIONS
    assert user.content == "Please decide claim CLM-1001."


def test_work_the_whole_queue(monkeypatch, capsys):
    client = TestClient(app)
    client.post("/api/claims/CLM-1002/start")
    client.post(
        "/api/claims/CLM-1002/decision",
        json={**decision(0), "decision": "decline"},
    )
    client.post("/api/claims/CLM-1003/start")
    ran = []
    monkeypatch.setattr(
        "agent.__main__.run", lambda claim_id, thread_id: ran.append(claim_id) or "Done"
    )
    work_queue([])
    assert len(ran) == 24
    assert "CLM-1002" not in ran
    assert "CLM-1003" in ran
    assert "CLM-1001: Done" in capsys.readouterr().out


def test_work_the_claims_named(monkeypatch):
    ran = []
    monkeypatch.setattr(
        "agent.__main__.run", lambda claim_id, thread_id: ran.append(claim_id) or "Done"
    )
    work_queue(["CLM-1003", "CLM-1005"])
    assert ran == ["CLM-1003", "CLM-1005"]


def test_model_name(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    assert main.model().model_name == "openai/gpt-6-luna"
    assert main.model().reasoning_effort == "low"
    assert main.model().rate_limiter is main.RATE_LIMITER
    monkeypatch.setenv("MODEL_NAME", "openrouter/free")
    assert main.model().model_name == "openrouter/free"
    assert main.model().reasoning_effort is None
