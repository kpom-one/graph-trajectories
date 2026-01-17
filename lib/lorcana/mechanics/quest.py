"""
Quest mechanic.

Compute when characters can quest, and execute the quest action.
"""
import networkx as nx
from lib.core.graph import get_node_attr
from lib.lorcana.constants import Zone, Action, CardType, Edge
from lib.lorcana.helpers import ActionEdge, get_game_context, get_card_data, cards_in_zone, has_edge


def compute_can_quest(G: nx.MultiDiGraph) -> list[ActionEdge]:
    """Return Action.QUEST edges for characters that can quest."""
    result = []

    # Get game context
    ctx = get_game_context(G)
    if not ctx:
        return result

    # Find cards in play
    cards_in_play = cards_in_zone(G, ctx['player'], Zone.PLAY)

    # Check each card for quest eligibility
    for card_node in cards_in_play:
        card_data = get_card_data(G, card_node)

        # Only characters can quest (4.3.5.1)
        if card_data['type'] != CardType.CHARACTER:
            continue

        # Must be ready (not exerted) - questing requires exerting (4.3.5.7)
        # Note: 0-lore characters CAN quest, they just gain 0 lore
        if get_node_attr(G, card_node, 'exerted', '0') == '1':
            continue

        # Must be dry (entered play before this turn)
        entered_play = int(get_node_attr(G, card_node, 'entered_play', '-1'))
        if entered_play == ctx['current_turn']:
            continue

        # Check for CANT_QUEST edge (e.g., from Reckless keyword)
        if has_edge(G, card_node, Edge.CANT_QUEST):
            continue

        result.append(ActionEdge(
            src=card_node,
            dst=ctx['player'],
            action_type=Action.QUEST,
            description=f"quest:{card_node}"
        ))

    return result


def execute_quest(state, from_node: str, to_node: str) -> None:
    """Execute quest action: exert card, add lore to player."""
    # Exert the card
    state.graph.nodes[from_node]['exerted'] = '1'

    # Get lore value and add to player (checks win condition)
    card_data = get_card_data(state.graph, from_node)
    lore_value = card_data['lore']
    state.add_lore(to_node, lore_value)
