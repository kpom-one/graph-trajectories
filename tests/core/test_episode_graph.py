"""Tests for episode graph generation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import networkx as nx
import pytest
from lib.core.episode_graph import (
    path_to_state_dirs,
    namespace_node,
    build_episode_graph,
    build_episode_from_path,
    TEMPORAL_EDGE,
)
from lib.core.graph import save_dot


class TestNamespaceNode:
    def test_simple_node(self):
        assert namespace_node("game", 0) == "game@0"
        assert namespace_node("game", 5) == "game@5"

    def test_player_node(self):
        assert namespace_node("p1", 2) == "p1@2"

    def test_card_node(self):
        assert namespace_node("p1.elsa_snow_queen.a", 3) == "p1.elsa_snow_queen.a@3"

    def test_step_node(self):
        assert namespace_node("step.p1.main", 1) == "step.p1.main@1"


class TestPathToStateDirs:
    def test_finds_state_sequence(self, tmp_path):
        # Create a path structure: seed/0/1/2
        seed = tmp_path / "seed"
        s0 = seed
        s1 = seed / "0"
        s2 = seed / "0" / "1"
        s3 = seed / "0" / "1" / "2"

        for d in [s0, s1, s2, s3]:
            d.mkdir(parents=True, exist_ok=True)
            (d / "game.dot").write_text("digraph { }")

        dirs = path_to_state_dirs(s3)
        assert len(dirs) == 4
        assert dirs[0] == s0
        assert dirs[1] == s1
        assert dirs[2] == s2
        assert dirs[3] == s3

    def test_single_state(self, tmp_path):
        seed = tmp_path / "seed"
        seed.mkdir()
        (seed / "game.dot").write_text("digraph { }")

        dirs = path_to_state_dirs(seed)
        assert len(dirs) == 1
        assert dirs[0] == seed

    def test_no_game_dot_raises(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()

        with pytest.raises(ValueError, match="No game.dot files found"):
            path_to_state_dirs(empty)


class TestBuildEpisodeGraph:
    def test_single_state_namespaces_nodes(self, tmp_path):
        # Create a simple graph
        G = nx.MultiDiGraph()
        G.add_node("game", type="Game", turn="1")
        G.add_node("p1", type="Player", lore="5")
        G.add_edge("game", "p1", label="CURRENT_TURN")

        state_dir = tmp_path / "state0"
        state_dir.mkdir()
        save_dot(G, state_dir / "game.dot")

        episode_graph = build_episode_graph([state_dir])

        # Check namespaced nodes exist
        assert "game@0" in episode_graph.nodes()
        assert "p1@0" in episode_graph.nodes()
        assert "game" not in episode_graph.nodes()  # Original not present

        # Check attributes preserved
        assert episode_graph.nodes["game@0"]["type"] == "Game"
        assert episode_graph.nodes["p1@0"]["lore"] == "5"

        # Check state_index added
        assert episode_graph.nodes["game@0"]["state_index"] == "0"

    def test_single_state_namespaces_edges(self, tmp_path):
        G = nx.MultiDiGraph()
        G.add_node("game", type="Game")
        G.add_node("p1", type="Player")
        G.add_edge("game", "p1", label="CURRENT_TURN", custom_attr="value")

        state_dir = tmp_path / "state0"
        state_dir.mkdir()
        save_dot(G, state_dir / "game.dot")

        episode_graph = build_episode_graph([state_dir])

        # Check edge exists with namespaced endpoints
        edges = list(episode_graph.edges("game@0", data=True))
        assert len(edges) == 1
        u, v, data = edges[0]
        assert u == "game@0"
        assert v == "p1@0"

    def test_two_states_adds_temporal_edges(self, tmp_path):
        # State 0
        G0 = nx.MultiDiGraph()
        G0.add_node("game", type="Game", turn="1")
        G0.add_node("p1", type="Player", lore="0")

        s0 = tmp_path / "s0"
        s0.mkdir()
        save_dot(G0, s0 / "game.dot")

        # State 1 - same nodes, different attributes
        G1 = nx.MultiDiGraph()
        G1.add_node("game", type="Game", turn="2")
        G1.add_node("p1", type="Player", lore="3")

        s1 = tmp_path / "s1"
        s1.mkdir()
        save_dot(G1, s1 / "game.dot")

        episode_graph = build_episode_graph([s0, s1])

        # Check both states present
        assert "game@0" in episode_graph.nodes()
        assert "game@1" in episode_graph.nodes()
        assert "p1@0" in episode_graph.nodes()
        assert "p1@1" in episode_graph.nodes()

        # Check temporal edges
        temporal_edges = [
            (u, v) for u, v, d in episode_graph.edges(data=True)
            if d.get("label") == TEMPORAL_EDGE
        ]
        assert ("game@0", "game@1") in temporal_edges
        assert ("p1@0", "p1@1") in temporal_edges

        # Attributes preserved per state
        assert episode_graph.nodes["p1@0"]["lore"] == "0"
        assert episode_graph.nodes["p1@1"]["lore"] == "3"

    def test_node_disappears_no_forward_temporal_edge(self, tmp_path):
        # State 0 has card
        G0 = nx.MultiDiGraph()
        G0.add_node("game", type="Game")
        G0.add_node("p1.card.a", type="Card", zone="play")

        s0 = tmp_path / "s0"
        s0.mkdir()
        save_dot(G0, s0 / "game.dot")

        # State 1 - card gone (banished)
        G1 = nx.MultiDiGraph()
        G1.add_node("game", type="Game")

        s1 = tmp_path / "s1"
        s1.mkdir()
        save_dot(G1, s1 / "game.dot")

        episode_graph = build_episode_graph([s0, s1])

        # Card@0 exists, card@1 doesn't
        assert "p1.card.a@0" in episode_graph.nodes()
        assert "p1.card.a@1" not in episode_graph.nodes()

        # No temporal edge for disappeared card
        temporal_edges = [
            (u, v) for u, v, d in episode_graph.edges(data=True)
            if d.get("label") == TEMPORAL_EDGE and "card" in u
        ]
        assert len(temporal_edges) == 0

    def test_node_appears_no_backward_temporal_edge(self, tmp_path):
        # State 0 - no card
        G0 = nx.MultiDiGraph()
        G0.add_node("game", type="Game")

        s0 = tmp_path / "s0"
        s0.mkdir()
        save_dot(G0, s0 / "game.dot")

        # State 1 - card appears (played from hand)
        G1 = nx.MultiDiGraph()
        G1.add_node("game", type="Game")
        G1.add_node("p1.card.a", type="Card", zone="play")

        s1 = tmp_path / "s1"
        s1.mkdir()
        save_dot(G1, s1 / "game.dot")

        episode_graph = build_episode_graph([s0, s1])

        # card@1 exists, card@0 doesn't
        assert "p1.card.a@0" not in episode_graph.nodes()
        assert "p1.card.a@1" in episode_graph.nodes()

        # No temporal edge for newly appeared card
        temporal_edges = [
            (u, v) for u, v, d in episode_graph.edges(data=True)
            if d.get("label") == TEMPORAL_EDGE and "card" in u
        ]
        assert len(temporal_edges) == 0


class TestBuildEpisodeFromPath:
    def test_integration_with_real_example(self):
        """Test with actual example data if available."""
        example_path = Path("output.example/459b/1sh7asne/3/0/6/0")

        if not example_path.exists():
            pytest.skip("Example data not available")

        episode_graph = build_episode_from_path(example_path)

        # Should have 5 states: seed + 4 actions (3/0/6/0)
        state_indices = set()
        for node in episode_graph.nodes():
            if "@" in node:
                idx = node.split("@")[-1]
                state_indices.add(int(idx))

        assert len(state_indices) == 5
        assert state_indices == {0, 1, 2, 3, 4}

        # Should have temporal edges
        temporal_count = sum(
            1 for _, _, d in episode_graph.edges(data=True)
            if d.get("label") == TEMPORAL_EDGE
        )
        assert temporal_count > 0

        # game node should exist in all states
        for i in range(5):
            assert f"game@{i}" in episode_graph.nodes()
