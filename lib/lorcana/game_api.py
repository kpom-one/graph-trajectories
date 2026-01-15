"""
Python API for playing Lorcana games in-memory.

Provides high-level game operations without filesystem I/O.
Uses MemoryStore for fast state management.
"""
import random
from pathlib import Path
from lib.core.store import StateStore
from lib.core.memory_store import MemoryStore
from lib.core.file_store import FileStore
from lib.core.graph import can_edges, get_node_attr, get_edge_attr
from lib.core.outcome import backpropagate, find_seed_path
from lib.lorcana.state import LorcanaState
from lib.lorcana.execute import execute_action
from lib.core.navigation import format_actions, Action


class GameSession:
    """
    In-memory game session.

    Manages game state and provides clean API for playing.
    No filesystem I/O - all operations in memory.
    """

    def __init__(self, initial_state: LorcanaState, store: StateStore = None, root_key: str = "root"):
        """
        Create game session from initial state.

        Args:
            initial_state: Starting game state
            store: Storage backend (defaults to MemoryStore)
            root_key: Key/path for root state (defaults to "root")
        """
        self.store = store or MemoryStore()
        self.root_key = root_key
        self.current_key = self.root_key

        # Save initial state
        self.store.save_state(initial_state, self.root_key, format_actions_fn=format_actions, action_taken="initial")

    @classmethod
    def from_file(cls, path: Path | str, store: StateStore = None):
        """
        Create session from existing file-based state.

        Args:
            path: Path to state directory
            store: Storage backend (defaults to MemoryStore)

        Returns:
            GameSession instance
        """
        path = Path(path)
        store = store or MemoryStore()
        file_store = FileStore()
        state = file_store.load_state(path, LorcanaState)
        return cls(state, store=store, root_key=str(path))

    def get_state(self) -> LorcanaState:
        """Get current game state."""
        return self.store.load_state(self.current_key, LorcanaState)

    def get_actions(self) -> list[Action]:
        """
        Get available actions from current state.

        Returns:
            List of Action objects
        """
        state = self.get_state()
        return format_actions(state.graph)

    def apply_action(self, action_id: str) -> bool:
        """
        Apply action by ID, advancing to new state.

        Args:
            action_id: Action ID to apply (e.g., "0", "1", "2")

        Returns:
            True if action was applied, False if action not found

        Mutates: Updates current_key to point to new state
        """
        state = self.get_state()

        # Find matching action
        for u, v, key, action_type, edge_action_id in can_edges(state.graph):
            if edge_action_id == action_id:
                # Get description before executing (edge will be removed)
                action_desc = get_edge_attr(state.graph, u, v, key, "description", f"{action_type}:{u}")

                # Execute action (mutates state)
                execute_action(state, action_type, u, v)

                # Save to new key
                new_key = f"{self.current_key}/{action_id}"
                self.store.save_state(state, new_key, format_actions_fn=format_actions, action_taken=action_desc)

                # Update current position
                self.current_key = new_key

                # If game is over, save outcome and backpropagate
                if get_node_attr(state.graph, 'game', 'game_over', '0') == '1':
                    outcome_data = {
                        'winner': get_node_attr(state.graph, 'game', 'winner', None),
                        'p1_lore': int(get_node_attr(state.graph, 'p1', 'lore', '0')),
                        'p2_lore': int(get_node_attr(state.graph, 'p2', 'lore', '0')),
                    }

                    self.store.save_outcome(new_key, None, outcome_data)

                    seed_path = find_seed_path(new_key)
                    if seed_path:
                        backpropagate(new_key, seed_path,
                            lambda parent, suffix: self.store.save_outcome(parent, suffix, outcome_data))

                return True

        return False

    def is_game_over(self) -> bool:
        """Check if current game is over."""
        state = self.get_state()
        return get_node_attr(state.graph, 'game', 'game_over', '0') == '1'

    def get_winner(self) -> str | None:
        """
        Get winner if game is over.

        Returns:
            Winner player node ("p1" or "p2"), or None if no winner yet
        """
        if not self.is_game_over():
            return None
        state = self.get_state()
        return get_node_attr(state.graph, 'game', 'winner', None)

    def get_path(self) -> str:
        """Get current path from root."""
        if self.current_key == self.root_key:
            return ""
        return self.current_key[len(self.root_key):]

    def reset(self):
        """Reset to initial state."""
        self.current_key = self.root_key

    def goto(self, key: str):
        """Jump to a previously computed state."""
        self.current_key = key

    def play_random_action(self, prefer_non_end: bool = True) -> bool:
        """
        Play a random action from current state.

        Args:
            prefer_non_end: If True, only choose 'end' if no other actions available

        Returns:
            True if action was played, False if no actions available
        """
        actions = self.get_actions()
        if not actions:
            return False

        # Filter non-end actions if preference set
        if prefer_non_end:
            non_end = [a for a in actions if a.description != 'end']
            if non_end:
                actions = non_end

        # Pick random action
        action = random.choice(actions)
        return self.apply_action(action.id)

    def play_until_game_over(self, prefer_non_end: bool = True, max_actions: int = 1000) -> str:
        """
        Play random actions until game ends.

        Args:
            prefer_non_end: Prefer non-end actions when available
            max_actions: Maximum actions to prevent infinite loops

        Returns:
            Path to final state (e.g., "/0/3/1/2")
        """
        for _ in range(max_actions):
            if self.is_game_over():
                break
            if not self.play_random_action(prefer_non_end):
                break

        return self.get_path()
