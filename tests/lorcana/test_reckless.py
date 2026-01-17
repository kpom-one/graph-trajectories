"""
Reckless Keyword Tests
======================

Reckless prevents characters from questing.

OFFICIAL RULES REFERENCE
------------------------
Reckless: "This character can't quest and must challenge each turn if able."

GRAPH DESIGN
------------
Printed Reckless creates:
- ability --[Keyword.RECKLESS]--> card
- ability --[Edge.CANT_QUEST]--> card

Quest logic checks for CANT_QUEST edge and blocks quest action.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.lorcana.conftest import make_game, add_character, set_turn
from lib.lorcana.constants import Zone, Edge
from lib.lorcana.mechanics.quest import compute_can_quest
from lib.lorcana.helpers import has_edge


class TestReckless:
    """Characters with Reckless cannot quest."""

    def test_reckless_cannot_quest(self):
        """
        SCENARIO: A character with Reckless cannot quest.

        SETUP:
        - Gaston (has Reckless) is ready and dry

        EXPECTED:
        - Gaston CANNOT quest
        """
        G = make_game()
        set_turn(G, 3)

        add_character(G, 'p1', 'gaston_arrogant_hunter',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=2
        )

        actions = compute_can_quest(G)

        assert len(actions) == 0, "Reckless character cannot quest"

    def test_non_reckless_can_quest(self):
        """
        SCENARIO: A character without Reckless can quest normally.

        SETUP:
        - Stitch (no Reckless) is ready and dry

        EXPECTED:
        - Stitch CAN quest
        """
        G = make_game()
        set_turn(G, 3)

        stitch = add_character(G, 'p1', 'stitch_new_dog',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=2
        )

        actions = compute_can_quest(G)

        assert len(actions) == 1, "Non-reckless character can quest"
        assert actions[0].src == stitch

    def test_cant_quest_edge_created_on_play(self):
        """
        SCENARIO: CANT_QUEST edge is created when Reckless character enters play.

        SETUP:
        - Gaston (has Reckless) is in play

        EXPECTED:
        - Gaston has a CANT_QUEST edge pointing to it
        """
        G = make_game()
        set_turn(G, 3)

        gaston = add_character(G, 'p1', 'gaston_arrogant_hunter',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=2
        )

        assert has_edge(G, gaston, Edge.CANT_QUEST), "Reckless should create CANT_QUEST edge"
