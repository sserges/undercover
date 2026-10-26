export type Status =
  "waiting" | "in_progress" | "waiting_for_sign_off" | "decided";

export type DecisionKind = "approve" | "decline" | "refer";

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

async function get<T>(path: string): Promise<T> {
  const response = await fetch(path);
  if (!response.ok)
    throw new Error(`${path} returned ${String(response.status)}`);
  return (await response.json()) as T;
}

export const fetchClaims = () => get<ClaimSummary[]>("/api/claims");
