"""
Helper functions for Lorcana game logic.

Common patterns used across mechanics.
"""
from typing import NamedTuple
from lib.core.graph import edges_by_label, get_node_attr
from lib.lorcana.cards import get_card_db
from lib.lorcana.constants import Zone, Keyword, Edge, Action, NodeType


class ActionEdge(NamedTuple):
    """
    Represents a potential action in the game.

    Used by compute_can_* functions to return available actions.
    """
    src: str          # Source node (e.g., card performing action)
    dst: str          # Target node (e.g., player, or defender for challenge)
    action_type: str  # Type of action (CAN_CHALLENGE, CAN_QUEST, etc.)
    description: str  # Human-readable description for UI
    metadata: dict | None = None  # Action-specific attributes (e.g., {'exerted': True} for Bodyguard)


def get_player_step(player: str, step: str) -> str:
    """
    Get step node ID for a player.

    Args:
        player: Player ID ("p1" or "p2")
        step: Step constant (Step.READY, Step.SET, Step.DRAW, Step.MAIN, Step.END)

    Returns:
        Step node ID (e.g., "step.p1.main")
    """
    return f"step.{player}.{step}"


def get_game_context(G):
    """
    Get common game state information.

    Returns dict with current player, opponent, and turn.
    Returns None if no current player (shouldn't happen in valid game state).

    Returns:
        dict with keys:
            - player: Current player ID ("p1" or "p2")
            - opponent: Opponent player ID
            - current_turn: Turn number (int)
    """
    edges = edges_by_label(G, Edge.CURRENT_TURN)
    if not edges:
        return None

    game, player, _ = edges[0]
    opponent = "p2" if player == "p1" else "p1"
    current_turn = int(get_node_attr(G, 'game', 'turn', 0))

    return {
        'player': player,
        'opponent': opponent,
        'current_turn': current_turn,
    }


def get_card_data(G, card_node: str):
    """
    Get card database entry for a card node.

    Args:
        G: Game graph
        card_node: Card node ID (e.g., "p1.tinker_bell_giant_fairy.a")

    Returns:
        Card data dict from database

    Raises:
        KeyError: If card not found in database (data is broken)
    """
    card_db = get_card_db()
    card_name = get_node_attr(G, card_node, 'label')
    return card_db[card_name]  # Fail fast if missing


def cards_in_zone(G, player: str, zone: str) -> list[str]:
    """
    Get all cards in a player's zone.

    Args:
        G: Game graph
        player: Player ID ("p1" or "p2")
        zone: Zone kind (Zone.HAND, Zone.PLAY, etc.)

    Returns:
        List of card node IDs in that zone
    """
    return [n for n in G.nodes()
            if n.startswith(f'{player}.')
            and get_node_attr(G, n, 'zone') == zone]


def has_keyword(G, card_node: str, keyword: str) -> bool:
    """
    Check if a card has a keyword edge pointing to it.

    Keywords are represented as edges: source --KEYWORD--> card
    For printed keywords, source = card (self-loop).
    For granted keywords, source = granting card/effect.

    Args:
        G: Game graph
        card_node: Card node ID
        keyword: Keyword edge label (e.g., Keyword.RUSH)

    Returns:
        True if any edge with that label points to the card
    """
    for u, v, data in G.in_edges(card_node, data=True):
        if data.get('label') == keyword:
            return True
    return False


def card_data_has_keyword(card_data: dict, keyword: str) -> bool:
    """
    Check if card data contains a specific keyword.

    Use this for cards not yet in play (e.g., in hand) where ability
    nodes don't exist yet. For cards in play, use has_keyword() instead.

    Args:
        card_data: Card data dict from card database
        keyword: Keyword name as it appears in card data (e.g., 'Bodyguard', 'Shift')

    Returns:
        True if card has the keyword in its abilities
    """
    for ability in card_data.get('abilities', []):
        if ability.get('keyword') == keyword:
            return True
    return False
