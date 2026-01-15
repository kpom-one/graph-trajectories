"""
Turn structure mechanic.

Handles turn phases and player switching.
Steps: ready -> set -> draw -> main -> end
"""
import networkx as nx
from lib.core.graph import edges_by_label, get_node_attr
from lib.lorcana.helpers import ActionEdge, get_game_context, get_player_step, cards_in_zone, ZONE_PLAY


def compute_can_pass(G: nx.MultiDiGraph) -> list[ActionEdge]:
    """Return CAN_PASS edge for current player during main step."""
    ctx = get_game_context(G)

    # Find current step via CURRENT_STEP edge
    current_step_edges = edges_by_label(G, "CURRENT_STEP")
    if not current_step_edges or not ctx:
        return []

    _, current_step_node, _ = current_step_edges[0]

    # Can only pass during main step
    step_type = get_node_attr(G, current_step_node, 'step', '')
    if step_type == 'main':
        return [ActionEdge(
            src=ctx['player'],
            dst='game',
            action_type="CAN_PASS",
            description="end"
        )]
    return []


def advance_turn(state, from_node: str, to_node: str) -> None:
    """
    Advance turn through steps: main -> end -> (switch) -> ready -> set -> draw -> main.

    Called when player passes during main step.
    Moves CURRENT_STEP edge through step sequence.
    """
    # Get current player
    turn_edges = edges_by_label(state.graph, "CURRENT_TURN")
    if not turn_edges:
        return

    game, current_player, turn_key = turn_edges[0]
    other_player = "p2" if current_player == "p1" else "p1"

    # Sequence: p1.main -> p1.end -> [switch] -> p2.ready -> p2.set -> p2.draw -> p2.main

    # Move to end step
    _move_to_step(state, get_player_step(current_player, 'end'))
    _end_step(state, current_player)

    # Switch players
    state.graph.remove_edge(game, current_player, turn_key)
    state.graph.add_edge(game, other_player, label="CURRENT_TURN")
    turn = int(get_node_attr(state.graph, 'game', 'turn', 0))
    state.graph.nodes['game']['turn'] = str(turn + 1)

    # Move through new player's steps: ready -> set -> draw -> main
    _move_to_step(state, get_player_step(other_player, 'ready'))
    _ready_step(state, other_player)

    _move_to_step(state, get_player_step(other_player, 'set'))
    _set_step(state, other_player)

    _move_to_step(state, get_player_step(other_player, 'draw'))
    _draw_step(state, other_player)

    _move_to_step(state, get_player_step(other_player, 'main'))


def _move_to_step(state, step_node: str) -> None:
    """Move CURRENT_STEP edge to a new step node."""
    # Remove old CURRENT_STEP edge
    step_edges = edges_by_label(state.graph, "CURRENT_STEP")
    if step_edges:
        game, old_step, key = step_edges[0]
        state.graph.remove_edge(game, old_step, key)

    # Add new CURRENT_STEP edge
    state.graph.add_edge('game', step_node, label="CURRENT_STEP")


def _end_step(state, player: str) -> None:
    """End of turn step. Currently does nothing."""
    pass


def _ready_step(state, player: str) -> None:
    """Ready step: Ready all cards in play for the new active player."""
    for card_node in cards_in_zone(state.graph, player, ZONE_PLAY):
        state.graph.nodes[card_node]['exerted'] = '0'


def _set_step(state, player: str) -> None:
    """Set step: Refill ink and reset ink drops."""
    # Give player 1 ink drop for this turn
    state.graph.nodes[player]['ink_drops'] = '1'

    # Refresh ink_available to match ink_total
    ink_total = int(get_node_attr(state.graph, player, 'ink_total', 0))
    state.graph.nodes[player]['ink_available'] = str(ink_total)


def _draw_step(state, player: str) -> None:
    """Draw step: Draw 1 card (skip on first turn for starting player)."""
    turn = int(get_node_attr(state.graph, 'game', 'turn', 0))

    # Starting player (p1) doesn't draw on turn 1
    if player == "p1" and turn == 1:
        return

    # Check if deck is empty before drawing
    player_num = 1 if player == "p1" else 2
    deck = state.deck1_ids if player_num == 1 else state.deck2_ids

    if len(deck) == 0:
        # Lose by deck-out
        other_player = "p2" if player == "p1" else "p1"
        state.graph.nodes['game']['winner'] = other_player
        state.graph.nodes['game']['game_over'] = '1'
        return

    # Draw 1 card
    state.draw(player_num, count=1)
