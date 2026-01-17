"""
Execute actions on Lorcana game state.

Applies mutations to the graph based on action types.
Routes to specific mechanic implementations.
"""
from pathlib import Path
import sys
from lib.core.graph import can_edges, get_node_attr, get_edge_attr
from lib.core.navigation import format_actions
from lib.core.file_store import FileStore
from lib.core.outcome import backpropagate, find_seed_path
from lib.lorcana.state import LorcanaState
from lib.lorcana.compute import compute_all
from lib.lorcana.mechanics.turn import advance_turn
from lib.lorcana.mechanics.ink import execute_ink
from lib.lorcana.mechanics.play import execute_play
from lib.lorcana.mechanics.quest import execute_quest
from lib.lorcana.mechanics.challenge import execute_challenge
from lib.lorcana.state_based_effects import check_state_based_effects
from lib.lorcana.constants import Action


def execute_action(state: LorcanaState, action_type: str, from_node: str, to_node: str, metadata: dict | None = None) -> None:
    """Execute an action, mutating the state."""
    metadata = metadata or {}
    if action_type == Action.PASS:
        advance_turn(state, from_node, to_node)
    elif action_type == Action.INK:
        execute_ink(state, from_node)
    elif action_type == Action.PLAY:
        execute_play(state, from_node, to_node, metadata)
    elif action_type == Action.QUEST:
        execute_quest(state, from_node, to_node)
    elif action_type == Action.CHALLENGE:
        execute_challenge(state, from_node, to_node)
    else:
        print(f"TODO: Implement {action_type}", file=sys.stderr)

    # Check state-based effects (banish damaged characters, etc.)
    check_state_based_effects(state)

    # Recompute legal actions after any mutation
    compute_all(state.graph)


def apply_action_at_path(path: Path) -> None:
    """
    Apply the action represented by this directory.

    Recursively ensures all parent states exist before applying this action.
    """
    path = Path(path)
    store = FileStore()

    # If state already exists, nothing to do
    if store.state_exists(path):
        return

    # Recursively ensure parent exists
    parent_path = path.parent
    if parent_path != path and not store.state_exists(parent_path):
        apply_action_at_path(parent_path)

    # Now apply this action
    action_id = path.name

    # Load parent state
    parent = store.load_state(parent_path, LorcanaState)

    # Find the action edge that matches this ID
    action_found = False
    action_desc = None
    for u, v, key, action_type, edge_action_id in can_edges(parent.graph):
        if edge_action_id == action_id:
            # Get description before applying (edge will be removed)
            action_desc = get_edge_attr(parent.graph, u, v, key, "description", f"{action_type}:{u}")
            # Collect metadata from edge (non-standard attributes)
            edge_data = parent.graph.edges[u, v, key]
            metadata = {k: v for k, v in edge_data.items() if k not in ('action_type', 'action_id', 'description')}
            # Apply the action (mutates parent.graph)
            execute_action(parent, action_type, u, v, metadata)
            action_found = True
            break

    if not action_found:
        raise ValueError(f"Action {action_id} not found in parent state")

    # Save new state at action path
    store.save_state(parent, path, format_actions_fn=format_actions, action_taken=action_desc)

    # If game is over, write outcome and backpropagate
    if get_node_attr(parent.graph, 'game', 'game_over', '0') == '1':
        outcome_data = {
            'winner': get_node_attr(parent.graph, 'game', 'winner', None),
            'p1_lore': int(get_node_attr(parent.graph, 'p1', 'lore', '0')),
            'p2_lore': int(get_node_attr(parent.graph, 'p2', 'lore', '0')),
        }

        # Save at winning state
        store.save_outcome(str(path), None, outcome_data)

        # Backpropagate up to seed directory
        seed_path = find_seed_path(str(path))
        if seed_path:
            backpropagate(str(path), seed_path,
                lambda parent, suffix: store.save_outcome(parent, suffix, outcome_data))
