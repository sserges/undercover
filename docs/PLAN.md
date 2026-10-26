# Plan: the claims pilot

Built from `docs/SPEC.md`, using the choices in `TECH_STACK.md`, the rules in `CODE_STANDARDS.md` and `PROCESS.md`, and the look in `BRAND.md`.

## The shape of it

Three parts, all talking through one API:

```
dashboard (React)  --HTTP-->  backend (FastAPI + SQLite)  <--HTTP--  UnderCover Agent (LangChain)
queue, claim page,            the records and the rules,             reads a claim, decides it,
live steps, sign-off          including the $1,000 block             pays it: uv run -m agent
```

The backend is the only part that holds data or enforces rules. The agent and the dashboard are both clients of its API. Three reasons for this shape:

- `TECH_STACK.md` says the agent reaches claims and its instructions only through the API.
- The sign-off rule must hold "even if the agent tries to pay". If the payment operation refuses, it doesn't matter what the agent decides to do.
- The agent can only see what the API serves, and the API never serves `data/evals/`.

### Claim statuses

| Status | Label | Color | How a claim gets there |
|---|---|---|---|
| `waiting` | Waiting | Cerulean | The seed data (`open` in `data/claims.json`) |
| `in_progress` | In progress | Marigold | The agent starts work on it |
| `waiting_for_sign_off` | Waiting for sign-off | Coral | The agent approves a payout over $1,000 |
| `decided` | Decided | Sea Green | The agent declines, refers or approves $1,000 or less, or a handler signs off |

```
waiting --start--> in_progress --decide--> decided                                  (decline, refer, approve up to $1,000)
                               --decide--> waiting_for_sign_off --sign off--> decided  (approve over $1,000; sign-off pays)
```

### The rules the backend enforces

- A claim can be started while it's waiting or in progress. Starting it again from in progress clears its earlier steps, so a run that crashed can be run again.
- A claim is decided once, and only while it's in progress.
- Decline and refer carry a payout of $0. Approve needs a payout above $0.
- `pay_claim` works only on an approved claim, only for exactly the approved payout, and only once.
- If the approved payout is over the limit in `data/company.json` ($1,000), `pay_claim` refuses with 403 until a handler signs off. Signing off makes the held payment. A payout of exactly $1,000.00 goes straight through, because the rule is "over $1,000".

Unknown ids give 404 and steps out of order give 409. Each error has a plain-English `detail`, which the agent reads when a call is refused.

### The API

Every operation has an `operation_id` that matches its function name, a one-line docstring and only required inputs.

| Operation | Method and path | Used by |
|---|---|---|
| `health` | `GET /api/health` | already built |
| `list_claims` | `GET /api/claims` | dashboard, agent command line |
| `get_claim` | `GET /api/claims/{claim_id}` | dashboard, agent |
| `get_policy` | `GET /api/policies/{policy_id}` | dashboard, agent: the policy with its plan's limits |
| `get_customer` | `GET /api/customers/{customer_id}` | dashboard, agent: the customer and their claim history |
| `list_handlers` | `GET /api/handlers` | dashboard: who can sign off |
| `get_policy_wording` | `GET /api/policy-wording` | agent |
| `get_instructions` | `GET /api/instructions` | agent, dashboard |
| `start_claim` | `POST /api/claims/{claim_id}/start` | agent |
| `add_step` | `POST /api/claims/{claim_id}/steps` | agent |
| `list_steps` | `GET /api/claims/{claim_id}/steps` | dashboard |
| `decide_claim` | `POST /api/claims/{claim_id}/decision` | agent |
| `pay_claim` | `POST /api/claims/{claim_id}/payment` | agent |
| `sign_off_claim` | `POST /api/claims/{claim_id}/sign-off` | dashboard |

`get_claim` returns the claim with its status, its decision, its payment and its sign-off; the last three are empty until they happen. `list_claims` returns one row per claim for the queue: id, customer name, type, summary, amount claimed, date submitted, status, decision and payout.

### Where the data lives

- **SQLite**, using Python's built-in `sqlite3`, in `backend/undercover.db`. `*.db` is already in `.gitignore`. The environment variable `UNDERCOVER_DB` points it at another file, so tests and the end-to-end run each get their own database.
- On its first start the backend creates the database and seeds it from `data/claims.json`, `policies.json`, `customers.json` and `handlers.json`. `npm run reset` (`uv run -m backend.db`) seeds it again from scratch, which lets you rerun the pilot.
- **Tables:** `claims`, `policies`, `customers` and `handlers` hold each record as JSON beside its id, and `claims` also has a `status` column. `decisions`, `payments`, `sign_offs` and `steps` hold what the agent and the handlers add.
- **Fixed documents, read from files:** `data/company.json` for the approval limit, `data/plans.json`, `data/policy_wording.md`, and `backend/instructions.md`, the agent's instructions, which are read only.
- The loader names each file it reads. Nothing reads `data/evals/`, `data/security/`, `data/claims_manual.md` or `data/knowledge.json`.

