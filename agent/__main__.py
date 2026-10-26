"""Work the claims queue: uv run -m agent [CLAIM_ID ...]"""

import sys
import uuid

from agent.main import api, run


def main(claim_ids: list[str]) -> None:
    """Run the agent on the claims named, or on every waiting claim in the queue."""
    if not claim_ids:
        queue = api("GET", "/api/claims")
        claim_ids = [c["claim_id"] for c in queue if c["status"] == "waiting"]
    for claim_id in claim_ids:
        print(f"{claim_id}: working")
        print(f"{claim_id}: {run(claim_id, str(uuid.uuid4()))}")


if __name__ == "__main__":
    main(sys.argv[1:])
