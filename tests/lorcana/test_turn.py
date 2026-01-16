"""
Turn Structure Tests
====================

These tests verify the turn structure rules as defined in the
Disney Lorcana Comprehensive Rules, Section 4.

TURN PHASES
-----------
Each turn follows this sequence:
1. Beginning Phase
   - Ready step (4.2.1): Ready all your cards
   - Set step (4.2.2): Characters become "dry", refill ink
   - Draw step (4.2.3): Draw 1 card (skip on turn 1 for starting player)
2. Main Phase (4.3): Take actions (ink, play, quest, challenge, pass)
3. End Phase (4.4): Turn ends, passes to opponent

OFFICIAL RULES REFERENCE
------------------------
4.2.1.1. "The active player readies all their cards in play and in their inkwell."

4.2.2.1. "Characters that are in play are no longer 'drying' and will be able to quest,
         challenge, or {E} to pay costs for activated abilities or song cards."

4.2.3.2. "First, the active player draws a card from their deck. If this turn is the
         first turn of the game, the active player skips this step."

3.2.1.2. "If a player attempted to draw from a deck with no cards since the last game
         state check, that player loses the game."
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.lorcana.conftest import make_game, add_character, make_state, give_ink, set_turn
from lib.lorcana.constants import Zone, NodeType, Edge, Action, Step
from lib.lorcana.mechanics.turn import compute_can_pass, advance_turn, _ready_step, _set_step, _draw_step
from lib.core.graph import edges_by_label


# =============================================================================
# PASSING / ENDING TURN
# =============================================================================

class TestCanPass:
    """
    You can only pass (end your turn) during the main phase.
    Passing advances the game to your opponent's turn.
    """

    def test_can_pass_during_main_phase(self):
        """
        SCENARIO: Player can pass during main phase.

        SETUP:
        - It's P1's turn, main phase

        EXPECTED:
        - CAN_PASS action is available

        RULE: 4.4.1 - "To end a turn... The active player declares the end of their turn."
        """
        G = make_game()
        # make_game() sets up main phase by default

        actions = compute_can_pass(G)

        assert len(actions) == 1
        assert actions[0].action_type == Action.PASS

    def test_cannot_pass_during_other_phases(self):
        """
        SCENARIO: Cannot pass during non-main phases.

        SETUP:
        - Current step is "ready" (not main)

        EXPECTED:
        - No CAN_PASS action available

        REASONING: You can only take actions during main phase (4.3).
        """
        G = make_game()
        # Change step to ready
        step_edges = edges_by_label(G, Edge.CURRENT_STEP)
        if step_edges:
            game, old_step, key = step_edges[0]
            G.remove_edge(game, old_step, key)
        G.add_edge('game', 'step.p1.ready', label=Edge.CURRENT_STEP)
        G.add_node('step.p1.ready', type=NodeType.STEP, player='p1', step=Step.READY)

        actions = compute_can_pass(G)

        assert len(actions) == 0, "Cannot pass outside of main phase"


# =============================================================================
# READY STEP
# =============================================================================

class TestReadyStep:
    """
    At the start of your turn, all your exerted cards become ready.
    This happens automatically in the ready step.
    """

    def test_ready_step_readies_exerted_characters(self):
        """
        SCENARIO: Exerted characters become ready at start of turn.

        SETUP:
        - P2 has two exerted characters in play
        - P1 passes, triggering P2's turn

        EXPECTED:
        - Both P2's characters are now ready

        RULE: 4.2.1.1 - "The active player readies all their cards in play"
        """
        G = make_game()
        state = make_state(G)

        # P2 has exerted characters
        char1 = add_character(G, 'p2', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=True,
            entered_play=0
        )
        char2 = add_character(G, 'p2', 'simba_protective_cub',
            zone=Zone.PLAY,
            exerted=True,
            entered_play=0
        )

        # Simulate ready step for P2
        _ready_step(state, 'p2')

        assert G.nodes[char1]['exerted'] == '0', "First character should be ready"
        assert G.nodes[char2]['exerted'] == '0', "Second character should be ready"

    def test_ready_step_does_not_affect_opponent(self):
        """
        SCENARIO: Ready step only affects the active player's cards.

        SETUP:
        - P1 has exerted characters
        - P2's ready step runs

        EXPECTED:
        - P1's characters remain exerted

        RULE: 4.2.1.1 - "The active player readies all their cards"
        """
        G = make_game()
        state = make_state(G)

        # P1 has exerted character
        char1 = add_character(G, 'p1', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=True,
            entered_play=0
        )

        # Run P2's ready step
        _ready_step(state, 'p2')

        assert G.nodes[char1]['exerted'] == '1', "Opponent's characters should stay exerted"


# =============================================================================
# SET STEP
# =============================================================================

class TestSetStep:
    """
    The set step refills your ink and gives you a new ink drop.
    """

    def test_set_step_refills_ink(self):
        """
        SCENARIO: Ink available refills to ink total at start of turn.

        SETUP:
        - P1 has 5 ink total but 0 ink available (spent last turn)

        EXPECTED:
        - ink_available is now 5 (matches ink_total)

        REASONING: At start of turn, all your ink becomes ready again.
        """
        G = make_game()
        G.nodes['p1']['ink_total'] = '5'
        G.nodes['p1']['ink_available'] = '0'
        state = make_state(G)

        _set_step(state, 'p1')

        assert G.nodes['p1']['ink_available'] == '5', "Ink should refill"
        assert G.nodes['p1']['ink_total'] == '5', "Ink total unchanged"

    def test_set_step_grants_ink_drop(self):
        """
        SCENARIO: Player gets 1 ink drop at start of turn.

        SETUP:
        - P1 has 0 ink drops (used last turn)

        EXPECTED:
        - ink_drops is now 1

        RULE: Each turn you can add one card to your inkwell.
        """
        G = make_game()
        G.nodes['p1']['ink_drops'] = '0'
        state = make_state(G)

        _set_step(state, 'p1')

        assert G.nodes['p1']['ink_drops'] == '1', "Should get 1 ink drop"


# =============================================================================
# DRAW STEP
# =============================================================================

class TestDrawStep:
    """
    You draw 1 card at the start of your turn (except turn 1 for starting player).
    """

    def test_draw_step_draws_one_card(self):
        """
        SCENARIO: Player draws a card at start of turn.

        SETUP:
        - It's turn 2 (not first turn)
        - P1 has cards in deck, none in hand

        EXPECTED:
        - P1 now has 1 card in hand

        RULE: 4.2.3.2 - "the active player draws a card from their deck"
        """
        G = make_game()
        set_turn(G, 2)
        # Give P1 a deck
        state = make_state(G)
        state.deck1_ids = ['stitch_rock_star.a', 'simba_protective_cub.a']

        _draw_step(state, 'p1')

        # Check a card was drawn (node created with zone=hand)
        hand_cards = [n for n in G.nodes() if n.startswith('p1.') and G.nodes[n].get('zone') == 'hand']
        assert len(hand_cards) == 1, "Should have drawn 1 card"

    def test_starting_player_skips_first_draw(self):
        """
        SCENARIO: Starting player (P1) doesn't draw on turn 1.

        SETUP:
        - It's turn 1
        - P1 is starting player

        EXPECTED:
        - P1 draws nothing

        RULE: 4.2.3.2 - "If this turn is the first turn of the game, the active
                        player skips this step."
        """
        G = make_game()
        set_turn(G, 1)
        state = make_state(G)
        state.deck1_ids = ['stitch_rock_star.a']

        _draw_step(state, 'p1')

        # Should not have drawn
        hand_cards = [n for n in G.nodes() if n.startswith('p1.') and G.nodes[n].get('zone') == 'hand']
        assert len(hand_cards) == 0, "P1 should not draw on turn 1"
        assert len(state.deck1_ids) == 1, "Deck should be unchanged"

    def test_second_player_draws_on_turn_2(self):
        """
        SCENARIO: P2 draws normally on their first turn (turn 2).

        SETUP:
        - It's turn 2 (P2's first turn)
        - P2 has cards in deck

        EXPECTED:
        - P2 draws 1 card

        REASONING: The "skip draw on turn 1" only applies to turn 1, which is
                   always the starting player's first turn.
        """
        G = make_game()
        set_turn(G, 2)
        state = make_state(G)
        state.deck2_ids = ['stitch_rock_star.a']

        _draw_step(state, 'p2')

        hand_cards = [n for n in G.nodes() if n.startswith('p2.') and G.nodes[n].get('zone') == 'hand']
        assert len(hand_cards) == 1, "P2 should draw on turn 2"


# =============================================================================
# DECK-OUT LOSS CONDITION
# =============================================================================

class TestDeckOut:
    """
    If you need to draw but your deck is empty, you lose the game.
    """

    def test_empty_deck_causes_loss(self):
        """
        SCENARIO: Player with empty deck loses when they need to draw.

        SETUP:
        - It's turn 3 (not turn 1, so draw happens)
        - P1's deck is empty

        EXPECTED:
        - Game is over
        - P2 wins (P1 loses)

        RULE: 3.2.1.2 - "If a player attempted to draw from a deck with no cards
                        since the last game state check, that player loses the game."
        """
        G = make_game()
        set_turn(G, 3)
        state = make_state(G)
        state.deck1_ids = []  # Empty deck

        _draw_step(state, 'p1')

        assert G.nodes['game']['game_over'] == '1', "Game should be over"
        assert G.nodes['game']['winner'] == 'p2', "Opponent should win"

    def test_deck_with_cards_does_not_lose(self):
        """
        SCENARIO: Player with cards in deck draws normally.

        SETUP:
        - P1 has 1 card in deck

        EXPECTED:
        - Game is NOT over
        - Card is drawn
        """
        G = make_game()
        set_turn(G, 2)
        state = make_state(G)
        state.deck1_ids = ['stitch_rock_star.a']

        _draw_step(state, 'p1')

        assert G.nodes['game'].get('game_over', '0') == '0', "Game should not be over"


# =============================================================================
# FULL TURN ADVANCE
# =============================================================================

class TestAdvanceTurn:
    """
    When you pass, the game advances through all steps to your opponent's main phase.
    """

    def test_advance_turn_switches_active_player(self):
        """
        SCENARIO: Passing switches the active player.

        SETUP:
        - It's P1's turn

        EXPECTED:
        - After passing, it's P2's turn

        RULE: Turn passes to opponent after you end your turn.
        """
        G = make_game()
        state = make_state(G)
        state.deck2_ids = ['stitch_rock_star.a']  # P2 needs cards to draw

        advance_turn(state, 'p1', 'game')

        # Check CURRENT_TURN edge
        turn_edges = edges_by_label(G, Edge.CURRENT_TURN)
        assert len(turn_edges) == 1
        _, current_player, _ = turn_edges[0]
        assert current_player == 'p2', "Should be P2's turn"

    def test_advance_turn_increments_turn_number(self):
        """
        SCENARIO: Turn number increases when turn passes.

        SETUP:
        - It's turn 1

        EXPECTED:
        - After passing, it's turn 2
        """
        G = make_game()
        set_turn(G, 1)
        state = make_state(G)
        state.deck2_ids = ['stitch_rock_star.a']

        advance_turn(state, 'p1', 'game')

        assert G.nodes['game']['turn'] == '2', "Turn should increment"

    def test_advance_turn_ends_in_main_phase(self):
        """
        SCENARIO: After turn advances, new player is in main phase.

        EXPECTED:
        - CURRENT_STEP is the new player's main step
        """
        G = make_game()
        state = make_state(G)
        state.deck2_ids = ['stitch_rock_star.a']

        advance_turn(state, 'p1', 'game')

        step_edges = edges_by_label(G, Edge.CURRENT_STEP)
        assert len(step_edges) == 1
        _, current_step, _ = step_edges[0]
        assert current_step == 'step.p2.main', "Should be P2's main phase"

    def test_advance_turn_readies_new_player_characters(self):
        """
        SCENARIO: New player's exerted characters ready when turn passes.

        SETUP:
        - P2 has exerted characters
        - P1 passes

        EXPECTED:
        - P2's characters are now ready
        """
        G = make_game()
        state = make_state(G)
        state.deck2_ids = ['moana_of_motunui.a']

        char = add_character(G, 'p2', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=True,
            entered_play=0
        )

        advance_turn(state, 'p1', 'game')

        assert G.nodes[char]['exerted'] == '0', "Character should be ready"

    def test_advance_turn_refills_new_player_ink(self):
        """
        SCENARIO: New player's ink refills when turn passes.

        SETUP:
        - P2 has 3 ink total, 0 available
        - P1 passes

        EXPECTED:
        - P2 has 3 ink available
        """
        G = make_game()
        G.nodes['p2']['ink_total'] = '3'
        G.nodes['p2']['ink_available'] = '0'
        G.nodes['p2']['ink_drops'] = '0'
        state = make_state(G)
        state.deck2_ids = ['stitch_rock_star.a']

        advance_turn(state, 'p1', 'game')

        assert G.nodes['p2']['ink_available'] == '3', "Ink should refill"
        assert G.nodes['p2']['ink_drops'] == '1', "Should get ink drop"
