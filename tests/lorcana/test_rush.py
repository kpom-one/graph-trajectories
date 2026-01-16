"""
Rush Keyword Tests
==================

Rush allows a character to challenge the turn they enter play,
bypassing the normal "drying" restriction.

OFFICIAL RULES REFERENCE
------------------------
Rush: "This character can challenge the turn they're played."

GRAPH DESIGN
------------
Printed Rush creates a self-loop edge: card --RUSH--> card
This edge is created when the character enters play.

The challenge logic checks for ANY incoming RUSH edge to determine
if a character can bypass the drying restriction.
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.lorcana.conftest import make_game, add_character, set_turn
from lib.lorcana.constants import Zone
from lib.lorcana.mechanics.challenge import compute_can_challenge


class TestRush:
    """Characters with Rush can challenge the turn they enter play."""

    def test_character_with_rush_can_challenge_when_drying(self):
        """
        SCENARIO: A character with printed Rush can challenge the turn it enters play.

        SETUP:
        - It's turn 3
        - Rafiki (has printed Rush) entered play this turn (turn 3)
        - Opponent has an exerted character

        EXPECTED:
        - Rafiki CAN challenge (Rush bypasses drying restriction)

        RULE: Rush - "This character can challenge the turn they're played."
        """
        G = make_game()
        set_turn(G, 3)

        # Rafiki - Mysterious Sage has printed Rush (3 cost, 3/3/1)
        rafiki = add_character(G, 'p1', 'rafiki_mysterious_sage',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=3  # Played THIS turn - normally can't challenge
        )

        # Opponent has valid target
        target = add_character(G, 'p2', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=True
        )

        actions = compute_can_challenge(G)

        assert len(actions) == 1, "Rush character should be able to challenge while drying"
        assert actions[0].src == rafiki
        assert actions[0].dst == target

    def test_rush_character_still_cannot_challenge_if_exerted(self):
        """
        SCENARIO: Rush doesn't let you challenge while exerted.

        SETUP:
        - Rafiki has Rush but is exerted

        EXPECTED:
        - Rafiki CANNOT challenge (exerted restriction still applies)

        Rush only bypasses the drying restriction, not other restrictions.
        """
        G = make_game()
        set_turn(G, 3)

        rafiki = add_character(G, 'p1', 'rafiki_mysterious_sage',
            zone=Zone.PLAY,
            exerted=True,  # Already exerted
            entered_play=2  # Dry (entered last turn)
        )

        add_character(G, 'p2', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=True
        )

        actions = compute_can_challenge(G)

        assert len(actions) == 0, "Rush doesn't bypass exerted restriction"

    def test_rush_character_can_challenge_when_dry(self):
        """
        SCENARIO: Rush character can also challenge normally when dry.

        SETUP:
        - Rafiki has Rush and entered play on a previous turn (dry)
        - Rafiki is ready

        EXPECTED:
        - Rafiki CAN challenge (Rush doesn't prevent normal challenging)
        """
        G = make_game()
        set_turn(G, 3)

        rafiki = add_character(G, 'p1', 'rafiki_mysterious_sage',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=2  # Entered last turn - already dry
        )

        target = add_character(G, 'p2', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=True
        )

        actions = compute_can_challenge(G)

        assert len(actions) == 1, "Rush character can challenge normally when dry"
        assert actions[0].src == rafiki
        assert actions[0].dst == target


class TestAbilityCleanup:
    """Ability nodes are removed when a character leaves play."""

    def test_rush_edge_removed_when_character_banished(self):
        """
        SCENARIO: When a Rush character is banished, its ability nodes are removed.

        SETUP:
        - Rafiki (has Rush) is in play with ability nodes
        - Rafiki is banished (moved to discard)

        EXPECTED:
        - Ability nodes with SOURCE edge to Rafiki are removed from graph
        """
        from tests.lorcana.conftest import make_state
        from lib.lorcana.constants import Edge, Keyword

        G = make_game()
        set_turn(G, 3)

        rafiki = add_character(G, 'p1', 'rafiki_mysterious_sage',
            zone=Zone.PLAY,
            entered_play=3
        )

        # Verify Rush ability exists before banish
        rush_edges = [
            (u, v) for u, v, data in G.in_edges(rafiki, data=True)
            if data.get('label') == Keyword.RUSH
        ]
        assert len(rush_edges) == 1, "Rush ability should exist before banish"

        # Find the ability node
        ability_node = rush_edges[0][0]
        assert ability_node in G.nodes(), "Ability node should exist"

        # Banish Rafiki
        state = make_state(G)
        state.move_card(rafiki, Zone.DISCARD)

        # Verify ability node is removed
        assert ability_node not in G.nodes(), "Ability node should be removed when card leaves play"

        # Verify card is in discard
        assert G.nodes[rafiki]['zone'] == Zone.DISCARD
