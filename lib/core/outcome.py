"""
Outcome backpropagation for completed games.

Generic tree-walking logic that calls a callback at each parent level.
"""
import re


def backpropagate(winning_path: str, stop_at: str, on_level) -> None:
    """
    Walk up the tree from winning state, calling on_level at each parent.

    Args:
        winning_path: Path to the winning state
        stop_at: Path to stop at (inclusive)
        on_level: Callback fn(parent_path, suffix) called at each level
                  suffix is action path like "0.1.2"
    """
    action_path = []
    current = winning_path

    while current != stop_at and '/' in current:
        parent, action = current.rsplit('/', 1)

        if not parent:
            break

        action_path.insert(0, action)
        suffix = "".join(action_path)

        on_level(parent, suffix)

        if parent == stop_at:
            break

        current = parent


def find_seed_path(path: str) -> str | None:
    """
    Find the seed directory portion of a path.

    Seed formats:
    - Hand-spec: xxxxxxx.xxxxxxx.xx (e.g., b123456.0123456.ab)
    - Simple: 8 alphanumeric chars (e.g., xzp8iq8p)

    Returns:
        Path up to and including seed dir, or None if not found
    """
    parts = path.split('/')

    for i, part in enumerate(parts):
        # Hand-spec format
        if re.match(r'^[a-z0-9]{7}\.[a-z0-9]{7}\.[a-z]{2}$', part):
            return '/'.join(parts[:i + 1])
        # Simple format (8 alphanumeric, no dots, not a single digit action)
        if re.match(r'^[a-z0-9]{8}$', part):
            return '/'.join(parts[:i + 1])

    return None
