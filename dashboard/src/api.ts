export type Status =
  "waiting" | "in_progress" | "waiting_for_sign_off" | "decided";

export type DecisionKind = "approve" | "decline" | "refer";

export type StepKind = "message" | "tool_call" | "tool_result";

export interface ClaimSummary {
  claim_id: string;
  customer_name: string;
  claim_type: string;
  summary: string;
  amount_claimed: number;
  submitted_on: string;
  status: Status;
  decision: DecisionKind | null;
  payout: number | null;
}

export interface Item {
  description: string;
  category: string;
  amount: number;
}

export interface Document {
  name: string;
  type: string;
  content: string;
}

export interface Decision {
  decision: DecisionKind;
  payout: number;
  reasons: string;
  policy_section: string;
  decided_at: string;
}

export interface Payment {
  amount: number;
  paid_at: string;
}

export interface SignOff {
  handler_id: string;
  handler_name: string;
  signed_off_at: string;
}

export interface Claim {
  claim_id: string;
  policy_id: string;
  customer_id: string;
  claim_type: string;
  submitted_on: string;
  incident_date: string;
  incident_location: string;
  summary: string;
  story: string;
  items: Item[];
  amount_claimed: number;
  documents: Document[];
  status: Status;
  decision: Decision | null;
  payment: Payment | null;
  sign_off: SignOff | null;
}

export interface Policy {
  policy_id: string;
  plan: string;
  plan_details: { name: string; deductible: number; per_item_limit: number };
  add_ons: string[];
  purchased_on: string;
  trip: {
    destination: string;
    departs_on: string;
    returns_on: string;
    trip_cost: number;
  };
  travelers: string[];
}

export interface PreviousClaim {
  claim_id: string;
  filed_on: string;
  claim_type: string;
  summary: string;
  outcome: string;
  amount_paid: number;
}

export interface Customer {
  customer_id: string;
  name: string;
  customer_since: string;
  previous_claims: PreviousClaim[];
}

export interface Handler {
  handler_id: string;
  name: string;
  role: string;
}

export interface Step {
  step_id: number;
  thread_id: string;
  kind: StepKind;
  text: string;
  created_at: string;
}

export interface Instructions {
  text: string;
}

/** Call the backend and return its reply, or throw its explanation. */
async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  const body = (await response.json()) as T | { detail: string };
  if (!response.ok) throw new Error((body as { detail: string }).detail);
  return body as T;
}

export const fetchClaims = () => call<ClaimSummary[]>("/api/claims");
export const fetchClaim = (id: string) => call<Claim>(`/api/claims/${id}`);
export const fetchSteps = (id: string) =>
  call<Step[]>(`/api/claims/${id}/steps`);
export const fetchPolicy = (id: string) => call<Policy>(`/api/policies/${id}`);
export const fetchCustomer = (id: string) =>
  call<Customer>(`/api/customers/${id}`);
export const fetchHandlers = () => call<Handler[]>("/api/handlers");
export const fetchInstructions = () => call<Instructions>("/api/instructions");

export const signOff = (claimId: string, handlerId: string) =>
  call<Claim>(`/api/claims/${claimId}/sign-off`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ handler_id: handlerId }),
  });
