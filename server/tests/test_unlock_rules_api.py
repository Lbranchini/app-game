"""Tests for the /unlocks/rules catalog endpoint and UnlockRule data shape."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agora.application.use_cases.unlocks import DEFAULT_RULES, UnlockRule
from agora.domain.player import Player
from agora.interfaces.api.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_rules_endpoint_lists_default_catalog(client: TestClient) -> None:
    response = client.get("/unlocks/rules")
    assert response.status_code == 200
    payload = response.json()
    ids = {r["character_id"] for r in payload}
    assert ids == {r.character_id for r in DEFAULT_RULES}


def test_rules_payload_carries_progress_key_and_target(client: TestClient) -> None:
    response = client.get("/unlocks/rules").json()
    medusa = next(r for r in response if r["character_id"] == "medusa")
    assert medusa["progress_key"] == "wins"
    assert medusa["target"] == 5
    assert "5" in medusa["description"]


# --------------------------------------------------------------------------- #
# UnlockRule data shape                                                       #
# --------------------------------------------------------------------------- #


def _player_with(progress: dict[str, int]) -> Player:
    return Player(
        id="00000000-0000-0000-0000-000000000000",
        provider_subject="google:test",
        progress=progress,
    )


def test_threshold_rule_progress_for_returns_current_and_target() -> None:
    rule = UnlockRule(
        character_id="medusa",
        description="Win 5 ranked matches",
        progress_key="wins",
        target=5,
    )
    assert rule.progress_for(_player_with({"wins": 3})) == (3, 5)
    assert rule.progress_for(_player_with({})) == (0, 5)


def test_threshold_rule_is_satisfied_at_target() -> None:
    rule = UnlockRule(
        character_id="medusa",
        description="...",
        progress_key="wins",
        target=5,
    )
    assert not rule.is_satisfied(_player_with({"wins": 4}))
    assert rule.is_satisfied(_player_with({"wins": 5}))
    assert rule.is_satisfied(_player_with({"wins": 7}))


def test_custom_predicate_rule_is_supported() -> None:
    rule = UnlockRule(
        character_id="x",
        description="custom",
        predicate=lambda p: p.progress.get("any", 0) > 0,
    )
    assert not rule.is_satisfied(_player_with({}))
    assert rule.is_satisfied(_player_with({"any": 1}))
    assert rule.progress_for(_player_with({"any": 1})) is None


def test_rule_without_threshold_or_predicate_is_invalid() -> None:
    with pytest.raises(ValueError):
        UnlockRule(character_id="x", description="empty")
