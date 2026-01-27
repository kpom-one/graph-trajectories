"""
Episode: a complete game playthrough.

An Episode captures the full history of a game:
- Sequence of game states (graphs)
- Actions taken at each step
- Starting deck lists
- Final outcome (winner, lore)

Can be built from either StateStore type and serialized
to a self-contained .episode directory.
"""
from dataclasses import dataclass
from pathlib import Path
import json
import networkx as nx

from lib.core.graph import save_dot
from lib.core.diff import diff_graphs
from lib.core.episode_graph import build_episode_graph_from_states


@dataclass
class Episode:
    """
    A complete game playthrough.

    Attributes:
        states: Game state graph at each step
        actions: Action taken to reach each state (first is "initial")
        decks: Starting deck lists (deck1_ids, deck2_ids)
        outcome: Game result {winner, p1_lore, p2_lore}
        game_id: Identifier for this episode
        source_path: Where this episode came from (for debugging)
    """
    states: list[nx.MultiDiGraph]
    actions: list[str]
    decks: tuple[list, list]
    outcome: dict
    game_id: str = ""
    source_path: str = ""

    def to_episode_dir(self, output_path: str | Path) -> Path:
        """
        Serialize to a .episode directory.

        Creates:
            {output_path}/
                graph.dot       - Stacked state graph with temporal edges
                history.txt     - Concatenated diffs with state markers
                result.json     - Game outcome and metadata
                deck1.dek       - Player 1's starting deck
                deck2.dek       - Player 2's starting deck

        Args:
            output_path: Directory path (will be created)

        Returns:
            Path to the created directory
        """
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        self._write_graph_dot(output_path)
        self._write_history_txt(output_path)
        self._write_result_json(output_path)
        self._write_deck_files(output_path)

        return output_path

    def _write_graph_dot(self, output_path: Path) -> None:
        """Build and write the stacked episode graph."""
        episode_graph = build_episode_graph_from_states(self.states)
        save_dot(episode_graph, output_path / "graph.dot")

    def _write_history_txt(self, output_path: Path) -> None:
        """Write concatenated diffs with state markers."""
        lines = []

        for i, (state, action) in enumerate(zip(self.states, self.actions)):
            # Header
            turn = _clean_attr(state.nodes.get("game", {}).get("turn", "0"))
            p1_lore = _clean_attr(state.nodes.get("p1", {}).get("lore", "0"))
            p2_lore = _clean_attr(state.nodes.get("p2", {}).get("lore", "0"))
            current_player = _get_current_player(state)

            lines.append(f"=== state {i} ===")
            lines.append(f"# turn: {turn}")
            lines.append(f"# current_player: {current_player}")
            lines.append(f"# lore: p1={p1_lore}, p2={p2_lore}")
            lines.append(f"# action: {action}")
            lines.append("")

            # Diff from previous state
            if i > 0:
                diff_lines = diff_graphs(self.states[i - 1], state)
                lines.extend(diff_lines)
            else:
                # First state: show cards as "added"
                for node, attrs in sorted(state.nodes(data=True)):
                    if attrs.get("type") == "Card":
                        attr_str = " ".join(
                            f"{k}={_clean_attr(v)}" for k, v in sorted(attrs.items())
                        )
                        lines.append(f"add node {node} {attr_str}")

            lines.append("")

        (output_path / "history.txt").write_text("\n".join(lines))

    def _write_result_json(self, output_path: Path) -> None:
        """Write game outcome and metadata."""
        final_state = self.states[-1]
        total_turns = int(_clean_attr(
            final_state.nodes.get("game", {}).get("turn", 0)
        ))

        result = {
            "game_id": self.game_id,
            "source_path": self.source_path,
            "winner": self.outcome.get("winner", "unknown"),
            "final_lore": {
                "p1": self.outcome.get("p1_lore", 0),
                "p2": self.outcome.get("p2_lore", 0),
            },
            "total_turns": total_turns,
            "total_states": len(self.states),
        }

        (output_path / "result.json").write_text(json.dumps(result, indent=2))

    def _write_deck_files(self, output_path: Path) -> None:
        """Write starting deck files."""
        deck1_ids, deck2_ids = self.decks
        (output_path / "deck1.dek").write_text("\n".join(deck1_ids))
        (output_path / "deck2.dek").write_text("\n".join(deck2_ids))


def _get_current_player(state: nx.MultiDiGraph) -> str:
    """Extract current player from CURRENT_TURN edge."""
    for u, v, data in state.edges(data=True):
        if data.get("label") == "CURRENT_TURN":
            return v
    return "p1"


def _clean_attr(val) -> str:
    """Clean attribute value (strip quotes)."""
    if val is None:
        return "0"
    if isinstance(val, str):
        return val.strip('"')
    return str(val)
