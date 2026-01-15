"""
Compute legal actions (CAN_* edges) from Lorcana game state.

Orchestrates mechanics to compute all legal actions.
"""
import networkx as nx
from lib.lorcana.mechanics.turn import compute_can_pass
from lib.lorcana.mechanics.ink import compute_can_ink
from lib.lorcana.mechanics.play import compute_can_play
from lib.lorcana.mechanics.quest import compute_can_quest
from lib.lorcana.mechanics.challenge import compute_can_challenge

# Base-36 alphabet for compact action IDs (0-9, a-z)
_BASE36_CHARS = "0123456789abcdefghijklmnopqrstuvwxyz"


def _to_base36(n: int) -> str:
    """Convert integer to base-36 string."""
    if n == 0:
        return "0"
    result = []
    while n:
        result.append(_BASE36_CHARS[n % 36])
        n //= 36
    return "".join(reversed(result))


def _clear_can_edges(G: nx.MultiDiGraph) -> None:
    """Remove all existing action edges from the graph."""
    to_remove = []
    for u, v, key, data in G.edges(keys=True, data=True):
        if data.get("action_type"):
            to_remove.append((u, v, key))
    for edge in to_remove:
        G.remove_edge(*edge)


def _add_can_edge(G: nx.MultiDiGraph, src: str, dst: str, action_type: str, action_id: str, description: str) -> str:
    """Add an action edge with sequential action_id and description."""
    key = G.add_edge(src, dst, action_type=action_type, action_id=action_id, description=description)
    return key


def compute_all(G: nx.MultiDiGraph) -> None:
    """Recompute all CAN_* edges from current state."""
    _clear_can_edges(G)

    # Don't compute actions if game is over
    game_over = G.nodes.get('game', {}).get('game_over', '0')
    if game_over == '1':
        return

    # Collect edges from all mechanics
    edges_to_add = []
    edges_to_add.extend(compute_can_pass(G))
    edges_to_add.extend(compute_can_ink(G))
    edges_to_add.extend(compute_can_play(G))
    edges_to_add.extend(compute_can_quest(G))
    edges_to_add.extend(compute_can_challenge(G))
    # TODO: Add other mechanics (activate abilities)

    # Sort deterministically and assign sequential action IDs
    # ActionEdge is a NamedTuple so we can use tuple indexing or named attributes
    sorted_edges = sorted(edges_to_add, key=lambda e: (e.action_type, e.src, e.dst))

    # Add edges with sequential action_ids (base-36 for compactness)
    for idx, edge in enumerate(sorted_edges):
        _add_can_edge(G, edge.src, edge.dst, edge.action_type, action_id=_to_base36(idx), description=edge.description)
