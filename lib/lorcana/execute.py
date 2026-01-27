"""
Execute actions on Lorcana game state.

Applies mutations to the graph based on action types.
Routes to specific mechanic implementations.
"""
import sys
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
