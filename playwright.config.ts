import { tmpdir } from "node:os";
import { join } from "node:path";
import { defineConfig } from "@playwright/test";

// The end-to-end tests run on their own ports with a freshly seeded database of
// their own, so they never touch the development data and can run beside npm run dev.
const database = join(tmpdir(), "undercover-e2e.db");

export default defineConfig({
  testDir: "e2e",
  outputDir: "e2e/test-results",
  reporter: "list",
  use: { baseURL: "http://localhost:5174" },
  projects: [
    { name: "queue", testMatch: "queue.spec.ts" },
    { name: "claims", testIgnore: "queue.spec.ts", dependencies: ["queue"] },
  ],
  webServer: [
    {
      command:
        "uv run -m backend.db && uv run -m uvicorn backend.main:app --port 8001",
      url: "http://127.0.0.1:8001/api/health",
      env: { UNDERCOVER_DB: database },
      reuseExistingServer: false,
    },
    {
      command: "npx vite dashboard --port 5174 --strictPort",
      url: "http://localhost:5174",
      env: { UNDERCOVER_API: "http://127.0.0.1:8001" },
      reuseExistingServer: false,
    },
  ],
});