### The agent

`run(claim_id, thread_id)` in `agent/main.py` does five things:

1. Calls `start_claim`.
2. Fetches its instructions from `get_instructions` and uses them as the system prompt.
3. Builds the agent with `create_agent` and six tools. Each tool wraps one API operation: `get_claim`, `get_policy`, `get_customer`, `get_policy_wording`, `decide_claim` and `pay_claim`. When the backend refuses a call, the tool gives the model the backend's explanation rather than raising an error, so the agent can carry on.
4. Streams the run and posts each model message, tool call and tool result to `add_step`. The runner records the steps, not the model, so the trace is complete and the model can't skip a step.
5. Returns the agent's final reply.

`uv run -m agent CLM-1001 CLM-1002` runs the agent on those claims. `uv run -m agent` with no ids works through every waiting claim in the queue, one at a time, with a new thread id for each.

The instructions tell the agent to:

- read the claim, then the policy, the customer's claim history and the policy wording
- decide from the wording alone, since the pilot has no claims manual
- refer a claim when a required document is missing or the claim needs a person's judgment
- work out the payout as section 10 of the wording describes
- explain the decision in two or three sentences and name the section it rests on
- after approving, pay the approved payout, unless the decision's response says the claim is waiting for sign-off

The model is `openai/gpt-6-luna` at low reasoning effort, or `MODEL_NAME` if it's set, as the skeleton already does.

### The dashboard

There are three pages, with React Router as the one new dependency:

- **Queue (`/`):** a tile for each status with its count, and a table of the claims. It refreshes every 2 seconds, so you can watch the agent move through the queue.
- **Claim (`/claims/:claimId`):**
  - the decision panel: the decision, the payout, the reasons and the policy section, plus the payment or the sign-off form
  - the agent's steps, refreshed every second while the claim is in progress, with long tool results folded away
  - the claim itself: the story, the items and the documents
  - the policy, and the customer with their earlier claims
- **Instructions (`/instructions`):** the agent's instructions as plain text, with no way to edit them.

The sign-off form lists the three handlers. With no sign-in, whoever is at the screen picks their name and presses "Sign off and pay".

The look follows `BRAND.md`:

- fonts from Google Fonts, and colors as CSS variables
- light and dark mode from the system setting
- rounded panels with no outlines
- JetBrains Mono for ids and amounts
- money as $1,250.00

`dashboard/src/api.ts` holds the typed fetch functions, with TypeScript types that match the backend's models.

### Tests

- **pytest:** a fixture gives each test a freshly seeded database in a temporary folder. The agent tests use the skeleton's stub model, with `TestClient` in place of HTTP. No test calls a model.
- **vitest:** the components are tested with a stubbed `fetch`.
- **Playwright:** the end-to-end run starts its own backend on port 8001 with its own freshly seeded database, and its own dashboard on port 5174. That way `npm run check` never touches the data in your development database, and it works while `npm run dev` is running. The Vite proxy target becomes an environment variable that defaults to port 8000. The tests act as the agent through the API (start, steps, decide, pay) and check what the dashboard shows.

### Decisions for you to review

1. **The agent runs from the command line.** The spec asks the dashboard to show the agent's work, not to start it.
2. **Signing off makes the held payment.** There is no way for a handler to overturn the agent's decision, because the spec doesn't ask for one.
3. **The agent is told not to pay a claim that's waiting for sign-off.** The backend refuses the payment either way.
4. **The end-to-end tests get their own ports and database**, so the checks can't wipe out the decisions in your development database.
5. **The agent isn't scored against `data/evals/`.** The spec says the handlers' decisions are for checking the agent "later", and `PROCESS.md` says not to open that folder unless asked. If you'd like, I can compare the queue run with the handlers' decisions after Phase 6.

### Not in this plan

As `SPEC.md` asks, the pilot leaves out the claims manual, sign-in, real payments and messages to customers. It also leaves out:

- `data/knowledge.json`, `data/policy_wording_short.md` and the security claim in `data/security/`
- starting the agent from the dashboard
- scoring against the evaluation set

---

## Phase 1: The records

**What it builds:**

- `backend/db.py`: the schema, the seed from `data/`, the reset command and a connection for each request
- `backend/models.py`: Pydantic models for the responses
- the read operations: `list_claims`, `get_claim`, `get_policy`, `get_customer`, `list_handlers` and `get_policy_wording`
- the `npm run reset` script
- the pytest fixture that gives each test a fresh database

