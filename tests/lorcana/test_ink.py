"""
Ink Mechanic Tests
==================

These tests verify the rules for inking cards as defined in the
Disney Lorcana Comprehensive Rules, Section 4.3.3.

WHAT IS INKING?
---------------
Inking is how you build your resources. Once per turn, you can put a card
from your hand into your "inkwell" facedown. That card becomes 1 ink you
can spend to play other cards.

Not all cards can be inked - only cards with the inkwell symbol around
their cost can be added to your inkwell.

OFFICIAL RULES REFERENCE
------------------------
4.3.3. "Put a card into the inkwell. This turn action is limited to once per turn."

4.3.3.1. "The player declares they're putting a card into their inkwell, then chooses
         and reveals a card from their hand with the inkwell symbol. All players verify
         that the inkwell symbol is present."

4.3.3.2. "The player places the revealed card in their inkwell facedown and ready."
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.lorcana.conftest import make_game, add_character, make_state, ZONE_HAND, ZONE_INK
from lib.lorcana.mechanics.ink import compute_can_ink, execute_ink


# =============================================================================
# BASIC INKING
# =============================================================================

class TestBasicInking:
    """
    You can ink a card if:
    1. The card is in your hand
    2. The card has the inkwell symbol (inkwell=True in card data)
    3. You haven't inked yet this turn (ink_drops > 0)
    """

    def test_can_ink_inkable_card_in_hand(self):
        """
        SCENARIO: Can ink a card that has the inkwell symbol.

        SETUP:
        - Player has an inkable card in hand
        - Player hasn't inked this turn (ink_drops = 1)

        EXPECTED:
        - Ink action is available for that card

        RULE: 4.3.3.1 - "chooses and reveals a card from their hand with the inkwell symbol"
        """
        G = make_game()
        # Stitch - Rock Star has inkwell=True
        stitch = add_character(G, 'p1', 'stitch_rock_star', zone=ZONE_HAND)

        actions = compute_can_ink(G)

        assert len(actions) == 1
        assert actions[0].src == stitch

    def test_inking_moves_card_to_inkwell(self):
        """
        SCENARIO: Inking a card moves it from hand to inkwell.

        SETUP:
        - Card is in hand
        - Player inks it

        EXPECTED:
        - Card is now in ink zone
        - ink_total increases by 1
        - ink_available increases by 1
        - ink_drops decreases by 1 (can't ink again this turn)

        RULE: 4.3.3.2 - "The player places the revealed card in their inkwell"
        """
        G = make_game()
        stitch = add_character(G, 'p1', 'stitch_rock_star', zone=ZONE_HAND)
        state = make_state(G)

        execute_ink(state, stitch)

        assert G.nodes[stitch]['zone'] == ZONE_INK, "Card should be in inkwell"
        assert G.nodes['p1']['ink_total'] == '1', "Ink total should increase"
        assert G.nodes['p1']['ink_available'] == '1', "Ink available should increase"
        assert G.nodes['p1']['ink_drops'] == '0', "Ink drops should decrease (can't ink again)"


# =============================================================================
# ONCE PER TURN RESTRICTION
# =============================================================================

class TestOncePerTurn:
    """
    You can only ink ONE card per turn.
    This is tracked by the ink_drops counter.
    """

    def test_cannot_ink_twice_in_one_turn(self):
        """
        SCENARIO: After inking once, cannot ink again this turn.

        SETUP:
        - Player has two inkable cards in hand
        - Player has already inked (ink_drops = 0)

        EXPECTED:
        - No ink actions available

        RULE: 4.3.3 - "This turn action is limited to once per turn."
        """
        G = make_game()
        G.nodes['p1']['ink_drops'] = '0'  # Already used ink drop

        add_character(G, 'p1', 'stitch_rock_star', zone=ZONE_HAND)
        add_character(G, 'p1', 'simba_protective_cub', zone=ZONE_HAND)

        actions = compute_can_ink(G)

        assert len(actions) == 0, "Cannot ink when ink_drops is 0"

    def test_multiple_inkable_cards_all_available(self):
        """
        SCENARIO: If you have multiple inkable cards, you can choose any one.

        SETUP:
        - Player has 3 inkable cards in hand
        - Player hasn't inked this turn

        EXPECTED:
        - 3 ink actions available (one per card)
        """
        G = make_game()

        add_character(G, 'p1', 'stitch_rock_star', zone=ZONE_HAND)
        add_character(G, 'p1', 'simba_protective_cub', zone=ZONE_HAND)
        add_character(G, 'p1', 'moana_of_motunui', zone=ZONE_HAND)

        actions = compute_can_ink(G)

        # All three characters have inkwell=True
        assert len(actions) == 3, "Should have ink option for each inkable card"


# =============================================================================
# NON-INKABLE CARDS
# =============================================================================

class TestNonInkableCards:
    """
    Some cards cannot be inked - they don't have the inkwell symbol.
    These are typically powerful cards that would be too easy to
    "throw away" as ink.
    """

    def test_cannot_ink_non_inkable_card(self):
        """
        SCENARIO: Cards without inkwell symbol cannot be inked.

        SETUP:
        - Player has a card without inkwell=True in hand
        - Player hasn't inked this turn

        EXPECTED:
        - No ink actions available for that card

        RULE: 4.3.3.1 - Must be "a card from their hand with the inkwell symbol"
        """
        G = make_game()
        # Hades - King of Olympus does NOT have inkwell (it's a powerful 8-cost card)
        hades = add_character(G, 'p1', 'hades_king_of_olympus', zone=ZONE_HAND)

        actions = compute_can_ink(G)

        # Should not be able to ink Hades
        inkable_cards = [a.src for a in actions]
        assert hades not in inkable_cards, "Non-inkable card should not have ink action"
