import { expect, test } from "@playwright/test";
import { actAsAgent } from "./agent";

test("a payout over $1,000 waits for a handler's sign-off", async ({
  page,
  request,
}) => {
  const agent = actAsAgent(request, "CLM-1003");
  await agent.start();
  await agent.decide(
    "approve",
    3000,
    "The fall abroad is covered.",
    "7. Emergency Medical",
  );
  const payment = await agent.pay(3000);
  expect(payment.status()).toBe(403);

  await page.goto("/claims/CLM-1003");
  await expect(page.locator(".claim-title")).toContainText(
    "Waiting for sign-off",
  );
  await page
    .getByRole("combobox", { name: "Handler" })
    .selectOption({ label: "Dana Whitfield" });
  await page.getByRole("button", { name: "Sign off and pay" }).click();

  await expect(page.locator(".claim-title")).toContainText("Decided");
  const decision = page.getByRole("region", { name: "Decision" });
  await expect(decision).toContainText("Paid $3,000.00");
  await expect(decision).toContainText("Signed off by Dana Whitfield");
  await expect(
    page.getByRole("button", { name: "Sign off and pay" }),
  ).toHaveCount(0);
});
