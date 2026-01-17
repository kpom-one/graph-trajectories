"""
Alert Keyword Tests
===================

Alert allows a character to challenge opponents with Evasive as if the
Alert character also had Evasive.

OFFICIAL RULES REFERENCE
------------------------
Alert: "This character can challenge characters with Evasive."

GRAPH DESIGN
------------
Printed Alert creates: ability --[Keyword.ALERT]--> card
Challenge logic checks if defender has Evasive, then permits if attacker has Evasive OR Alert.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.lorcana.conftest import make_game, add_character, set_turn
from lib.lorcana.constants import Zone
from lib.lorcana.mechanics.challenge import compute_can_challenge


class TestAlert:
    """Characters with Alert can challenge Evasive characters."""

    def test_alert_can_challenge_evasive(self):
        """
        SCENARIO: A character with Alert can challenge an Evasive character.

        SETUP:
        - Cri-Kee (has Alert) is ready and dry
        - Peter Pan (has Evasive) is exerted

        EXPECTED:
        - Cri-Kee CAN challenge Peter Pan
        """
        G = make_game()
        set_turn(G, 3)

        attacker = add_character(G, 'p1', 'cri_kee_good_luck_charm',
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

        assert len(actions) == 1, "Alert can challenge Evasive"
        assert actions[0].src == attacker
        assert actions[0].dst == defender

    def test_alert_can_challenge_non_evasive(self):
        """
        SCENARIO: A character with Alert can challenge a non-Evasive character.

        SETUP:
        - Cri-Kee (has Alert) is ready and dry
        - Stitch (no Evasive) is exerted

        EXPECTED:
        - Cri-Kee CAN challenge Stitch (Alert doesn't restrict normal challenges)
        """
        G = make_game()
        set_turn(G, 3)

        attacker = add_character(G, 'p1', 'cri_kee_good_luck_charm',
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

        assert len(actions) == 1, "Alert can challenge non-Evasive"
        assert actions[0].src == attacker
        assert actions[0].dst == defender
