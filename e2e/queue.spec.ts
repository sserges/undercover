import { expect, test } from "@playwright/test";

// These run first, on the freshly seeded queue, before the other tests change it.

test("the queue shows all 25 claims waiting", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("row")).toHaveCount(26);
  const tiles = page
    .getByRole("list", { name: "Claims by status" })
    .getByRole("listitem");
  await expect(tiles).toHaveText([
    "25 Waiting",
    "0 In progress",
    "0 Waiting for sign-off",
    "0 Decided",
  ]);
});

test("the queue shows a claim in progress without a reload", async ({
  page,
  request,
}) => {
  await page.goto("/");
  const row = page.getByRole("row", { name: /CLM-1025/ });
  await expect(row).toContainText("Waiting");
  expect((await request.post("/api/claims/CLM-1025/start")).ok()).toBe(true);
  await expect(row).toContainText("In progress");
});
