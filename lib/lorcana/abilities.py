"""
Ability node management.

Creates and removes ability nodes that represent active effects on cards.
"""
from lib.lorcana.constants import Keyword, Edge, NodeType


def create_printed_abilities(G, card_node: str, card_data: dict, turn: int) -> None:
    """Create ability nodes for printed keywords on a card entering play."""
    for ability in card_data.get('abilities', []):
        keyword = ability.get('keyword')
        if keyword == 'Rush':
            create_ability(G, card_node, Keyword.RUSH, turn)
        elif keyword == 'Evasive':
            create_ability(G, card_node, Keyword.EVASIVE, turn)


def create_ability(G, card_node: str, keyword: str, turn: int) -> str:
    """
    Create an ability node with effect and source edges.

    Args:
        G: Game graph
        card_node: Card this ability belongs to
        keyword: Keyword constant (e.g., Keyword.RUSH)
        turn: Current turn number

    Returns:
        Ability node ID
    """
    # Generate unique ability ID: {keyword}.t{turn}.{seq}
    keyword_lower = keyword.lower()
    seq = _next_ability_seq(G, keyword_lower, turn)
    ability_id = f"{keyword_lower}.t{turn}.{seq}"

    # Create ability node
    G.add_node(ability_id, type=NodeType.ABILITY)

    # Create effect edge: ability --[KEYWORD]--> card
    G.add_edge(ability_id, card_node, label=keyword)

    # Create source edge: ability --[SOURCE]--> card
    G.add_edge(ability_id, card_node, label=Edge.SOURCE)

    return ability_id


def _next_ability_seq(G, keyword: str, turn: int) -> int:
    """Get next sequence number for ability ID uniqueness."""
    prefix = f"{keyword}.t{turn}."
    seq = 1
    while f"{prefix}{seq}" in G.nodes():
        seq += 1
    return seq
