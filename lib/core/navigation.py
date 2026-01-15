"""
Navigation file utilities for game tree exploration.

Manages path.txt and actions.txt files that document game state navigation.
"""
import networkx as nx
from pathlib import Path
from typing import NamedTuple
from lib.core.graph import can_edges, get_edge_attr


class Action(NamedTuple):
    """
    Represents an available action read from the game graph.

    Created by format_actions after action_id has been assigned.
    """
    id: str
    action_type: str
    src: str
    dst: str
    description: str


def format_actions(G: nx.MultiDiGraph) -> list[Action]:
    """
    Format action edges into list of Action objects.

    Reads from graph edges that have action_type set.

    Returns:
        List of Action objects sorted by (action_type, src, dst)
    """
    actions = []
    # Sort edges by action_type for deterministic ordering
    sorted_edges = sorted(can_edges(G), key=lambda e: (e[3], e[0], e[1]))  # (action_type, from, to)

    for u, v, key, action_type, action_id in sorted_edges:
        description = get_edge_attr(G, u, v, key, "description", action_type.lower())
        actions.append(Action(
            id=action_id,
            action_type=action_type,
            src=u,
            dst=v,
            description=description,
        ))
    return actions


def write_actions_file(path: Path, actions: list[Action]) -> None:
    """
    Write actions.txt showing available actions from this state.

    Args:
        path: Current state directory
        actions: List of Action objects
    """
    path.mkdir(parents=True, exist_ok=True)
    with open(path / "actions.txt", 'w') as f:
        for action in actions:
            f.write(f"{action.id}: {action.description}\n")


def read_actions_file(path: Path) -> list[dict]:
    """
    Read actions.txt and return list of action dicts.

    Args:
        path: Directory containing actions.txt

    Returns:
        List of dicts with 'id' and 'description' keys
    """
    actions = []
    actions_file = Path(path) / "actions.txt"

    if not actions_file.exists():
        return actions

    with open(actions_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Parse "id: description" format
            if ':' in line:
                action_id, description = line.split(':', 1)
                actions.append({
                    'id': action_id.strip(),
                    'description': description.strip()
                })

    return actions
