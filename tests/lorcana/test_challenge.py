"""
Challenge Mechanic Tests
========================

These tests verify the rules for challenging as defined in the
Disney Lorcana Comprehensive Rules, Section 4.3.6.

WHAT IS CHALLENGING?
--------------------
Challenging is combat. Your character attacks an opponent's EXERTED character.
Both characters deal damage equal to their strength to each other.
If a character takes damage equal to or greater than their willpower, they're banished.

OFFICIAL RULES REFERENCE
------------------------
4.3.6.1. "Sending a character into a challenge is a turn action. Only characters can challenge."

4.3.6.6. "First, the player declares one of their characters is challenging a character.
         The declared character must have been in play since the beginning of the turn
         (that is, they must be dry), ready, and otherwise able to challenge."

4.3.6.7. "Second, the player chooses an exerted opposing character to be challenged."

4.3.6.9. "Fourth, the challenging player exerts the challenging character."

4.3.6.13. "Eighth, once all effects in the bag have resolved, each character deals damage
          equal to their Strength {S} to the other character."

5.1.11. "Drying - A character that entered play during their player's turn is considered
        to be drying. A drying character... can't be declared as a challenging character..."

5.1.12. "Dry - A character that's been in play since the start of their player's turn is
        considered to be dry. A dry character can... be declared as a challenging character."
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.lorcana.conftest import make_game, add_character, make_state, set_turn
from lib.lorcana.constants import Zone
from lib.lorcana.mechanics.challenge import compute_can_challenge, execute_challenge
from lib.lorcana.state_based_effects import check_state_based_effects


# =============================================================================
# BASIC CHALLENGING
# =============================================================================

class TestBasicChallenging:
    """
    To challenge, your character must be:
    1. A character (not item/location)
    2. In play
    3. Ready (not exerted)
    4. Dry (was in play at start of turn)
    5. Have strength > 0

    The target must be:
    1. An opposing character
    2. Exerted
    """

    def test_can_challenge_exerted_opponent(self):
        """
        SCENARIO: A ready, dry character can challenge an exerted opponent.

        SETUP:
        - P1 has Simba (ready, dry, 4 strength)
        - P2 has Stitch (exerted)

        EXPECTED:
        - Simba CAN challenge Stitch

        RULE: 4.3.6.6 - Challenger must be "dry, ready, and otherwise able to challenge"
        RULE: 4.3.6.7 - Target must be "an exerted opposing character"
        """
        G = make_game()

        simba = add_character(G, 'p1', 'simba_protective_cub',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=0  # Dry
        )
        stitch = add_character(G, 'p2', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=True  # Valid target
        )

        actions = compute_can_challenge(G)

        assert len(actions) == 1
        assert actions[0].src == simba
        assert actions[0].dst == stitch

    def test_challenging_deals_damage_both_ways(self):
        """
        SCENARIO: In a challenge, both characters deal damage to each other.

        SETUP:
        - Simba - Protective Cub (2 strength) challenges Stitch - Rock Star (3 strength)

        EXPECTED:
        - Simba takes 3 damage (from Stitch's strength)
        - Stitch takes 2 damage (from Simba's strength)
        - Simba becomes exerted

        RULE: 4.3.6.13 - "each character deals damage equal to their Strength {S}
                         to the other character"
        RULE: 4.3.6.9 - "the challenging player exerts the challenging character"
        """
        G = make_game()

        simba = add_character(G, 'p1', 'simba_protective_cub',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=0
        )
        stitch = add_character(G, 'p2', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=True
        )
        state = make_state(G)

        execute_challenge(state, simba, stitch)

        # Simba - Protective Cub has 2 strength, Stitch - Rock Star has 3 strength
        assert G.nodes[simba]['damage'] == '3', "Simba should take damage equal to Stitch's strength"
        assert G.nodes[stitch]['damage'] == '2', "Stitch should take damage equal to Simba's strength"
        assert G.nodes[simba]['exerted'] == '1', "Attacker should be exerted"


# =============================================================================
# VALID TARGETS (Must Be Exerted)
# =============================================================================

class TestTargetMustBeExerted:
    """
    You can ONLY challenge EXERTED characters.

    This is a core strategic element - you have to "bait" characters into
    exerting (by questing or using abilities) before you can attack them.
    """

    def test_cannot_challenge_ready_opponent(self):
        """
        SCENARIO: Cannot challenge a ready (non-exerted) opponent.

        SETUP:
        - P1 has Simba (ready, dry)
        - P2 has Stitch (ready - NOT exerted)

        EXPECTED:
        - No challenge actions available

        RULE: 4.3.6.7 - "the player chooses an exerted opposing character"
        """
        G = make_game()

        add_character(G, 'p1', 'simba_protective_cub',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=0
        )
        add_character(G, 'p2', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=False  # Ready = can't be challenged
        )

        actions = compute_can_challenge(G)

        assert len(actions) == 0, "Cannot challenge a ready character"


# =============================================================================
# ATTACKER RESTRICTIONS
# =============================================================================

class TestAttackerRestrictions:
    """
    The attacking character has several requirements to be able to challenge.
    """

    def test_exerted_character_cannot_challenge(self):
        """
        SCENARIO: An exerted character cannot initiate a challenge.

        SETUP:
        - P1's Simba is exerted (already acted this turn)
        - P2's Stitch is exerted (valid target otherwise)

        EXPECTED:
        - No challenge actions available

        RULE: 4.3.6.6 - Challenger must be "ready"
        """
        G = make_game()

        add_character(G, 'p1', 'simba_protective_cub',
            zone=Zone.PLAY,
            exerted=True,  # Can't attack when exerted
            entered_play=0
        )
        add_character(G, 'p2', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=True
        )

        actions = compute_can_challenge(G)

        assert len(actions) == 0, "Exerted character cannot challenge"

    def test_drying_character_cannot_challenge(self):
        """
        SCENARIO: A character that just entered play cannot challenge.

        SETUP:
        - It's turn 3
        - P1's Simba entered play on turn 3 (this turn)
        - P2's Stitch is exerted

        EXPECTED:
        - No challenge actions available

        RULE: 4.3.6.6 - Challenger "must have been in play since the beginning
                        of the turn (that is, they must be dry)"
        RULE: 5.1.11 - "A drying character... can't be declared as a challenging character"
        """
        G = make_game()
        set_turn(G, 3)

        add_character(G, 'p1', 'simba_protective_cub',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=3  # Just played this turn
        )
        add_character(G, 'p2', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=True
        )

        actions = compute_can_challenge(G)

        assert len(actions) == 0, "Character played this turn cannot challenge"

    def test_character_with_zero_strength_can_challenge(self):
        """
        SCENARIO: A character with 0 strength CAN challenge.

        SETUP:
        - P1 has a character with 0 strength (ready, dry)
        - P2 has an exerted character

        EXPECTED:
        - Challenge action IS available

        RULE: 4.3.6.6 - Challenger must be "dry, ready, and otherwise able to challenge"
              No strength requirement. 0-strength characters deal 0 damage but can
              still challenge (matters for "when this character challenges" triggers).
        """
        G = make_game()

        # Dr. Facilier - Charlatan has 0 strength (he's a schemer, not a fighter)
        facilier = add_character(G, 'p1', 'dr._facilier_charlatan',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=0
        )
        stitch = add_character(G, 'p2', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=True
        )

        actions = compute_can_challenge(G)

        assert len(actions) == 1, "Character with 0 strength CAN challenge"
        assert actions[0].src == facilier
        assert actions[0].dst == stitch

    def test_zero_strength_challenger_deals_no_damage(self):
        """
        SCENARIO: A 0-strength challenger deals 0 damage but takes full damage.

        SETUP:
        - Dr. Facilier (0 strength) challenges Stitch (3 strength)

        EXPECTED:
        - Stitch takes 0 damage
        - Facilier takes 3 damage
        - Facilier is exerted

        RULE: 4.3.6.13 - "each character deals damage equal to their Strength {S}"
        """
        G = make_game()

        facilier = add_character(G, 'p1', 'dr._facilier_charlatan',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=0
        )
        stitch = add_character(G, 'p2', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=True
        )
        state = make_state(G)

        execute_challenge(state, facilier, stitch)

        assert G.nodes[stitch]['damage'] == '0', "Stitch takes 0 damage from 0-str attacker"
        assert G.nodes[facilier]['damage'] == '3', "Facilier takes full damage from Stitch"
        assert G.nodes[facilier]['exerted'] == '1', "Attacker should be exerted"


# =============================================================================
# BANISHING (Lethal Damage)
# =============================================================================

class TestBanishing:
    """
    When a character has damage >= their willpower, they are BANISHED
    (moved to the discard pile).

    This is checked as a state-based effect after actions resolve.
    """

    def test_lethal_damage_banishes_character(self):
        """
        SCENARIO: A character with damage >= willpower is banished.

        SETUP:
        - Stitch - Rock Star has 5 willpower
        - Stitch - Carefree Surfer has 4 strength
        - Carefree Surfer challenges Rock Star (who already has 1 damage)

        EXPECTED:
        - Rock Star now has 5 damage (1 + 4)
        - 5 damage >= 5 willpower, so Rock Star is banished

        RULE: From glossary - "banish: When a character or location has damage on them
              equal to or greater than their {W}, they are banished."
        """
        G = make_game()

        # Stitch - Carefree Surfer has 4 strength
        attacker = add_character(G, 'p1', 'stitch_carefree_surfer',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=0
        )
        # Stitch - Rock Star has 5 willpower
        defender = add_character(G, 'p2', 'stitch_rock_star',
            zone=Zone.PLAY,
            exerted=True,
            damage=1  # Already has 1 damage
        )
        state = make_state(G)

        execute_challenge(state, attacker, defender)
        check_state_based_effects(state)

        # Rock Star has 5 willpower, took 4 more damage (total 5), should be banished
        assert G.nodes[defender]['zone'] == Zone.DISCARD, "Character with lethal damage should be banished"

    def test_both_characters_can_be_banished(self):
        """
        SCENARIO: Both characters in a challenge can be banished (a "trade").

        SETUP:
        - Simba - Protective Cub (2 strength, 3 willpower, already has 1 damage)
        - Stitch - New Dog (2 strength, 2 willpower)

        After challenge:
        - Simba takes 2 damage (total 3) >= 3 willpower -> banished
        - Stitch takes 2 damage >= 2 willpower -> banished

        This is a trade - both characters die.
        """
        G = make_game()

        # Simba - Protective Cub: 2 strength, 3 willpower
        attacker = add_character(G, 'p1', 'simba_protective_cub',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=0,
            damage=1  # Already has 1 damage
        )
        # Stitch - New Dog: 2 strength, 2 willpower
        defender = add_character(G, 'p2', 'stitch_new_dog',
            zone=Zone.PLAY,
            exerted=True
        )
        state = make_state(G)

        execute_challenge(state, attacker, defender)
        check_state_based_effects(state)

        # Simba: 3 willpower, had 1 + takes 2 = 3 damage -> banished
        assert G.nodes[attacker]['zone'] == Zone.DISCARD, "Attacker should be banished"
        # Stitch: 2 willpower, takes 2 damage -> banished
        assert G.nodes[defender]['zone'] == Zone.DISCARD, "Defender should be banished"


# =============================================================================
# CANNOT CHALLENGE YOUR OWN CHARACTERS
# =============================================================================

class TestCannotChallengeOwnCharacters:
    """
    You can only challenge OPPOSING characters.
    You cannot attack your own characters.
    """

    def test_cannot_challenge_own_character(self):
        """
        SCENARIO: Cannot challenge your own exerted character.

        SETUP:
        - P1 has Simba (ready, dry)
        - P1 also has Stitch (exerted)

        EXPECTED:
        - No challenge actions available (no opposing targets)

        RULE: 4.3.6.7 - "chooses an exerted opposing character"
        """
        G = make_game()

        add_character(G, 'p1', 'simba_protective_cub',
            zone=Zone.PLAY,
            exerted=False,
            entered_play=0
        )
        add_character(G, 'p1', 'stitch_rock_star',  # Same player!
            zone=Zone.PLAY,
            exerted=True
        )

        actions = compute_can_challenge(G)

        assert len(actions) == 0, "Cannot challenge your own characters"
