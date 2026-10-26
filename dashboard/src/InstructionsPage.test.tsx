import { cleanup, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { renderAt, stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("shows the agent's instructions, read only", async () => {
  stubApi({
    "GET /api/instructions": {
      text: "# The UnderCover Agent\n\nDecide claims.",
    },
  });
  renderAt("/instructions");
  expect(await screen.findByText(/Decide claims\./)).toBeDefined();
  expect(screen.queryByRole("textbox")).toBeNull();
  expect(screen.queryByRole("button")).toBeNull();
  expect(screen.getByRole("link", { name: "Instructions" }).className).toBe(
    "active",
  );
});
