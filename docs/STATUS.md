# Status

The pilot is being built from `docs/PLAN.md`. Phases 1 and 2 of 6 are done.

## What's built

- `backend/`: FastAPI on SQLite.
  - The database is `backend/undercover.db`, or the file named in `UNDERCOVER_DB`. The backend creates it on its first start and seeds it from `data/`.
  - Read operations: `list_claims`, `get_claim`, `get_policy`, `get_customer`, `list_handlers`, `get_policy_wording`, and `health`.
  - Work on a claim: `start_claim`, `add_step`, `list_steps`, `decide_claim`, `pay_claim` and `sign_off_claim`.
  - A claim moves from `waiting` to `in_progress`, then to `decided`, or to `waiting_for_sign_off` when the agent approves a payout over $1,000. `pay_claim` refuses such a payout with 403 until a handler signs off, and the sign-off makes the payment.
- `agent/`: still the skeleton, with the entry point `run(claim_id, thread_id)` and one tool that calls the health route.
- `dashboard/`: still the skeleton, with one page that shows whether the backend is up.
- `e2e/`: one test of that page.

## How to run it

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173.
- `npm run reset` seeds the database again from `data/`, putting all 25 claims back in the queue.
- `npm run check` runs every check.
