"""
Challenge mechanic.

Compute when characters can challenge, and execute the challenge action.
"""
import networkx as nx
from lib.core.graph import get_node_attr
from lib.lorcana.cards import get_strength
from lib.lorcana.constants import Zone, Action, Keyword, CardType
from lib.lorcana.helpers import ActionEdge, get_game_context, get_card_data, cards_in_zone, has_keyword


def compute_can_challenge(G: nx.MultiDiGraph) -> list[ActionEdge]:
    """Return Action.CHALLENGE edges for valid challenges."""
    result = []

    # Get game context
    ctx = get_game_context(G)
    if not ctx:
        return result

    # Find characters in current player's play zone (potential challengers)
    cards_in_play = cards_in_zone(G, ctx['player'], Zone.PLAY)

    # Find exerted characters in opponent's play zone (potential targets)
    opponent_cards = cards_in_zone(G, ctx['opponent'], Zone.PLAY)

    # Check each potential challenger
    for challenger in cards_in_play:
        card_data = get_card_data(G, challenger)

        # Only characters can challenge (4.3.6.1)
        if card_data['type'] != CardType.CHARACTER:
            continue

        # Must be ready (4.3.6.6: "ready, and otherwise able to challenge")
        # Note: 0-strength characters CAN challenge, they just deal 0 damage
        if get_node_attr(G, challenger, 'exerted', '0') == '1':
            continue

        # Must be dry (entered play before this turn) OR have Rush
        entered_play = int(get_node_attr(G, challenger, 'entered_play', '-1'))
        is_drying = entered_play == ctx['current_turn']
        if is_drying and not has_keyword(G, challenger, Keyword.RUSH):
            continue

        # Find valid targets (exerted opposing characters)
        for defender in opponent_cards:
            defender_data = get_card_data(G, defender)

            # Only characters can be challenged
            if defender_data['type'] != CardType.CHARACTER:
                continue

            # Must be exerted to be challenged
            if get_node_attr(G, defender, 'exerted', '0') != '1':
                continue

            # Evasive check: if defender has Evasive, attacker must have Evasive or Alert
            if has_keyword(G, defender, Keyword.EVASIVE):
                if not has_keyword(G, challenger, Keyword.EVASIVE) and not has_keyword(G, challenger, Keyword.ALERT):
                    continue

            # Valid challenge!
            result.append(ActionEdge(
                src=challenger,
                dst=defender,
                action_type=Action.CHALLENGE,
                description=f"challenge:{challenger}->{defender}"
            ))

    return result


def execute_challenge(state, attacker: str, defender: str) -> None:
    """Execute challenge action: exert attacker, deal damage, check for banish."""
    # 1. Exert the attacker
    state.graph.nodes[attacker]['exerted'] = '1'

    # 2. Get strength values for both characters
    attacker_strength = get_strength(state, attacker)
    defender_strength = get_strength(state, defender)

    # 3. Deal damage simultaneously
    state.damage_card(defender, attacker_strength)
    state.damage_card(attacker, defender_strength)
