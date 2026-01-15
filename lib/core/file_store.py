"""
File-based state storage using DOT files.

Persists game states to filesystem as .dot files and .dek files.
"""
import copy
import json
import os
from pathlib import Path
from lib.core.store import StateStore
from lib.core.graph import load_dot, save_dot, get_node_attr
from lib.lorcana.helpers import get_game_context
from lib.core.navigation import write_actions_file, read_actions_file
from lib.core.diff import diff_graphs

# File names
_DEK1_FILE = "deck1.dek"
_DEK2_FILE = "deck2.dek"
_GAME_FILE = "game.dot"
_DIFF_FILE = "diff.txt"
_OUTCOME_FILE = "outcome.txt"
_OUTCOMES_JSON = "outcomes.json"


class FileStore(StateStore):
    """
    File-based state storage.

    Saves states as DOT graphs and deck lists to filesystem.
    Caches loaded states to avoid repeated disk reads.
    """

    def __init__(self):
        self._cache = {}  # path -> state

    def load_state(self, path: Path | str, state_class):
        """
        Load game state from filesystem (cached).

        Args:
            path: Directory containing game.dot and deck files
            state_class: Class to instantiate (e.g., LorcanaState)

        Returns:
            Loaded state instance

        Raises:
            FileNotFoundError: If game.dot doesn't exist
        """
        path = Path(path)
        cache_key = str(path)

        if cache_key in self._cache:
            return copy.deepcopy(self._cache[cache_key])

        game_file = path / _GAME_FILE

        if not game_file.exists():
            raise FileNotFoundError(f"No {_GAME_FILE} at {path}")

        graph = load_dot(game_file)
        deck1_ids = self._load_deck(path, player=1)
        deck2_ids = self._load_deck(path, player=2)

        state = state_class(graph, deck1_ids, deck2_ids)
        self._cache[cache_key] = copy.deepcopy(state)  # Cache a copy to preserve for diffs
        return state

    def save_state(self, state, path: Path | str, format_actions_fn=None, action_taken: str | None = None):
        """
        Save game state to filesystem.

        Args:
            state: State object with graph, deck1_ids, deck2_ids attributes
            path: Directory to save to
            format_actions_fn: Optional function to format actions for actions.txt
            action_taken: Description of action that led to this state (for diff header)
        """
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        # Save core state
        save_dot(state.graph, path / _GAME_FILE)
        self._save_deck(state.deck1_ids, path, player=1)
        self._save_deck(state.deck2_ids, path, player=2)

        # Update cache
        self._cache[str(path)] = state

        # Write actions file if formatter provided
        if format_actions_fn:
            actions = format_actions_fn(state.graph)
            write_actions_file(path, actions)

        # Write diff file
        self._write_diff(state.graph, path, action_taken)

    def state_exists(self, path: Path | str) -> bool:
        """
        Check if state exists on filesystem.

        Args:
            path: Directory that should contain state

        Returns:
            True if game.dot exists, False otherwise
        """
        path = Path(path)
        return (path / _GAME_FILE).exists()

    def get_actions(self, path: Path | str) -> list[dict]:
        """
        Get available actions from actions.txt.

        Args:
            path: Directory containing actions.txt

        Returns:
            List of action dicts with 'id' and 'description' keys
        """
        return read_actions_file(Path(path))

    def save_outcome(self, path: Path | str, suffix: str | None, data: dict) -> None:
        """
        Save outcome data at a path.

        At winning state (suffix=None): writes outcome.txt
        At parent states: updates outcomes.json with aggregated stats
        """
        path = Path(path)

        if suffix is None:
            # Winning state - write actual file
            outcome_file = path / _OUTCOME_FILE
            with open(outcome_file, 'w') as f:
                for key, value in data.items():
                    f.write(f"{key}: {value}\n")
        else:
            # Parent state - update outcomes.json
            outcomes_file = path / _OUTCOMES_JSON

            # Load existing or create new
            if outcomes_file.exists():
                with open(outcomes_file) as f:
                    outcomes = json.load(f)
            else:
                outcomes = {"outcomes": {}, "p1_wins": [], "p2_wins": []}

            # Get first action in suffix (the immediate child)
            first_action = suffix[0] if suffix else ""
            winner = data.get("winner", "")

            # Update per-action stats
            if first_action not in outcomes["outcomes"]:
                outcomes["outcomes"][first_action] = {"p1_wins": 0, "p2_wins": 0}

            if winner == "p1":
                outcomes["outcomes"][first_action]["p1_wins"] += 1
                outcomes["p1_wins"].append(suffix)
            elif winner == "p2":
                outcomes["outcomes"][first_action]["p2_wins"] += 1
                outcomes["p2_wins"].append(suffix)

            # Write back
            with open(outcomes_file, 'w') as f:
                json.dump(outcomes, f, indent=2)

    def get_outcomes(self, path: Path | str) -> dict:
        """Get outcomes data at this state."""
        path = Path(path)
        outcomes_file = path / _OUTCOMES_JSON

        if outcomes_file.exists():
            with open(outcomes_file) as f:
                return json.load(f)

        return {"outcomes": {}, "p1_wins": [], "p2_wins": []}

    # ========== Internal Helpers ==========

    def _load_deck(self, base_path: Path, player: int) -> list[str]:
        """Load deck card IDs for a player."""
        deck_file = _DEK1_FILE if player == 1 else _DEK2_FILE
        path = base_path / deck_file

        if not path.exists():
            return []

        with open(path) as f:
            return [line.strip() for line in f if line.strip()]

    def _save_deck(self, deck_ids: list[str], base_path: Path, player: int) -> None:
        """
        Save deck card IDs for a player.

        Symlinks to parent's deck file if content is unchanged to save disk space.
        """
        deck_file = _DEK1_FILE if player == 1 else _DEK2_FILE
        path = base_path / deck_file

        # Check if parent has same deck content - symlink if so
        parent_deck = base_path.parent / deck_file
        if parent_deck.exists():
            parent_ids = self._load_deck(base_path.parent, player)
            if parent_ids == deck_ids:
                # Content matches - create symlink instead of copying
                if path.exists() or path.is_symlink():
                    path.unlink()
                os.symlink(parent_deck.resolve(), path)
                return

        # Content differs or no parent - write new file
        with open(path, 'w') as f:
            for card_id in deck_ids:
                f.write(f"{card_id}\n")

    def _write_diff(self, graph, path: Path, action_taken: str | None) -> None:
        """
        Write diff.txt showing changes from parent state.

        Args:
            graph: Current state graph
            path: Directory being saved to
            action_taken: Description of action (for header)
        """
        # Try cache first (parent was likely just loaded)
        parent_key = str(path.parent)
        if parent_key in self._cache:
            parent_graph = self._cache[parent_key].graph
        else:
            parent_game = path.parent / _GAME_FILE
            if not parent_game.exists():
                return  # No parent to diff against
            parent_graph = load_dot(parent_game)
        diff_lines = diff_graphs(parent_graph, graph)

        # Build header
        turn = get_node_attr(graph, 'game', 'turn', '?')
        p1_lore = get_node_attr(graph, 'p1', 'lore', '0')
        p2_lore = get_node_attr(graph, 'p2', 'lore', '0')

        # Find current player
        ctx = get_game_context(graph)
        current_player = ctx['player'] if ctx else '?'

        header = [
            f"# turn: {turn}",
            f"# current_player: {current_player}",
            f"# lore: p1={p1_lore}, p2={p2_lore}",
            f"# action: {action_taken or 'initial'}",
        ]

        with open(path / _DIFF_FILE, 'w') as f:
            for line in header:
                f.write(f"{line}\n")
            if diff_lines:
                f.write("\n")
                for line in diff_lines:
                    f.write(f"{line}\n")
