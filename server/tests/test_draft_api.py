"""End-to-end tests for the draft REST surface, ending in a created match."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agora.interfaces.api.main import create_app
from agora.interfaces.api.routers import match as match_router


@pytest.fixture(autouse=True)
def reset_runtime() -> None:
    match_router._runtime = None


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_full_draft_flow_through_to_match(client: TestClient) -> None:
    started = client.post(
        "/draft/start",
        json={"side_a_player_id": "p1", "side_b_player_id": "p2", "arena_id": "olympus"},
    )
    assert started.status_code == 200, started.text
    draft_id = started.json()["draft_id"]
    assert started.json()["phase"] == "ban"

    assert client.post(
        f"/draft/{draft_id}/ban", json={"side": "A", "character_id": "loki"}
    ).status_code == 200
    after_ban = client.post(
        f"/draft/{draft_id}/ban", json={"side": "B", "character_id": "anubis"}
    )
    assert after_ban.json()["phase"] == "pick"

    for side, char_id in [
        ("A", "achilles"),
        ("B", "thor"),
        ("B", "isis"),
        ("A", "athena"),
        ("A", "medusa"),
        ("B", "amaterasu"),
    ]:
        response = client.post(
            f"/draft/{draft_id}/pick", json={"side": side, "character_id": char_id}
        )
        assert response.status_code == 200, response.text

    assert client.get(f"/draft/{draft_id}").json()["phase"] == "confirm"

    finalize = client.post(f"/draft/{draft_id}/finalize")
    assert finalize.status_code == 200
    payload = finalize.json()
    assert payload["draft"]["phase"] == "done"
    assert payload["match_id"]

    # Match exists and reflects the drafted teams.
    match_state = client.get(f"/match/{payload['match_id']}").json()
    assert [c["id"] for c in match_state["a"]["characters"]] == ["achilles", "athena", "medusa"]
    assert [c["id"] for c in match_state["b"]["characters"]] == ["thor", "isis", "amaterasu"]
    assert match_state["arena_id"] == "olympus"


def test_unknown_arena_returns_400(client: TestClient) -> None:
    response = client.post(
        "/draft/start",
        json={"side_a_player_id": "p1", "side_b_player_id": "p2", "arena_id": "atlantis"},
    )
    assert response.status_code == 400


def test_pick_out_of_turn_returns_400(client: TestClient) -> None:
    started = client.post(
        "/draft/start",
        json={"side_a_player_id": "p1", "side_b_player_id": "p2", "arena_id": "neutral"},
    ).json()
    client.post(
        f"/draft/{started['draft_id']}/ban", json={"side": "A", "character_id": "loki"}
    )
    client.post(
        f"/draft/{started['draft_id']}/ban", json={"side": "B", "character_id": "anubis"}
    )
    # Side A picks first per snake order.
    bad = client.post(
        f"/draft/{started['draft_id']}/pick", json={"side": "B", "character_id": "thor"}
    )
    assert bad.status_code == 400


def test_finalize_before_picks_done_returns_400(client: TestClient) -> None:
    started = client.post(
        "/draft/start",
        json={"side_a_player_id": "p1", "side_b_player_id": "p2", "arena_id": "neutral"},
    ).json()
    response = client.post(f"/draft/{started['draft_id']}/finalize")
    assert response.status_code == 400


def test_get_unknown_draft_returns_404(client: TestClient) -> None:
    response = client.get("/draft/does-not-exist")
    assert response.status_code == 404


def test_cancel_marks_draft_cancelled(client: TestClient) -> None:
    started = client.post(
        "/draft/start",
        json={"side_a_player_id": "p1", "side_b_player_id": "p2", "arena_id": "neutral"},
    ).json()
    response = client.post(f"/draft/{started['draft_id']}/cancel")
    assert response.json()["phase"] == "cancelled"