**Why first:** everything else reads these records. Getting the seed and the shapes right first means the agent and the dashboard are built against an API that's already tested. A test also checks every route in the OpenAPI schema against the API rules in `TECH_STACK.md`, so the rules keep holding as the API grows.

- [x] `uv run pytest -q backend` passes, with tests for each read operation and for the 404s
- [x] A test walks `app.openapi()` and checks that every operation has an `operationId` and a description, every parameter is required, and every request body and its fields are required
- [x] With no database file, starting the backend creates `backend/undercover.db` with 25 claims, 50 policies, 49 customers and 3 handlers
- [x] `GET /api/claims` returns 25 rows, all with status `waiting`, and each with the customer's name, the claim type, the summary and the amount claimed
- [x] `GET /api/claims/CLM-1001` returns Maya Patel's claim with its story, 3 items and 4 documents, status `waiting`, and no decision, payment or sign-off
- [x] `GET /api/policies/POL-2001` returns a Premium policy with its plan's limits: a $50 deductible and a $300 per-item limit
- [x] `GET /api/customers/CUS-3001` returns Maya Patel with one earlier claim, CLM-0412
- [x] `GET /api/handlers` returns Dana Whitfield, Marcus Oyelaran and Priya Raman
- [x] `GET /api/policy-wording` returns version `2026.1` and the wording's text
- [x] `GET /api/claims/CLM-9999` returns 404 with a `detail`
- [x] After a claim is changed in the database, `npm run reset` brings the queue back to 25 waiting claims
- [x] A search of `backend/` for `evals`, `security`, `claims_manual` and `knowledge` finds nothing
- [x] `npm run check:python` passes with coverage of at least 80%

## Phase 2: Decisions, payments and the sign-off rule

**What it builds:** the write operations: `start_claim`, `add_step`, `list_steps`, `decide_claim`, `pay_claim` and `sign_off_claim`. It also adds the decision, payment and sign-off to `get_claim`, and the decision and payout to `list_claims`.

**Why now, and why in the backend:** the rules in the spec, especially the $1,000 block, belong in one place that every client has to go through. If they're tested here, before an agent exists, the agent can't get around them later.

- [ ] `start_claim` moves a waiting claim to `in_progress`. On an in-progress claim it clears the earlier steps. On a claim that's decided or waiting for sign-off it returns 409
- [ ] `decide_claim` on a waiting claim (not yet started) returns 409, and deciding a claim twice returns 409
- [ ] Decline with a $0 payout leaves the claim `decided`. Decline with a $50 payout returns 422, and approve with a $0 payout returns 422
- [ ] Approving $420.00 leaves the claim `decided`. Paying $420.00 then returns 200 and records the payment. Paying again returns 409, and paying $400.00 returns 409
- [ ] Approving exactly $1,000.00 leaves the claim `decided`, and paying $1,000.00 succeeds
- [ ] Approving $3,000.00 leaves the claim `waiting_for_sign_off`. Paying $3,000.00 then returns 403, with a `detail` that says a handler must sign off, and no payment is recorded
- [ ] Signing off that claim as HND-01 makes it `decided` and records a $3,000.00 payment with the handler and the time. Signing off as an unknown handler returns 404, and signing off a claim that isn't waiting for sign-off returns 409
- [ ] Paying a declined claim returns 409
- [ ] After three steps are added, `list_steps` returns them in order, each with its thread id, kind, text and time
- [ ] On the development server, CLM-1003 goes through the API from start, to an approval of $3,000.00, to a refused payment (403), to a sign-off, and ends `decided` and paid. `npm run reset` afterwards
- [ ] `npm run check:python` passes

## Phase 3: The UnderCover Agent

**What it builds:**

- `backend/instructions.md` and the `get_instructions` operation
- the agent's six tools over the API
- `run(claim_id, thread_id)`, which records the steps
- `agent/__main__.py`, the command that works the queue

**Why this approach:** one tool per API operation means the agent can reach exactly what the API allows and no more. The instructions come from the backend, so the dashboard shows the same text the agent runs on. The runner records the steps from the stream, so the dashboard sees everything the agent does, as it happens.

