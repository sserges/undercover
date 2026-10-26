import pytest
from fastapi.testclient import TestClient

from agent import main
from backend import db
from backend.main import app


@pytest.fixture(autouse=True)
def backend(tmp_path, monkeypatch):
    """Point the agent at a test backend with a freshly seeded database."""
    monkeypatch.setenv("UNDERCOVER_DB", str(tmp_path / "undercover.db"))
    db.reset()
    monkeypatch.setattr(main, "backend", lambda: TestClient(app))
