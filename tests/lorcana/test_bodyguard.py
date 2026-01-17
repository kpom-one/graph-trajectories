"""
Bodyguard Keyword Tests
=======================

Bodyguard forces opponents to target characters with Bodyguard if able.

OFFICIAL RULES REFERENCE
------------------------
Bodyguard: "An opposing character who challenges one of your characters
must choose one with Bodyguard if able."

GRAPH DESIGN
------------
Printed Bodyguard creates: ability --[Keyword.BODYGUARD]--> card
Challenge logic filters valid defenders to only Bodyguard characters when present.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.lorcana.conftest import make_game, add_character, set_turn
from lib.lorcana.constants import Zone
from lib.lorcana.mechanics.challenge import compute_can_challenge


class TestBodyguard:
    """Characters with Bodyguard must be challenged if able."""

    def test_must_challenge_bodyguard_when_exerted(self):
        """
        SCENARIO: With both exerted Bodyguard and non-Bodyguard present,
        only Bodyguard becomes a valid target.

        SETUP:
        - Stitch (attacker, no keywords) is ready and dry
        - Simba (has Bodyguard) is exerted
        - Stitch New Dog (no Bodyguard) is exerted

        EXPECTED:
        - Only Simba (Bodyguard) can be challenged
        """
        G = make_game()
        set_turn(G, 3)

        attacker = add_character(G, 'p1', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=2
        )

        bodyguard = add_character(G, 'p2', 'simba_protective_cub',
            zone=Zone.PLAY,
            exerted=True,
            entered_play=2
        )

        add_character(G, 'p2', 'stitch_new_dog',
            zone=Zone.PLAY,
            exerted=True,
            entered_play=2
        )

        actions = compute_can_challenge(G)

        assert len(actions) == 1, "Must challenge Bodyguard when present"
        assert actions[0].src == attacker
        assert actions[0].dst == bodyguard

    def test_ready_bodyguard_doesnt_restrict(self):
        """
        SCENARIO: A ready (non-exerted) Bodyguard doesn't limit target selection.

        SETUP:
        - Stitch (attacker) is ready and dry
        - Simba (has Bodyguard) is ready (not exerted)
        - Stitch New Dog (no Bodyguard) is exerted

        EXPECTED:
        - Can challenge Stitch New Dog (Bodyguard not exerted, so not "able")
        """
        G = make_game()
        set_turn(G, 3)

        attacker = add_character(G, 'p1', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=2
        )

        add_character(G, 'p2', 'simba_protective_cub',
            zone=Zone.PLAY,
            exerted=False,  # Ready, not a valid target
            entered_play=2
        )

        non_bodyguard = add_character(G, 'p2', 'stitch_new_dog',
            zone=Zone.PLAY,
            exerted=True,
            entered_play=2
        )

        actions = compute_can_challenge(G)

        assert len(actions) == 1, "Ready Bodyguard doesn't restrict targets"
        assert actions[0].src == attacker
        assert actions[0].dst == non_bodyguard

    def test_multiple_bodyguards_all_valid(self):
        """
        SCENARIO: Multiple exerted Bodyguards all remain valid targets.

        SETUP:
        - Stitch (attacker) is ready and dry
        - Two Simbas (both have Bodyguard) are exerted

        EXPECTED:
        - Both Bodyguards are valid challenge targets
        """
        G = make_game()
        set_turn(G, 3)

        attacker = add_character(G, 'p1', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=2
        )

        # Add first bodyguard with unique node id
        bodyguard1 = 'p2.simba_protective_cub.a'
        G.add_node(bodyguard1,
            type='card',
            label='simba_protective_cub',
            zone=Zone.PLAY,
            exerted='1',
            damage='0',
            entered_play='2'
        )
        from lib.lorcana.cards import get_card_db
        from lib.lorcana.abilities import create_printed_abilities
        card_db = get_card_db()
        create_printed_abilities(G, bodyguard1, card_db['simba_protective_cub'], 2)

        # Add second bodyguard with different node id
        bodyguard2 = 'p2.simba_protective_cub.b'
        G.add_node(bodyguard2,
            type='card',
            label='simba_protective_cub',
            zone=Zone.PLAY,
            exerted='1',
            damage='0',
            entered_play='2'
        )
        create_printed_abilities(G, bodyguard2, card_db['simba_protective_cub'], 2)

        actions = compute_can_challenge(G)

        assert len(actions) == 2, "Multiple Bodyguards all valid"
        targets = {a.dst for a in actions}
        assert bodyguard1 in targets
        assert bodyguard2 in targets
        assert all(a.src == attacker for a in actions)
