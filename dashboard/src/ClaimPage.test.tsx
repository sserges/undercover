import {
  cleanup,
  fireEvent,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Claim, Customer, Decision, Handler, Policy, Step } from "./api";
import { renderAt, stubApi } from "./testing";

const claim: Claim = {
  claim_id: "CLM-1001",
  policy_id: "POL-2001",
  customer_id: "CUS-3001",
  claim_type: "trip_delay",
  submitted_on: "2026-06-24",
  incident_date: "2026-06-18",
  incident_location: "Rome, Italy",
  summary: "Flight home canceled by the airline",
  story: "My flight home from Rome on June 18 was canceled.",
  items: [
    {
      description: "Airport hotel, one night",
      category: "accommodation",
      amount: 245,
    },
    { description: "Dinner and breakfast", category: "meals", amount: 95 },
  ],
  amount_claimed: 340,
  documents: [
    {
      name: "Meridian Air cancellation notice",
      type: "carrier_report",
      content: "Flight MA 611 was canceled because of crew availability.",
    },
  ],
  status: "waiting",
  decision: null,
  payment: null,
  sign_off: null,
};

const approval: Decision = {
  decision: "approve",
  payout: 340,
  reasons: "The airline canceled the flight for a crew problem.",
  policy_section: "3. Trip Delay",
  decided_at: "2026-10-26T19:37:37+00:00",
};

const decided: Claim = {
  ...claim,
  status: "decided",
  decision: approval,
  payment: { amount: 340, paid_at: "2026-10-26T19:37:45+00:00" },
};

const held: Claim = {
  ...claim,
  status: "waiting_for_sign_off",
  decision: { ...approval, payout: 3000 },
};

const policy: Policy = {
  policy_id: "POL-2001",
  plan: "premium",
  plan_details: {
    name: "UnderCover Premium",
    deductible: 50,
    per_item_limit: 300,
  },
  add_ons: ["electronics_plus"],
  purchased_on: "2026-04-22",
  trip: {
    destination: "Rome, Italy",
    departs_on: "2026-06-10",
    returns_on: "2026-06-18",
    trip_cost: 3100,
  },
  travelers: ["Maya Patel"],
};

const customer: Customer = {
  customer_id: "CUS-3001",
  name: "Maya Patel",
  customer_since: "2023-04-11",
  previous_claims: [
    {
      claim_id: "CLM-0412",
      filed_on: "2024-08-19",
      claim_type: "baggage_delay",
      summary: "Checked bag arrived 30 hours late in Lisbon",
      outcome: "approved",
      amount_paid: 140,
    },
  ],
};

const handlers: Handler[] = [
  {
    handler_id: "HND-01",
    name: "Dana Whitfield",
    role: "Senior Claims Handler",
  },
  { handler_id: "HND-02", name: "Marcus Oyelaran", role: "Claims Handler" },
];

const steps: Step[] = [
  { kind: "tool_call", text: 'get_claim(claim_id="CLM-1001")' },
  { kind: "tool_result", text: '{"claim_id":"CLM-1001"}' },
  { kind: "tool_result", text: "Refused (403): The payout is held." },
  { kind: "message", text: "Approved and paid $340.00." },
].map((step, i) => ({
  ...step,
  step_id: i + 1,
  thread_id: "thread-1",
  created_at: "2026-10-26T19:37:10+00:00",
})) as Step[];

function stubClaim(
  current: Claim,
  recorded: Step[] = [],
  more: Record<string, unknown> = {},
) {
  return stubApi({
    ...more,
    "GET /api/claims/CLM-1001": current,
    "GET /api/claims/CLM-1001/steps": recorded,
    "GET /api/policies/POL-2001": policy,
    "GET /api/customers/CUS-3001": customer,
    "GET /api/handlers": handlers,
  });
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows the claim in full", async () => {
  stubClaim(claim);
  renderAt("/claims/CLM-1001");
  expect(
    await screen.findByRole("heading", { name: "CLM-1001" }),
  ).toBeDefined();
  const details = screen.getByRole("region", { name: "The claim" });
  expect(within(details).getByText(claim.story)).toBeDefined();
  expect(within(details).getByText("Airport hotel, one night")).toBeDefined();
  expect(within(details).getByText("$245.00")).toBeDefined();
  expect(
    within(details).getByText("Meridian Air cancellation notice"),
  ).toBeDefined();
  expect(
    within(details).getByText("Incident on Jun 18, 2026 in Rome, Italy."),
  ).toBeDefined();
});

