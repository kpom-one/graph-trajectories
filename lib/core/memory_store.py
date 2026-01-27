"""
In-memory state storage.

Fast dict-based storage for game states. No filesystem I/O.
Useful for performance-critical operations like game tree search.
"""
from pathlib import Path
from copy import deepcopy
from lib.core.store import StateStore
from lib.core.episode import Episode


class MemoryStore(StateStore):
    """
    In-memory state storage using dictionaries.

    Stores states in memory without writing to disk.
    Much faster than FileStore for batch operations.
    """

    def __init__(self):
        """Initialize empty in-memory storage."""
        # Storage: path -> (graph, deck1_ids, deck2_ids)
        self._states = {}
        # Optional: path -> formatted_actions (for navigation)
        self._actions = {}
        # Action taken to reach each state: path -> action_description
        self._action_taken = {}
        # Outcomes: path -> outcome_data dict
        self._outcomes = {}
        # Outcome refs: path -> list of action-path suffixes
        self._outcome_refs = {}

    def load_state(self, path: Path | str, state_class):
        """
        Load game state from memory.

        Args:
            path: Key for the state
            state_class: Class to instantiate (e.g., LorcanaState)

        Returns:
            Loaded state instance with deep-copied graph

        Raises:
            KeyError: If state doesn't exist
        """
        path = str(path)  # Normalize to string key

        if path not in self._states:
            raise KeyError(f"State not found: {path}")

        graph, deck1_ids, deck2_ids = self._states[path]

        # Deep copy graph to prevent mutation of stored state
        # Deck lists are copied in state constructor
        return state_class(deepcopy(graph), list(deck1_ids), list(deck2_ids))

    def save_state(self, state, path: Path | str, format_actions_fn=None, action_taken: str | None = None):
        """
        Save game state to memory.

        Args:
            state: State object with graph, deck1_ids, deck2_ids attributes
            path: Key for where to save
            format_actions_fn: Optional function to format actions for navigation
            action_taken: Description of action that led to this state
        """
        path = str(path)  # Normalize to string key

        # Store deep copy to prevent external mutations
        self._states[path] = (
            deepcopy(state.graph),
            list(state.deck1_ids),
            list(state.deck2_ids)
        )

        # Store formatted actions if provided
        if format_actions_fn:
            self._actions[path] = format_actions_fn(state.graph)

        # Store action that led to this state
        if action_taken is not None:
            self._action_taken[path] = action_taken

    def state_exists(self, path: Path | str) -> bool:
        """
        Check if state exists in memory.

        Args:
            path: Key for the state

        Returns:
            True if state exists, False otherwise
        """
        return str(path) in self._states

    def get_actions(self, path: Path | str) -> list[dict]:
        """
        Get formatted actions for a state (if available).

        Args:
            path: Key for the state

        Returns:
            List of action dicts with 'id' and 'description' keys
        """
        return self._actions.get(str(path), [])

    def clear(self):
        """Clear all stored states from memory."""
        self._states.clear()
        self._actions.clear()
        self._action_taken.clear()
        self._outcomes.clear()
        self._outcome_refs.clear()

    def save_outcome(self, path: Path | str, suffix: str | None, data: dict) -> None:
        """Save outcome data at a path."""
        path = str(path)

        if suffix is None:
            # Winning state - store the actual outcome
            self._outcomes[path] = data
        else:
            # Parent state - update aggregated stats
            if path not in self._outcome_refs:
                self._outcome_refs[path] = {"outcomes": {}, "p1_wins": [], "p2_wins": []}

            # Get first action in suffix
            first_action = suffix[0] if suffix else ""
            winner = data.get("winner", "")

            if first_action not in self._outcome_refs[path]["outcomes"]:
                self._outcome_refs[path]["outcomes"][first_action] = {"p1_wins": 0, "p2_wins": 0}

            if winner == "p1":
                self._outcome_refs[path]["outcomes"][first_action]["p1_wins"] += 1
                self._outcome_refs[path]["p1_wins"].append(suffix)
            elif winner == "p2":
                self._outcome_refs[path]["outcomes"][first_action]["p2_wins"] += 1
                self._outcome_refs[path]["p2_wins"].append(suffix)

    def get_outcomes(self, path: Path | str) -> dict:
        """Get outcomes data at this state."""
        return self._outcome_refs.get(str(path), {"outcomes": {}, "p1_wins": [], "p2_wins": []})

    def get_episode(self, leaf_path: Path | str) -> Episode:
        """
        Build an Episode from root to the given leaf path.

        Walks the path components from root to leaf,
        collecting states, actions, decks, and outcome.

        Args:
            leaf_path: Path to the final state (e.g., "root/3/0/6")

        Returns:
            Episode object ready for serialization
        """
        leaf_path = str(leaf_path)

        # Generate sequence of paths from root to leaf
        # e.g., "root/3/0/6" -> ["root", "root/3", "root/3/0", "root/3/0/6"]
        state_paths = self._path_sequence(leaf_path)

        states = []
        actions = []

        for path in state_paths:
            # Load state graph (need to import state class dynamically or store graphs directly)
            if path not in self._states:
                raise KeyError(f"State not found: {path}")

            graph, deck1_ids, deck2_ids = self._states[path]
            states.append(deepcopy(graph))

            # Get action that led to this state
            action = self._action_taken.get(path, "initial" if path == state_paths[0] else "unknown")
            actions.append(action)

        # Get starting decks from first state
        _, deck1_ids, deck2_ids = self._states[state_paths[0]]

        # Get outcome from leaf
        outcome = self._outcomes.get(leaf_path, {"winner": "unknown", "p1_lore": 0, "p2_lore": 0})

        # Generate game_id from root path name
        root_path = state_paths[0]
        game_id = root_path.split("/")[-1] if "/" in root_path else root_path

        return Episode(
            states=states,
            actions=actions,
            decks=(list(deck1_ids), list(deck2_ids)),
            outcome=outcome,
            game_id=game_id,
            source_path=leaf_path,
        )

    def _path_sequence(self, leaf_path: str) -> list[str]:
        """
        Generate sequence of paths from root to leaf.

        Walks path components and returns only those that have states stored.

        Example:
            "root/3/0/6" with states at root, root/3, root/3/0, root/3/0/6
            -> ["root", "root/3", "root/3/0", "root/3/0/6"]
        """
        parts = leaf_path.split("/")
        paths = []

        for i in range(len(parts)):
            path = "/".join(parts[:i + 1])
            if path in self._states:
                paths.append(path)

        if not paths:
            raise ValueError(f"No states found in path hierarchy: {leaf_path}")

        return paths
