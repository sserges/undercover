"""The UnderCover Agent."""

import json
import os
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

load_dotenv(override=True)

BACKEND_URL = "http://127.0.0.1:8000"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-6-luna"


def backend() -> httpx.Client:
    """Return a client for the UnderCover backend."""
    return httpx.Client(base_url=BACKEND_URL, timeout=30)


def request(
    method: str, path: str, body: dict[str, Any] | None = None
) -> httpx.Response:
    with backend() as client:
        return client.request(method, path, json=body)


def api(method: str, path: str, body: dict[str, Any] | None = None) -> Any:
    """Call the backend and return its reply, raising an error if it refuses."""
    response = request(method, path, body)
    response.raise_for_status()
    return response.json()


def ask(method: str, path: str, body: dict[str, Any] | None = None) -> str:
    """Call the backend for a tool: its reply, or its reason when it refuses."""
    response = request(method, path, body)
    if response.is_error:
        return f"Refused ({response.status_code}): {response.json()['detail']}"
    return response.text


@tool
def get_claim(claim_id: str) -> str:
    """Get a claim: the customer's story, the items claimed and the documents."""
    return ask("GET", f"/api/claims/{claim_id}")


@tool
def get_policy(policy_id: str) -> str:
    """Get a policy: its plan and limits, add-ons, purchase date, trip and travelers."""
    return ask("GET", f"/api/policies/{policy_id}")


@tool
def get_customer(customer_id: str) -> str:
    """Get a customer and their claim history."""
    return ask("GET", f"/api/customers/{customer_id}")


@tool
def get_policy_wording() -> str:
    """Get the policy wording, which every decision follows."""
    return ask("GET", "/api/policy-wording")


@tool
def decide_claim(
    claim_id: str,
    decision: Literal["approve", "decline", "refer"],
    payout: float,
    reasons: str,
    policy_section: str,
) -> str:
    """Record the decision on a claim, with its payout, reasons and policy section."""
    body = {
        "decision": decision,
        "payout": payout,
        "reasons": reasons,
        "policy_section": policy_section,
    }
    return ask("POST", f"/api/claims/{claim_id}/decision", body)


@tool
def pay_claim(claim_id: str, amount: float) -> str:
    """Pay an approved claim its payout."""
    return ask("POST", f"/api/claims/{claim_id}/payment", {"amount": amount})


TOOLS = [
    get_claim,
    get_policy,
    get_customer,
    get_policy_wording,
    decide_claim,
    pay_claim,
]


def model() -> ChatOpenAI:
    """Return the model named in MODEL_NAME, or GPT-6 Luna by default."""
    name = os.getenv("MODEL_NAME")
    return ChatOpenAI(
        model=name or DEFAULT_MODEL,
        base_url=OPENROUTER_BASE_URL,
        api_key=SecretStr(os.environ["OPENROUTER_API_KEY"]),
        reasoning_effort=None if name else "low",
    )


def steps(message: BaseMessage) -> list[tuple[str, str]]:
    """Turn a message from the agent's run into the steps the dashboard shows."""
    if isinstance(message, ToolMessage):
        return [("tool_result", message.text)]
    found: list[tuple[str, str]] = [("message", message.text)] if message.text else []
    if isinstance(message, AIMessage):
        for call in message.tool_calls:
            args = ", ".join(f"{k}={json.dumps(v)}" for k, v in call["args"].items())
            found.append(("tool_call", f"{call['name']}({args})"))
    return found


def run(claim_id: str, thread_id: str, llm: BaseChatModel | None = None) -> str:
    """Run the agent on one claim, recording each step, and return its final reply."""
    api("POST", f"/api/claims/{claim_id}/start")
    instructions = api("GET", "/api/instructions")["text"]
    agent = create_agent(llm or model(), tools=TOOLS, system_prompt=instructions)
    stream = agent.stream(
        {"messages": [{"role": "user", "content": f"Please decide claim {claim_id}."}]},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode="updates",
    )
    messages = (
        m for update in stream for node in update.values() for m in node["messages"]
    )
    reply = ""
    for message in messages:
        for kind, text in steps(message):
            step = {"thread_id": thread_id, "kind": kind, "text": text}
            api("POST", f"/api/claims/{claim_id}/steps", step)
        reply = message.text
    return reply