it("shows the policy and the customer's earlier claims", async () => {
  stubClaim(claim);
  renderAt("/claims/CLM-1001");
  const policyPanel = await screen.findByRole("region", { name: "Policy" });
  expect(within(policyPanel).getByText("UnderCover Premium")).toBeDefined();
  expect(within(policyPanel).getByText("Electronics plus")).toBeDefined();
  expect(within(policyPanel).getByText("$3,100.00")).toBeDefined();
  const customerPanel = await screen.findByRole("region", { name: "Customer" });
  expect(within(customerPanel).getByText("CLM-0412")).toBeDefined();
});

it("says when the agent hasn't decided or taken any steps", async () => {
  stubClaim(claim);
  renderAt("/claims/CLM-1001");
  expect(
    await screen.findByText("The agent hasn't decided this claim yet."),
  ).toBeDefined();
  expect(await screen.findByText("No steps yet.")).toBeDefined();
});

it("shows the decision, its reasons, its section and the payment", async () => {
  stubClaim(decided);
  renderAt("/claims/CLM-1001");
  const panel = await screen.findByRole("region", { name: "Decision" });
  expect(within(panel).getByText("Approve")).toBeDefined();
  expect(within(panel).getAllByText("$340.00")).toHaveLength(2);
  expect(within(panel).getByText("Section 3. Trip Delay")).toBeDefined();
  expect(within(panel).getByText(approval.reasons)).toBeDefined();
  expect(within(panel).getByText(/^Paid/)).toBeDefined();
  expect(within(panel).queryByRole("button")).toBeNull();
});

it("shows the agent's steps, with refusals in plain sight", async () => {
  stubClaim(decided, steps);
  renderAt("/claims/CLM-1001");
  const panel = await screen.findByRole("region", {
    name: "The agent's steps",
  });
  expect(
    await within(panel).findByText('get_claim(claim_id="CLM-1001")'),
  ).toBeDefined();
  expect(within(panel).getByText("Result")).toBeDefined();
  expect(
    within(panel).getAllByText("Refused (403): The payout is held."),
  ).toHaveLength(2);
  expect(within(panel).getByText("Approved and paid $340.00.")).toBeDefined();
});

async function chooseHandler(name: string) {
  const option = await screen.findByRole("option", { name });
  fireEvent.change(screen.getByRole("combobox", { name: "Handler" }), {
    target: { value: (option as HTMLOptionElement).value },
  });
}

it("signs off a payout over the limit as the handler chosen", async () => {
  const fetchMock = stubClaim(held, [], {
    "POST /api/claims/CLM-1001/sign-off": decided,
  });
  renderAt("/claims/CLM-1001");
  const button = await screen.findByRole("button", {
    name: "Sign off and pay",
  });
  expect((button as HTMLButtonElement).disabled).toBe(true);
  await chooseHandler("Dana Whitfield");
  fireEvent.click(button);
  await waitFor(() => {
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });
  const call = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
  expect(call?.[0]).toBe("/api/claims/CLM-1001/sign-off");
  expect(call?.[1]?.body).toBe('{"handler_id":"HND-01"}');
  expect(screen.queryByRole("alert")).toBeNull();
});

it("shows why a sign-off was refused", async () => {
  stubClaim(held);
  renderAt("/claims/CLM-1001");
  await chooseHandler("Marcus Oyelaran");
  fireEvent.click(screen.getByRole("button", { name: "Sign off and pay" }));
  expect((await screen.findByRole("alert")).textContent).toBe(
    "No stub for POST /api/claims/CLM-1001/sign-off",
  );
});

it("says when a claim doesn't exist", async () => {
  stubApi({});
  renderAt("/claims/CLM-9999");
  expect(await screen.findByText("Claim CLM-9999 wasn't found.")).toBeDefined();
});
