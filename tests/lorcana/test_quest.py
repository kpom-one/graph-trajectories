"""
Quest Mechanic Tests
====================

These tests verify the rules for questing as defined in the
Disney Lorcana Comprehensive Rules, Section 4.3.5.

WHAT IS QUESTING?
-----------------
Questing is how you gain lore to win the game. You send a character
on a quest, they exert (turn sideways), and you gain lore equal to
that character's lore value.

OFFICIAL RULES REFERENCE
------------------------
4.3.5.1. "Sending a character on a quest is a turn action. Only characters can quest."

4.3.5.5. "Second, the player identifies the questing character and checks for any
         restrictions that prevent them from questing (e.g., they aren't dry yet,
         they have Reckless, etc.)."

4.3.5.7. "Third, the player exerts the questing character."

4.3.5.8. "If no effect prevents the character from questing, the quest is complete
         and the questing player gains lore equal to the {L} of the questing character."

5.1.11. "Drying - A character that entered play during their player's turn is considered
        to be drying. A drying character can't quest..."

5.1.12. "Dry - A character that's been in play since the start of their player's turn
        is considered to be dry. A dry character can quest..."
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.lorcana.conftest import make_game, add_character, make_state, give_ink, set_turn
from lib.lorcana.constants import Zone
from lib.lorcana.mechanics.quest import compute_can_quest, execute_quest


# =============================================================================
# BASIC QUESTING
# =============================================================================

class TestBasicQuesting:
    """
    A character can quest if they meet ALL of these conditions:
    1. They are a character (not an item or location)
    2. They are in play (not in hand, deck, or discard)
    3. They have a lore value greater than 0
    4. They are ready (not exerted)
    5. They are "dry" (were in play at the start of the turn)
    """

    def test_character_can_quest_when_all_conditions_met(self):
        """
        SCENARIO: A ready, dry character with lore can quest.

        SETUP:
        - Stitch is in play, ready, and has been here since before this turn
        - Stitch has 2 lore

        EXPECTED:
        - Stitch CAN quest (action should be available)

        RULE: 4.3.5.1 - "Sending a character on a quest is a turn action."
        """
        G = make_game()
        stitch = add_character(G, 'p1', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=0  # Turn 0 = before the game, so definitely dry
        )

        actions = compute_can_quest(G)

        assert len(actions) == 1, "Stitch should be able to quest"
        assert actions[0].src == stitch

    def test_questing_grants_lore_to_player(self):
        """
        SCENARIO: When a character quests, the player gains lore.

        SETUP:
        - Player 1 has 0 lore
        - Stitch quests (Stitch - Rock Star has 3 lore)

        EXPECTED:
        - Player 1 now has 3 lore
        - Stitch is now exerted

        RULE: 4.3.5.8 - "the questing player gains lore equal to the {L}
                        of the questing character."
        RULE: 4.3.5.7 - "Third, the player exerts the questing character."
        """
        G = make_game()
        stitch = add_character(G, 'p1', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=0
        )
        state = make_state(G)

        # Stitch - Rock Star has 3 lore
        execute_quest(state, stitch, 'p1')

        assert G.nodes['p1']['lore'] == '3', "Player should gain lore equal to character's lore value"
        assert G.nodes[stitch]['exerted'] == '1', "Character should be exerted after questing"


# =============================================================================
# DRY vs DRYING (Fresh Characters Can't Quest)
# =============================================================================

class TestDryingRestriction:
    """
    Characters that just entered play this turn are "drying" and can't quest.
    They become "dry" at the start of their controller's NEXT turn.

    This prevents you from playing a character and immediately questing with it.
    """

    def test_character_played_this_turn_cannot_quest(self):
        """
        SCENARIO: A character that just entered play cannot quest.

        SETUP:
        - It's turn 3
        - Stitch entered play on turn 3 (this turn)

        EXPECTED:
        - Stitch CANNOT quest (no action available)

        RULE: 5.1.11 - "A drying character can't quest..."
        """
        G = make_game()
        set_turn(G, 3)

        stitch = add_character(G, 'p1', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=3  # Entered THIS turn
        )

        actions = compute_can_quest(G)

        assert len(actions) == 0, "Character played this turn is 'drying' and cannot quest"

    def test_character_played_last_turn_can_quest(self):
        """
        SCENARIO: A character that entered play on a previous turn can quest.

        SETUP:
        - It's turn 3
        - Stitch entered play on turn 2 (last turn)

        EXPECTED:
        - Stitch CAN quest

        RULE: 5.1.12 - "A dry character can quest..."
        RULE: 4.2.2.1 - "Characters that are in play are no longer 'drying' and
                        will be able to quest, challenge..."
        """
        G = make_game()
        set_turn(G, 3)

        stitch = add_character(G, 'p1', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=2  # Entered LAST turn
        )

        actions = compute_can_quest(G)

        assert len(actions) == 1, "Character played on a previous turn is 'dry' and can quest"


# =============================================================================
# EXERTED CHARACTERS
# =============================================================================

class TestExertedRestriction:
    """
    Only READY characters can quest. Exerted characters cannot.

    A character becomes exerted when they quest, challenge, or use certain abilities.
    They become ready again at the start of their controller's turn.
    """

    def test_exerted_character_cannot_quest(self):
        """
        SCENARIO: An exerted character cannot quest.

        SETUP:
        - Stitch is in play but exerted (already used this turn)

        EXPECTED:
        - Stitch CANNOT quest

        REASONING: The rules don't explicitly say "ready characters can quest"
                   but 4.3.5.7 says "the player exerts the questing character" -
                   you can't exert something that's already exerted.
        """
        G = make_game()
        stitch = add_character(G, 'p1', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=True,  # Already exerted
            entered_play=0
        )

        actions = compute_can_quest(G)

        assert len(actions) == 0, "Exerted character cannot quest"


# =============================================================================
# LORE VALUE REQUIREMENTS
# =============================================================================

class TestZeroLore:
    """
    Characters with 0 lore CAN still quest - they just gain 0 lore.
    This matters for triggered abilities ("whenever this character quests").
    """

    def test_character_with_zero_lore_can_quest(self):
        """
        SCENARIO: A character with 0 lore CAN quest.

        SETUP:
        - A character with 0 lore is in play, ready, and dry

        EXPECTED:
        - Character CAN quest (gains 0 lore, but still exerts and triggers abilities)

        RULE: 4.3.5.8 - "the questing player gains lore equal to the {L}"
              No rule prevents questing with 0 lore. You gain 0, but you still quest.
              This matters for "whenever this character quests" triggers.
        """
        G = make_game()
        # Gaston - Arrogant Hunter has 0 lore (he's Reckless, meant for combat)
        gaston = add_character(G, 'p1', 'gaston_arrogant_hunter',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=0
        )

        actions = compute_can_quest(G)

        assert len(actions) == 1, "Character with 0 lore CAN quest"
        assert actions[0].src == gaston

    def test_questing_with_zero_lore_gains_nothing(self):
        """
        SCENARIO: Questing with 0 lore gains 0 lore but still exerts.

        SETUP:
        - Player has 5 lore
        - Gaston (0 lore) quests

        EXPECTED:
        - Player still has 5 lore (gained 0)
        - Gaston is exerted

        RULE: 4.3.5.8 - You gain lore equal to {L}. If {L} is 0, you gain 0.
        """
        G = make_game()
        G.nodes['p1']['lore'] = '5'
        gaston = add_character(G, 'p1', 'gaston_arrogant_hunter',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=0
        )
        state = make_state(G)

        execute_quest(state, gaston, 'p1')

        assert G.nodes['p1']['lore'] == '5', "Should gain 0 lore"
        assert G.nodes[gaston]['exerted'] == '1', "Should still exert"


# =============================================================================
# ZONE RESTRICTIONS
# =============================================================================

class TestZoneRestrictions:
    """
    Only characters IN PLAY can quest.
    Characters in hand, deck, discard, or inkwell cannot quest.
    """

    def test_character_in_hand_cannot_quest(self):
        """
        SCENARIO: A character in hand cannot quest.

        EXPECTED: No quest action available

        RULE: 4.3.5.1 - Questing is for characters in play
        """
        G = make_game()
        add_character(G, 'p1', 'stitch_rock_star',
            zone=Zone.HAND  # In hand, not in play
        )

        actions = compute_can_quest(G)

        assert len(actions) == 0, "Character in hand cannot quest"


# =============================================================================
# WINNING THE GAME
# =============================================================================

class TestWinCondition:
    """
    The game is won when a player reaches 20 lore.
    This is checked immediately when lore is gained.
    """

    def test_reaching_20_lore_wins_game(self):
        """
        SCENARIO: Gaining enough lore to reach 20 wins the game.

        SETUP:
        - Player 1 has 17 lore
        - Stitch quests for 3 lore (Stitch - Rock Star has 3 lore)

        EXPECTED:
        - Player 1 now has 20 lore
        - Game is over
        - Player 1 is the winner

        RULE: 3.2.1 - "A player wins as soon as they have 20 or more lore."
        """
        G = make_game()
        G.nodes['p1']['lore'] = '17'

        stitch = add_character(G, 'p1', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=0
        )
        state = make_state(G)

        execute_quest(state, stitch, 'p1')

        assert G.nodes['p1']['lore'] == '20'
        assert G.nodes['game']['game_over'] == '1', "Game should be over"
        assert G.nodes['game']['winner'] == 'p1', "Player 1 should win"

    def test_exceeding_20_lore_still_wins(self):
        """
        SCENARIO: Going over 20 lore also wins (you don't have to hit exactly 20).

        SETUP:
        - Player 1 has 18 lore
        - Stitch quests for 3 lore

        EXPECTED:
        - Player 1 now has 21 lore
        - Game is over, Player 1 wins
        """
        G = make_game()
        G.nodes['p1']['lore'] = '18'

        stitch = add_character(G, 'p1', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=0
        )
        state = make_state(G)

        execute_quest(state, stitch, 'p1')

        assert G.nodes['p1']['lore'] == '21'
        assert G.nodes['game']['game_over'] == '1'
        assert G.nodes['game']['winner'] == 'p1'
