"""
State-based effects.

Checks and resolves state-based effects after each action.
"""
from lib.core.graph import get_node_attr
from lib.lorcana.cards import get_willpower
from lib.lorcana.constants import Zone, CardType
from lib.lorcana.helpers import get_card_data, cards_in_zone


def check_state_based_effects(state) -> None:
    """
    Check and resolve state-based effects.

    Currently handles:
    - Banish characters with damage >= willpower
    """
    check_and_banish_damaged_characters(state)


def check_and_banish_damaged_characters(state) -> None:
    """Check all characters in play and banish those with lethal damage."""
    cards_to_banish = []

    # Check both players' play zones
    for player in ['p1', 'p2']:
        for card_node in cards_in_zone(state.graph, player, Zone.PLAY):
            card_data = get_card_data(state.graph, card_node)

            # Only check characters
            if card_data['type'] != CardType.CHARACTER:
                continue

            # Only check if card has damage
            damage = int(get_node_attr(state.graph, card_node, 'damage', '0'))
            if damage == 0:
                continue

            # Check damage vs willpower
            willpower = get_willpower(state, card_node)

            if damage >= willpower:
                cards_to_banish.append(card_node)

    # Banish all marked cards
    for card_node in cards_to_banish:
        state.move_card(card_node, Zone.DISCARD)
