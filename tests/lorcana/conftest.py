"""
Test fixtures for Lorcana rules engine tests.

These helpers create minimal game states for testing specific rules.
They're intentionally simple - we're testing game logic, not full game setup.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import networkx as nx
from lib.lorcana.state import LorcanaState
from lib.lorcana.cards import get_card_db
from lib.lorcana.constants import Zone, Keyword, NodeType, Edge, Step
from lib.lorcana.abilities import create_printed_abilities


def make_game() -> nx.MultiDiGraph:
    """
    Create a minimal game graph with just the essentials.

    Returns a graph with:
    - game node (turn 1, p1's turn, main phase)
    - p1 and p2 player nodes
    - step nodes for turn structure
    """
    G = nx.MultiDiGraph()

    # Game state
    G.add_node('game', type=NodeType.GAME, turn='1', game_over='0', winner='')

    # Players
    G.add_node('p1', type=NodeType.PLAYER, lore='0', ink_drops='1', ink_total='0', ink_available='0')
    G.add_node('p2', type=NodeType.PLAYER, lore='0', ink_drops='1', ink_total='0', ink_available='0')

    # It's p1's turn, main phase
    G.add_edge('game', 'p1', label=Edge.CURRENT_TURN)
    G.add_node('step.p1.main', type=NodeType.STEP, player='p1', step=Step.MAIN)
    G.add_edge('game', 'step.p1.main', label=Edge.CURRENT_STEP)

    return G


def add_character(G: nx.MultiDiGraph, player: str, name: str, *,
                  zone: str = Zone.PLAY,
                  exerted: bool = False,
                  damage: int = 0,
                  entered_play: int = 0) -> str:
    """
    Add a character to the game.

    Args:
        G: Game graph
        player: "p1" or "p2"
        name: Card name (normalized, e.g., "stitch_rock_star")
        zone: Where the card is (hand, play, ink, discard)
        exerted: Is the character exerted?
        damage: Damage counters on the character
        entered_play: Turn number when character entered play (0 = before game started, i.e., "dry")

    Returns:
        Node ID for the character (e.g., "p1.stitch_rock_star.a")
    """
    node_id = f"{player}.{name}.a"

    G.add_node(node_id,
        type=NodeType.CARD,
        label=name,
        zone=zone,
        exerted='1' if exerted else '0',
        damage=str(damage),
        entered_play=str(entered_play)
    )

    # Create ability nodes for printed keywords when card is in play
    if zone == Zone.PLAY:
        card_db = get_card_db()
        card_data = card_db.get(name, {})
        create_printed_abilities(G, node_id, card_data, entered_play)

    return node_id


def make_state(G: nx.MultiDiGraph) -> LorcanaState:
    """Wrap a graph in a LorcanaState (with empty decks)."""
    return LorcanaState(G, deck1_ids=[], deck2_ids=[])


def give_ink(G: nx.MultiDiGraph, player: str, amount: int):
    """Give a player ink to spend."""
    G.nodes[player]['ink_total'] = str(amount)
    G.nodes[player]['ink_available'] = str(amount)


def set_turn(G: nx.MultiDiGraph, turn_number: int):
    """Set the current turn number."""
    G.nodes['game']['turn'] = str(turn_number)
