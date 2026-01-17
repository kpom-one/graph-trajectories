"""
Play card mechanic.

Compute when cards can be played, and execute the play action.
"""
import networkx as nx
from lib.core.graph import get_node_attr
from lib.lorcana.constants import Zone, Action, CardType
from lib.lorcana.helpers import ActionEdge, get_game_context, get_card_data, cards_in_zone, card_data_has_keyword
from lib.lorcana.abilities import create_printed_abilities


def compute_can_play(G: nx.MultiDiGraph) -> list[ActionEdge]:
    """Return Action.PLAY edges for playable cards in current player's hand."""
    result = []

    # Get game context
    ctx = get_game_context(G)
    if not ctx:
        return result

    # Get ink_available
    ink_available = int(get_node_attr(G, ctx['player'], 'ink_available', 0))

    # Find cards in hand
    cards_in_hand = cards_in_zone(G, ctx['player'], Zone.HAND)

    # Check each card for playability
    for card_node in cards_in_hand:
        card_data = get_card_data(G, card_node)
        cost = card_data.get('cost', 0)

        if ink_available >= cost:
            # Normal play option
            result.append(ActionEdge(
                src=card_node,
                dst=ctx['player'],
                action_type=Action.PLAY,
                description=f"play:{card_node}"
            ))

            # Bodyguard cards can also enter play exerted
            if card_data_has_keyword(card_data, 'Bodyguard'):
                result.append(ActionEdge(
                    src=card_node,
                    dst=ctx['player'],
                    action_type=Action.PLAY,
                    description=f"play:{card_node}:exerted",
                    metadata={'exerted': True}
                ))

    return result


def execute_play(state, from_node: str, to_node: str, metadata: dict | None = None) -> None:
    """Execute play action: move card to play/discard, spend ink, track entered_play turn."""
    metadata = metadata or {}

    # Get card data and game context
    card_data = get_card_data(state.graph, from_node)
    ctx = get_game_context(state.graph)

    # Determine destination zone based on card type
    zone = Zone.DISCARD if card_data['type'] == CardType.ACTION else Zone.PLAY

    # Move card from hand to play/discard
    state.move_card(from_node, zone)

    # Spend ink
    cost = card_data['cost']
    ink_available = int(get_node_attr(state.graph, ctx['player'], 'ink_available', 0))
    state.graph.nodes[ctx['player']]['ink_available'] = str(ink_available - cost)

    # If card entered play zone (not discard), track the turn and create abilities
    if zone == Zone.PLAY:
        state.graph.nodes[from_node]['entered_play'] = str(ctx['current_turn'])
        # Bodyguard can enter play exerted
        state.graph.nodes[from_node]['exerted'] = '1' if metadata.get('exerted') else '0'

        # Create ability nodes for printed keywords
        create_printed_abilities(state.graph, from_node, card_data, ctx['current_turn'])


