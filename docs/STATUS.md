# Status

The pilot is built: all six phases of `docs/PLAN.md` are done.

## What's built

- `backend/`: FastAPI on SQLite.
  - The database is `backend/undercover.db`, or the file named in `UNDERCOVER_DB`. The backend creates it on its first start and seeds it from `data/`. It never reads `data/evals/`.
  - Read operations: `list_claims`, `get_claim`, `get_policy`, `get_customer`, `list_handlers`, `get_policy_wording`, `get_instructions`, and `health`.
  - Work on a claim: `start_claim`, `add_step`, `list_steps`, `decide_claim`, `pay_claim` and `sign_off_claim`.
  - A claim moves from `waiting` to `in_progress`, then to `decided`, or to `waiting_for_sign_off` when the agent approves a payout over $1,000. `pay_claim` refuses such a payout with 403 until a handler signs off, and the sign-off makes the payment.
  - `backend/instructions.md` holds the agent's instructions. They're read only and served by `get_instructions`.
- `agent/`: the UnderCover Agent, built with LangChain's `create_agent` on OpenRouter.
  - `run(claim_id, thread_id)` starts the claim, takes its instructions from the backend, and works the claim with six tools: `get_claim`, `get_policy`, `get_customer`, `get_policy_wording`, `decide_claim` and `pay_claim`.
  - It records each model message, tool call and tool result as a step.
  - It uses `openai/gpt-6-luna` at low reasoning effort, or the model in `MODEL_NAME`.
  - It makes at most 20 model requests a minute, OpenRouter's limit for new accounts and free models. A claim takes about 15 seconds, and the whole queue about 6 minutes.
- `dashboard/`: React, Vite and TypeScript, with React Router, in the brand's fonts and colors, in light and dark mode.
  - The queue (`/`): a count of the claims in each status, and a table of the claims with each one's status and decision. It refreshes every 2 seconds.
  - A claim (`/claims/CLM-1001`): the decision with its payout, reasons and policy section, the payment and the sign-off, the agent's steps as they happen, the claim in full, the policy, and the customer with their earlier claims. It refreshes every second. While a claim waits for sign-off, a handler picks their name and presses "Sign off and pay".
  - The agent's instructions (`/instructions`), read only.
- `e2e/`: Playwright tests of the queue, a claim page, the live steps, the sign-off and the instructions. They act as the agent through the API, and run on their own ports (backend 8001, dashboard 5174) with a freshly seeded database in the system's temp folder, so they never touch the development data and can run while `npm run dev` is running.

## How to run it

- `npm run dev` starts the backend on port 8000 and the dashboard at http://localhost:5173.
- With the backend running, in a second terminal:
  - `uv run -m agent` works through every claim that isn't decided yet, including any left in progress by a run that stopped.
  - `uv run -m agent CLM-1001 CLM-1002` works just those claims.
- `npm run reset` seeds the database again from `data/`, putting all 25 claims back in the queue.
- `npm run check` runs every check.

## The pilot run

On October 26, 2026, GPT-6 Luna at low effort worked all 25 claims in about 6 minutes, for well under a cent:

- 14 approvals, 7 declines and 4 referrals
- every approval of $1,000 or less paid
- the two approvals over $1,000, CLM-1003 and CLM-1011, held for sign-off

The decisions haven't been scored against the handlers' decisions in `data/evals/`.
