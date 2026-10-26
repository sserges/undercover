import { cleanup, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { renderAt, stubApi } from "./testing";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("links to the queue and the instructions", () => {
  stubApi({ "GET /api/claims": [] });
  renderAt("/");
  const nav = screen.getByRole("navigation", { name: "Main" });
  expect(nav.textContent).toBe("QueueInstructions");
  expect(screen.getByRole("link", { name: "Queue" }).className).toBe("active");
});

it("says when a page doesn't exist", () => {
  renderAt("/nowhere");
  expect(screen.getByText("Page not found.")).toBeDefined();
});
