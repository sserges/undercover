# Status

The pilot is being built from `docs/PLAN.md`. Phase 1 of 6 is done.

## What's built

- `backend/`: FastAPI on SQLite.
  - The database is `backend/undercover.db`, or the file named in `UNDERCOVER_DB`. The backend creates it on its first start and seeds it from `data/`.
  - Read operations: `list_claims`, `get_claim`, `get_policy`, `get_customer`, `list_handlers`, `get_policy_wording`, and `health`.
- `agent/`: still the skeleton, with the entry point `run(claim_id, thread_id)` and one tool that calls the health route.
- `dashboard/`: still the skeleton, with one page that shows whether the backend is up.
- `e2e/`: one test of that page.

## How to run it

- `npm run dev` starts the backend on port 8000 and the dashboard on port 5173.
- `npm run reset` seeds the database again from `data/`, putting all 25 claims back in the queue.
- `npm run check` runs every check.