- [ ] `GET /api/instructions` returns the text of `backend/instructions.md`
- [ ] Stub-model test: a scripted run on CLM-1001 calls `get_claim`, `get_policy`, `get_customer`, `get_policy_wording`, `decide_claim` (approve $420.00) and `pay_claim`. Afterwards the claim is `decided` and paid, and `list_steps` shows each tool call and result in order, with the run's thread id
- [ ] Stub-model test: a scripted approval over $1,000 followed by `pay_claim` gives the model the backend's sign-off refusal without raising an error. The claim stays `waiting_for_sign_off` with no payment
- [ ] Stub-model test: the system prompt the model receives is the text served by `get_instructions`
- [ ] Command-line test: with no ids, the command runs every waiting claim and skips the others. With ids, it runs just those
- [ ] The model test still passes: `openai/gpt-6-luna` by default, and `MODEL_NAME` overrides it
- [ ] A search of `agent/` for `data/` finds nothing, so the agent reads only through the API
- [ ] Live, with `npm run dev` running: `uv run -m agent CLM-1001` on the real model finishes with a reply. `GET /api/claims/CLM-1001` then shows a decision with a payout, reasons in two or three sentences and a policy section, and `list_steps` shows the run. This costs well under a cent. `npm run reset` afterwards
- [ ] `npm run check:python` passes

## Phase 4: The dashboard and the queue

**What it builds:**

- the brand: fonts, color variables, and light and dark mode
- the layout, with a header and links to the Queue and the Instructions
- the router and `api.ts`
- the queue page, with its status tiles and its table, refreshing every 2 seconds
- the end-to-end setup, with its own ports and a fresh database
- a queue test in place of the health end-to-end test

**Why now:** the API is finished and tested, so the dashboard can be built against real responses. Moving the end-to-end tests to their own servers now keeps every later check from touching your development data.

- [ ] vitest: the queue shows each claim with its status label, a link to its claim page and its amounts formatted as money, such as $1,150.00. The tiles count the claims in each status
- [ ] e2e: the queue shows 25 claims, and the Waiting tile shows 25
- [ ] e2e: after the test starts a claim through the API, the queue shows it as In progress without a page reload
- [ ] `npm run e2e` passes while `npm run dev` is running, and the development database is unchanged afterwards
- [ ] In the browser, through the Playwright MCP server, at http://localhost:5173, the queue follows `BRAND.md`:
  - Instrument Sans for text, and JetBrains Mono for ids and amounts
  - the four status colors
  - rounded panels without outlines
  - no edge borders and no line across the top of the page
  - screenshots in light mode and in dark mode
- [ ] `npm run check:ts` passes: ESLint, Prettier, strict tsc, and vitest with at least 80% coverage

## Phase 5: The claim page, live steps, sign-off and instructions

**What it builds:** the claim page, the live list of steps, the sign-off form and the instructions page.

**Why this approach:** the claim page is where a handler checks the agent's work, so it puts the decision and its reasons at the top. The steps sit beside them, and the full claim, the policy and the customer's history follow underneath. The sign-off form appears only while a claim is waiting for sign-off.

- [ ] vitest covers the decision panel, the steps, the sign-off form and the instructions page
- [ ] e2e: the CLM-1001 page shows the story, 3 items, 4 documents, the Premium policy, and Maya Patel's earlier claim CLM-0412
- [ ] e2e: the test acts as the agent through the API on a claim: it starts the claim, adds two steps, then declines with reasons and a section. The claim page shows the steps, the decision Decline, the reasons, the section and the status Decided
- [ ] e2e: with the claim page open, a step the test adds through the API appears without a page reload
- [ ] e2e: after an approval of $3,000.00 through the API, the page shows Waiting for sign-off and the sign-off form, and a payment through the API returns 403. Choosing Dana Whitfield and pressing "Sign off and pay" leaves the claim Decided, and the page shows $3,000.00 paid and signed off by Dana Whitfield
- [ ] e2e: the instructions page shows the agent's instructions and has no editing control
- [ ] In the browser, through the Playwright MCP server, the claim page follows `BRAND.md`, with screenshots in light mode and in dark mode
- [ ] `npm run check` passes

## Phase 6: The pilot run

**What it builds:** no new features. The real agent works the whole queue while we watch it in the dashboard, and anything the run shows up gets fixed, most likely in the instructions. `docs/STATUS.md` gets its final update.

**Why a phase of its own:** this is the first time the live model, the backend's rules and the dashboard all run together, on all 25 claims. GPT-6 Luna at low effort costs about a cent for the whole queue.

- [ ] After `npm run reset` and `npm run dev`, `uv run -m agent` works through the queue. Every one of the 25 claims ends Decided or Waiting for sign-off, and none is stuck In progress
- [ ] While the agent runs, the dashboard, seen through the Playwright MCP server, shows a claim In progress with its steps appearing live. Screenshot
- [ ] Through the API, every decided claim has a decision, reasons in two or three sentences and a policy section, and every approval has a payout
- [ ] Every approval over $1,000 is Waiting for sign-off with no payment recorded
- [ ] Signing off one of those claims in the dashboard leaves it Decided and paid
- [ ] `docs/STATUS.md` describes what's built and how to run it on Windows and Mac: `npm run dev`, `uv run -m agent` and `npm run reset`
- [ ] `npm run check` passes
