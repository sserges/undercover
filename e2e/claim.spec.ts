import { expect, test } from "@playwright/test";
import { actAsAgent } from "./agent";

test("a claim page shows the claim in full", async ({ page }) => {
  await page.goto("/claims/CLM-1001");
  await expect(page.getByRole("heading", { name: "CLM-1001" })).toBeVisible();
  const claim = page.getByRole("region", { name: "The claim" });
  await expect(claim).toContainText("My flight home from Rome on June 18");
  await expect(claim.getByRole("table").getByRole("row")).toHaveCount(4);
  await expect(claim.getByRole("listitem")).toHaveCount(4);
  await expect(page.getByRole("region", { name: "Policy" })).toContainText(
    "UnderCover Premium",
  );
  const customer = page.getByRole("region", { name: "Customer" });
  await expect(customer).toContainText("Maya Patel");
  await expect(customer).toContainText("CLM-0412");
});

test("a claim page shows the agent's steps and decision", async ({
  page,
  request,
}) => {
  const agent = actAsAgent(request, "CLM-1002");
  await agent.start();
  await agent.step("tool_call", 'get_claim(claim_id="CLM-1002")');
  await agent.step("message", "The carrier report is there.");
  await agent.decide(
    "decline",
    0,
    "The airline already paid more than the covered items.",
    "5. Baggage and Personal Effects",
  );
  await page.goto("/claims/CLM-1002");
  const steps = page.getByRole("region", { name: "The agent's steps" });
  await expect(steps.getByRole("listitem")).toHaveText([
    'get_claim(claim_id="CLM-1002")',
    "The carrier report is there.",
  ]);
  const decision = page.getByRole("region", { name: "Decision" });
  await expect(decision).toContainText("Decline");
  await expect(decision).toContainText(
    "The airline already paid more than the covered items.",
  );
  await expect(decision).toContainText(
    "Section 5. Baggage and Personal Effects",
  );
  await expect(page.locator(".claim-title")).toContainText("Decided");
});

test("a step appears on the claim page as the agent takes it", async ({
  page,
  request,
}) => {
  const agent = actAsAgent(request, "CLM-1004");
  await agent.start();
  await page.goto("/claims/CLM-1004");
  await expect(page.getByText("No steps yet.")).toBeVisible();
  await agent.step("tool_call", 'get_policy(policy_id="POL-2004")');
  await expect(
    page.getByRole("region", { name: "The agent's steps" }),
  ).toContainText('get_policy(policy_id="POL-2004")');
});
