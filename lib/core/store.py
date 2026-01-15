"""
Abstract interface for state storage.

Defines contract for loading/saving game states.
Implementations: FileStore (DOT files), MemoryStore (dict-based).
"""
from abc import ABC, abstractmethod
from pathlib import Path


class StateStore(ABC):
    """Abstract base class for state storage backends."""

    @abstractmethod
    def load_state(self, path: Path | str, state_class):
        """
        Load game state from storage.

        Args:
            path: Identifier for the state (file path or key)
            state_class: Class to instantiate (e.g., LorcanaState)

        Returns:
            Loaded state instance

        Raises:
            KeyError or FileNotFoundError: If state doesn't exist
        """
        pass

    @abstractmethod
    def save_state(self, state, path: Path | str, format_actions_fn=None, action_taken: str | None = None):
        """
        Save game state to storage.

        Args:
            state: State object with graph, deck1_ids, deck2_ids attributes
            path: Identifier for where to save (file path or key)
            format_actions_fn: Optional function to format actions for navigation
            action_taken: Description of action that led to this state (for diff header)
        """
        pass

    @abstractmethod
    def state_exists(self, path: Path | str) -> bool:
        """
        Check if state exists in storage.

        Args:
            path: Identifier for the state

        Returns:
            True if state exists, False otherwise
        """
        pass

    @abstractmethod
    def get_actions(self, path: Path | str) -> list[dict]:
        """
        Get available actions for a state.

        Args:
            path: Identifier for the state

        Returns:
            List of action dicts with 'id' and 'description' keys
        """
        pass

    @abstractmethod
    def save_outcome(self, path: Path | str, suffix: str | None, data: dict) -> None:
        """
        Save outcome data at a path.

        Args:
            path: Identifier for the state
            suffix: Action-path suffix (e.g., "0.1.2") or None for winning state
            data: Outcome data dict (winner, p1_lore, p2_lore)
        """
        pass

    def get_outcomes(self, path: Path | str) -> dict:
        """
        Get outcomes data at this state.

        Args:
            path: Identifier for the state

        Returns:
            Dict with 'outcomes' (per-action stats), 'p1_wins', 'p2_wins' (path lists)
        """
        return {"outcomes": {}, "p1_wins": [], "p2_wins": []}
