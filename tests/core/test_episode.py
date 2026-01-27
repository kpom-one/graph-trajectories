"""
Integration tests for Episode export.

Tests the full flow: create_initial_state -> GameSession -> get_episode -> to_episode_dir
"""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from lib.lorcana.setup import create_initial_state
from lib.lorcana.game_api import GameSession
from lib.core.memory_store import MemoryStore


@pytest.fixture(scope="module")
def completed_game():
    """Play a game once, reuse across all tests."""
    state = create_initial_state(
        "data/decks/debug-gp.txt",
        "data/decks/debug-ys.txt",
        seed="test123"
    )

    store = MemoryStore()
    session = GameSession(state, store=store, root_key="test123")
    session.play_until_game_over()

    episode = store.get_episode(session.current_key)

    return {
        "session": session,
        "store": store,
        "episode": episode,
    }


@pytest.fixture
def episode_dir(completed_game, tmp_path):
    """Export episode to temp directory."""
    output = tmp_path / "game.episode"
    completed_game["episode"].to_episode_dir(output)
    return output


class TestEpisodeExport:
    """Test episode export from gameplay."""

    def test_game_completed(self, completed_game):
        """Game ran to completion with a winner."""
        session = completed_game["session"]
        assert session.is_game_over()
        assert session.get_winner() in ("p1", "p2")

    def test_episode_has_states(self, completed_game):
        """Episode captured multiple states."""
        episode = completed_game["episode"]
        assert len(episode.states) > 1
        assert len(episode.actions) == len(episode.states)
        assert episode.actions[0] == "initial"

    def test_episode_has_outcome(self, completed_game):
        """Episode captured the winner."""
        episode = completed_game["episode"]
        assert episode.outcome["winner"] in ("p1", "p2")

    def test_episode_dir_has_all_files(self, episode_dir):
        """to_episode_dir creates all 5 expected files."""
        assert (episode_dir / "graph.dot").exists()
        assert (episode_dir / "history.txt").exists()
        assert (episode_dir / "result.json").exists()
        assert (episode_dir / "deck1.dek").exists()
        assert (episode_dir / "deck2.dek").exists()

    def test_result_json_content(self, completed_game, episode_dir):
        """result.json has correct winner and state count."""
        episode = completed_game["episode"]
        result = json.loads((episode_dir / "result.json").read_text())

        assert result["winner"] == episode.outcome["winner"]
        assert result["total_states"] == len(episode.states)

    def test_history_has_all_states(self, completed_game, episode_dir):
        """history.txt contains markers for every state."""
        episode = completed_game["episode"]
        history = (episode_dir / "history.txt").read_text()

        for i in range(len(episode.states)):
            assert f"=== state {i} ===" in history

    def test_graph_dot_has_temporal_edges(self, episode_dir):
        """graph.dot connects states with temporal 'next' edges."""
        dot_content = (episode_dir / "graph.dot").read_text()

        assert "game@0" in dot_content
        assert "game@1" in dot_content
        assert "next" in dot_content

    def test_deck_files_populated(self, episode_dir):
        """deck1.dek and deck2.dek contain card IDs."""
        deck1 = (episode_dir / "deck1.dek").read_text().strip()
        deck2 = (episode_dir / "deck2.dek").read_text().strip()

        assert len(deck1) > 0
        assert len(deck2) > 0
