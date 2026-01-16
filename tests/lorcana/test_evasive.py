"""
Evasive Keyword Tests
=====================

Evasive protects a character from being challenged by non-Evasive characters.

OFFICIAL RULES REFERENCE
------------------------
Evasive: "Only characters with Evasive can challenge this character."

GRAPH DESIGN
------------
Printed Evasive creates: ability --[Keyword.EVASIVE]--> card
Challenge logic checks defender for Evasive edge, then requires attacker to have one too.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.lorcana.conftest import make_game, add_character, set_turn
from lib.lorcana.constants import Zone
from lib.lorcana.mechanics.challenge import compute_can_challenge


class TestEvasive:
    """Characters with Evasive can only be challenged by Evasive characters."""

    def test_non_evasive_cannot_challenge_evasive(self):
        """
        SCENARIO: A character without Evasive cannot challenge an Evasive character.

        SETUP:
        - Stitch (no Evasive) is ready and dry
        - Peter Pan (has Evasive) is exerted

        EXPECTED:
        - Stitch CANNOT challenge Peter Pan
        """
        G = make_game()
        set_turn(G, 3)

        add_character(G, 'p1', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=2
        )

        add_character(G, 'p2', 'peter_pan_never_landing',
            zone=Zone.PLAY,
            exerted=True,
            entered_play=2
        )

        actions = compute_can_challenge(G)

        assert len(actions) == 0, "Non-Evasive cannot challenge Evasive"

    def test_evasive_can_challenge_evasive(self):
        """
        SCENARIO: A character with Evasive can challenge an Evasive character.

        SETUP:
        - Peter Pan (has Evasive) is ready and dry
        - Another Peter Pan (has Evasive) is exerted

        EXPECTED:
        - Can challenge
        """
        G = make_game()
        set_turn(G, 3)

        attacker = add_character(G, 'p1', 'peter_pan_never_landing',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=2
        )

        defender = add_character(G, 'p2', 'peter_pan_never_landing',
            zone=Zone.PLAY,
            exerted=True,
            entered_play=2
        )

        actions = compute_can_challenge(G)

        assert len(actions) == 1, "Evasive can challenge Evasive"
        assert actions[0].src == attacker
        assert actions[0].dst == defender

    def test_evasive_can_challenge_non_evasive(self):
        """
        SCENARIO: A character with Evasive can challenge a non-Evasive character.

        SETUP:
        - Peter Pan (has Evasive) is ready and dry
        - Stitch (no Evasive) is exerted

        EXPECTED:
        - Can challenge (Evasive only restricts who can challenge YOU)
        """
        G = make_game()
        set_turn(G, 3)

        attacker = add_character(G, 'p1', 'peter_pan_never_landing',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=2
        )

        defender = add_character(G, 'p2', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=True,
            entered_play=2
        )

        actions = compute_can_challenge(G)

        assert len(actions) == 1, "Evasive can challenge non-Evasive"
        assert actions[0].src == attacker
        assert actions[0].dst == defender
