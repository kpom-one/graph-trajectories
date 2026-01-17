"""
Bodyguard Play Exerted Tests
============================

Bodyguard characters may optionally enter play exerted.

OFFICIAL RULES REFERENCE
------------------------
Bodyguard: "This character may enter play exerted."

GRAPH DESIGN
------------
Bodyguard cards get two CAN_PLAY edges:
- Normal: card --[action_type=Action.PLAY]--> player
- Exerted: card --[action_type=Action.PLAY, exerted=True]--> player
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.lorcana.conftest import make_game, add_character, make_state, give_ink
from lib.lorcana.constants import Zone, Action
from lib.lorcana.mechanics.play import compute_can_play, execute_play


class TestBodyguardPlayOptions:
    """Bodyguard cards have two play options."""

    def test_bodyguard_shows_two_play_options(self):
        """
        SCENARIO: Bodyguard cards display two CAN_PLAY options.

        SETUP:
        - Player has Simba (Bodyguard) in hand
        - Player has enough ink

        EXPECTED:
        - Two play actions available for Simba
        - One normal, one with exerted metadata
        """
        G = make_game()
        give_ink(G, 'p1', 2)  # Simba costs 2
        simba = add_character(G, 'p1', 'simba_protective_cub', zone=Zone.HAND)

        actions = compute_can_play(G)

        simba_actions = [a for a in actions if a.src == simba]
        assert len(simba_actions) == 2, "Bodyguard should have two play options"

        # One should be normal (no metadata or exerted=False)
        normal = [a for a in simba_actions if not a.metadata or not a.metadata.get('exerted')]
        assert len(normal) == 1, "Should have one normal play option"
        assert normal[0].description == f"play:{simba}"

        # One should be exerted
        exerted = [a for a in simba_actions if a.metadata and a.metadata.get('exerted')]
        assert len(exerted) == 1, "Should have one exerted play option"
        assert exerted[0].description == f"play:{simba}:exerted"

    def test_non_bodyguard_has_single_play_option(self):
        """
        SCENARIO: Non-bodyguard cards have only one play option.

        SETUP:
        - Player has Stitch (no Bodyguard) in hand
        - Player has enough ink

        EXPECTED:
        - Only one play action available
        """
        G = make_game()
        give_ink(G, 'p1', 4)  # Stitch New Dog costs 4
        stitch = add_character(G, 'p1', 'stitch_new_dog', zone=Zone.HAND)

        actions = compute_can_play(G)

        stitch_actions = [a for a in actions if a.src == stitch]
        assert len(stitch_actions) == 1, "Non-bodyguard should have one play option"
        assert stitch_actions[0].metadata is None or not stitch_actions[0].metadata.get('exerted')


class TestBodyguardPlayExecution:
    """Bodyguard play modes set correct exerted state."""

    def test_normal_play_enters_ready(self):
        """
        SCENARIO: Normal play mode enters ready state.

        SETUP:
        - Player plays Simba normally (no exerted metadata)

        EXPECTED:
        - Simba enters play ready (exerted='0')
        """
        G = make_game()
        give_ink(G, 'p1', 2)
        simba = add_character(G, 'p1', 'simba_protective_cub', zone=Zone.HAND)
        state = make_state(G)

        # Execute normal play (no metadata)
        execute_play(state, simba, 'p1', metadata=None)

        assert G.nodes[simba]['zone'] == Zone.PLAY
        assert G.nodes[simba]['exerted'] == '0', "Normal play should enter ready"

    def test_bodyguard_play_exerted_enters_exerted(self):
        """
        SCENARIO: Bodyguard exerted play mode enters exerted state.

        SETUP:
        - Player plays Simba with exerted=True metadata

        EXPECTED:
        - Simba enters play exerted (exerted='1')
        """
        G = make_game()
        give_ink(G, 'p1', 2)
        simba = add_character(G, 'p1', 'simba_protective_cub', zone=Zone.HAND)
        state = make_state(G)

        # Execute bodyguard play (with exerted metadata)
        execute_play(state, simba, 'p1', metadata={'exerted': True})

        assert G.nodes[simba]['zone'] == Zone.PLAY
        assert G.nodes[simba]['exerted'] == '1', "Bodyguard exerted play should enter exerted"
