"""
Ink card mechanic.

Compute when cards can be inked, and execute the ink action.
"""
import networkx as nx
from lib.core.graph import get_node_attr
from lib.lorcana.constants import Zone, Action
from lib.lorcana.helpers import ActionEdge, get_game_context, get_card_data, cards_in_zone


def compute_can_ink(G: nx.MultiDiGraph) -> list[ActionEdge]:
    """Return Action.INK edges for inkable cards in current player's hand."""
    result = []

    # Get game context
    ctx = get_game_context(G)
    if not ctx:
        return result

    # Check ink_drops > 0
    ink_drops = int(get_node_attr(G, ctx['player'], 'ink_drops', 0))
    if ink_drops <= 0:
        return result

    # Find cards in hand
    cards_in_hand = cards_in_zone(G, ctx['player'], Zone.HAND)

    # Check each card for inkwell property
    for card_node in cards_in_hand:
        card_data = get_card_data(G, card_node)
        if card_data.get('inkwell', False):
            result.append(ActionEdge(
                src=card_node,
                dst=ctx['player'],
                action_type=Action.INK,
                description=f"ink:{card_node}"
            ))

    return result


def execute_ink(state, from_node: str) -> None:
    """Execute ink action: move card to inkwell, update ink tracking."""
    # Move card from hand to inkwell
    state.move_card(from_node, Zone.INK)

    # Get game context
    ctx = get_game_context(state.graph)

    # Decrement ink_drops
    ink_drops = int(get_node_attr(state.graph, ctx['player'], 'ink_drops', 1))
    state.graph.nodes[ctx['player']]['ink_drops'] = str(ink_drops - 1)

    # Increment ink_total and ink_available
    ink_total = int(get_node_attr(state.graph, ctx['player'], 'ink_total', 0))
    state.graph.nodes[ctx['player']]['ink_total'] = str(ink_total + 1)
    ink_available = int(get_node_attr(state.graph, ctx['player'], 'ink_available', 0))
    state.graph.nodes[ctx['player']]['ink_available'] = str(ink_available + 1)
