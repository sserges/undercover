import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { vi } from "vitest";
import { App } from "./App";

/** Stub fetch so that each "METHOD /path" returns its JSON, and anything else a 404. */
export function stubApi(routes: Record<string, unknown>) {
  const fetchMock = vi.fn((path: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${path}`;
    const found = key in routes;
    const body = found ? routes[key] : { detail: `No stub for ${key}` };
    return Promise.resolve(
      new Response(JSON.stringify(body), { status: found ? 200 : 404 }),
    );
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

export function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}
