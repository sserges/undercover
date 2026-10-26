"""Work the claims queue: uv run -m agent [CLAIM_ID ...]"""

import sys
import uuid

from agent.main import api, run

TO_WORK = {"waiting", "in_progress"}


def main(claim_ids: list[str]) -> None:
    """Run the agent on the claims named, or on every claim not yet decided.

    That includes claims left in progress by a run that stopped part way.
    """
    if not claim_ids:
        queue = api("GET", "/api/claims")
        claim_ids = [c["claim_id"] for c in queue if c["status"] in TO_WORK]
    for claim_id in claim_ids:
        print(f"{claim_id}: working", flush=True)
        print(f"{claim_id}: {run(claim_id, str(uuid.uuid4()))}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
