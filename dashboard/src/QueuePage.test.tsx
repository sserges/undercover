import { act, cleanup, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { ClaimSummary } from "./api";
import { renderAt, stubApi } from "./testing";

const claims: ClaimSummary[] = [
  {
    claim_id: "CLM-1001",
    customer_name: "Maya Patel",
    claim_type: "trip_delay",
    summary: "Flight home canceled",
    amount_claimed: 420,
    submitted_on: "2026-06-24",
    status: "decided",
    decision: "approve",
    payout: 420,
  },
  {
    claim_id: "CLM-1002",
    customer_name: "Tom Becker",
    claim_type: "baggage",
    summary: "Suitcase lost on a connecting flight",
    amount_claimed: 1150,
    submitted_on: "2026-07-20",
    status: "waiting",
    decision: null,
    payout: null,
  },
  {
    claim_id: "CLM-1003",
    customer_name: "Aiko Tanaka",
    claim_type: "emergency_medical",
    summary: "Fractured wrist",
    amount_claimed: 3800,
    submitted_on: "2026-07-06",
    status: "waiting_for_sign_off",
    decision: "approve",
    payout: 3000,
  },
  {
    claim_id: "CLM-1004",
    customer_name: "Lena Ortiz",
    claim_type: "baggage_delay",
    summary: "Bag arrived late",
    amount_claimed: 186,
    submitted_on: "2026-07-02",
    status: "decided",
    decision: "decline",
    payout: 0,
  },
];

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

it("shows each claim with its customer, type, amounts and status", async () => {
  stubApi({ "GET /api/claims": claims });
  renderAt("/");
  const row = await screen.findByRole("row", { name: /CLM-1002/ });
  for (const text of [
    "Tom Becker",
    "Baggage",
    "Suitcase lost on a connecting flight",
    "$1,150.00",
    "Jul 20, 2026",
    "Waiting",
  ]) {
    expect(within(row).getByText(text)).toBeDefined();
  }
  expect(within(row).getByRole("link").getAttribute("href")).toBe(
    "/claims/CLM-1002",
  );
});

it("shows the decision, with the payout of an approval", async () => {
  stubApi({ "GET /api/claims": claims });
  renderAt("/");
  const approved = await screen.findByRole("row", { name: /CLM-1003/ });
  expect(within(approved).getByText("Approve")).toBeDefined();
  expect(within(approved).getByText("$3,000.00")).toBeDefined();
  const declined = screen.getByRole("row", { name: /CLM-1004/ });
  expect(within(declined).getByText("Decline")).toBeDefined();
  expect(within(declined).queryByText("$0.00")).toBeNull();
});

it("counts the claims in each status", async () => {
  stubApi({ "GET /api/claims": claims });
  renderAt("/");
  const tiles = await screen.findByRole("list", { name: "Claims by status" });
  expect(
    within(tiles)
      .getAllByRole("listitem")
      .map((tile) => tile.textContent),
  ).toEqual([
    "1 Waiting",
    "0 In progress",
    "1 Waiting for sign-off",
    "2 Decided",
  ]);
});

it("refreshes the queue every two seconds", async () => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  const fetchMock = stubApi({ "GET /api/claims": claims });
  renderAt("/");
  await screen.findByRole("row", { name: /CLM-1001/ });
  await act(() => vi.advanceTimersByTimeAsync(2000));
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

it("says when the backend isn't responding", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  renderAt("/");
  expect(
    await screen.findByText("The backend isn't responding."),
  ).toBeDefined();
});
