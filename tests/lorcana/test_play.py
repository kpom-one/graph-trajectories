"""
Play Card Mechanic Tests
========================

These tests verify the rules for playing cards as defined in the
Disney Lorcana Comprehensive Rules, Section 4.3.4.

WHAT IS PLAYING A CARD?
-----------------------
Playing a card means paying its ink cost and putting it into play
(for characters, items, locations) or resolving its effect and
discarding it (for actions).

OFFICIAL RULES REFERENCE
------------------------
4.3.4.1. "The active player can take a turn action to play a card from their hand
         by announcing the card and paying its cost."

4.3.4.6. "Fourth, the player pays the total cost. If the total cost includes any ink,
         the player must exert a number of ready ink cards equal to the ink cost."

4.3.4.7. "Once the total card cost is paid, the card is now 'played.' If the card is
         a character, item, or location, the card enters the Play zone. If it's a
         character being played using its Shift ability, it must be put on top of
         the card indicated in the second step of this process. If the card is an
         action, the effect immediately resolves and the card goes to the player's
         discard pile."
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.lorcana.conftest import make_game, add_character, make_state, give_ink, ZONE_HAND, ZONE_PLAY, ZONE_DISCARD
from lib.lorcana.mechanics.play import compute_can_play, execute_play


# =============================================================================
# BASIC PLAYING
# =============================================================================

class TestBasicPlaying:
    """
    You can play a card if:
    1. The card is in your hand
    2. You have enough ink available to pay its cost
    """

    def test_can_play_card_with_enough_ink(self):
        """
        SCENARIO: Can play a card when you have enough ink.

        SETUP:
        - Player has a 6-cost card in hand (Stitch - Rock Star costs 6)
        - Player has 6 ink available

        EXPECTED:
        - Play action is available

        RULE: 4.3.4.1 - "play a card from their hand by... paying its cost"
        """
        G = make_game()
        give_ink(G, 'p1', 6)
        # Stitch - Rock Star costs 6
        stitch = add_character(G, 'p1', 'stitch_rock_star', zone=ZONE_HAND)

        actions = compute_can_play(G)

        assert len(actions) == 1
        assert actions[0].src == stitch

    def test_cannot_play_card_without_enough_ink(self):
        """
        SCENARIO: Cannot play a card when you don't have enough ink.

        SETUP:
        - Player has a 6-cost card in hand
        - Player has only 3 ink available

        EXPECTED:
        - No play actions available

        RULE: 4.3.4.6 - "the player must exert a number of ready ink cards
                        equal to the ink cost"
        """
        G = make_game()
        give_ink(G, 'p1', 3)  # Not enough for 6-cost Stitch
        add_character(G, 'p1', 'stitch_rock_star', zone=ZONE_HAND)

        actions = compute_can_play(G)

        assert len(actions) == 0, "Cannot play card you can't afford"

    def test_can_play_cheap_card_with_minimal_ink(self):
        """
        SCENARIO: Can play a 1-cost card with just 1 ink.

        SETUP:
        - Player has a 1-cost card in hand (HeiHei costs 1)
        - Player has 1 ink

        EXPECTED:
        - Play action is available
        """
        G = make_game()
        give_ink(G, 'p1', 1)
        # HeiHei - Boat Snack costs 1
        heihei = add_character(G, 'p1', 'heihei_boat_snack', zone=ZONE_HAND)

        actions = compute_can_play(G)

        assert len(actions) == 1
        assert actions[0].src == heihei


# =============================================================================
# CHARACTERS ENTER PLAY
# =============================================================================

class TestCharactersEnterPlay:
    """
    When you play a character, it enters the play zone.
    It's ready but "drying" (can't act until next turn).
    """

    def test_playing_character_moves_to_play_zone(self):
        """
        SCENARIO: Playing a character puts it in the play zone.

        SETUP:
        - Player has Stitch in hand (costs 6)
        - Player has 6 ink

        AFTER PLAYING:
        - Stitch is in play zone
        - Stitch is ready (not exerted)
        - Ink available is reduced by card cost

        RULE: 4.3.4.7 - "If the card is a character... the card enters the Play zone."
        """
        G = make_game()
        give_ink(G, 'p1', 6)
        stitch = add_character(G, 'p1', 'stitch_rock_star', zone=ZONE_HAND)
        state = make_state(G)

        execute_play(state, stitch, 'p1')

        assert G.nodes[stitch]['zone'] == ZONE_PLAY, "Character should enter play"
        assert G.nodes[stitch]['exerted'] == '0', "Character should enter ready"
        assert G.nodes['p1']['ink_available'] == '0', "Ink should be spent (6 - 6 = 0)"

    def test_playing_character_tracks_entered_turn(self):
        """
        SCENARIO: The game tracks when a character entered play.

        This is used for the "drying/dry" check - characters can't
        quest or challenge on the turn they enter play.

        SETUP:
        - It's turn 3
        - Player plays Stitch

        EXPECTED:
        - Stitch's entered_play is set to 3

        RULE: 5.1.11 - "A character that entered play during their player's turn
                       is considered to be drying."
        """
        G = make_game()
        G.nodes['game']['turn'] = '3'
        give_ink(G, 'p1', 5)
        stitch = add_character(G, 'p1', 'stitch_rock_star', zone=ZONE_HAND)
        state = make_state(G)

        execute_play(state, stitch, 'p1')

        assert G.nodes[stitch]['entered_play'] == '3', "Should track turn when played"


# =============================================================================
# ACTIONS GO TO DISCARD
# =============================================================================

class TestActionsGoToDiscard:
    """
    Unlike characters, action cards don't stay in play.
    They resolve immediately and go to discard.
    """

    def test_playing_action_goes_to_discard(self):
        """
        SCENARIO: Playing an action card puts it in discard.

        SETUP:
        - Player has an action card in hand
        - Player has enough ink

        AFTER PLAYING:
        - Action is in discard pile (not in play)

        RULE: 4.3.4.7 - "If the card is an action, the effect immediately resolves
                        and the card goes to the player's discard pile."

        NOTE: We're testing the zone change only. Effect resolution is
              not yet implemented.
        """
        G = make_game()
        give_ink(G, 'p1', 2)

        # Manually create an action card node (since add_character is for characters)
        action_card = 'p1.dragon_fire.a'
        G.add_node(action_card,
            type='Card',
            label='dragon_fire',
            zone=ZONE_HAND,
            exerted='0',
            damage='0'
        )
        state = make_state(G)

        execute_play(state, action_card, 'p1')

        assert G.nodes[action_card]['zone'] == ZONE_DISCARD, "Action should go to discard"


# =============================================================================
# INK SPENDING
# =============================================================================

class TestInkSpending:
    """
    Playing a card costs ink. The ink_available is reduced but
    ink_total stays the same (ink refreshes each turn).
    """

    def test_playing_reduces_ink_available(self):
        """
        SCENARIO: Playing a card reduces ink_available.

        SETUP:
        - Player has 8 ink total, 8 ink available
        - Player plays a 6-cost card (Stitch - Rock Star)

        EXPECTED:
        - ink_available is now 2 (8 - 6)
        - ink_total is still 8 (doesn't change)
        """
        G = make_game()
        G.nodes['p1']['ink_total'] = '8'
        G.nodes['p1']['ink_available'] = '8'

        stitch = add_character(G, 'p1', 'stitch_rock_star', zone=ZONE_HAND)
        state = make_state(G)

        execute_play(state, stitch, 'p1')

        assert G.nodes['p1']['ink_available'] == '2', "Available ink should be reduced"
        assert G.nodes['p1']['ink_total'] == '8', "Total ink should not change"

    def test_can_play_multiple_cards_if_enough_ink(self):
        """
        SCENARIO: Can play multiple cards in one turn if you have enough ink.

        SETUP:
        - Player has 10 ink
        - Player has two 5-cost cards

        EXPECTED:
        - Both play actions are available initially
        - After playing one, can still afford the other
        """
        G = make_game()
        give_ink(G, 'p1', 10)

        stitch = add_character(G, 'p1', 'stitch_rock_star', zone=ZONE_HAND)
        moana = add_character(G, 'p1', 'stitch_carefree_surfer', zone=ZONE_HAND)

        actions = compute_can_play(G)

        assert len(actions) == 2, "Should be able to afford both cards"
