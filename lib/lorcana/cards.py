"""
Card database singleton - loaded once, reused everywhere.

Also provides stat calculation helpers.
"""
import json
from lib.core.graph import get_node_attr

_CARD_DB = None


def normalize_card_name(name: str) -> str:
    """Convert 'Tinker Bell - Giant Fairy' to 'tinker_bell_giant_fairy'."""
    return name.lower().replace(' - ', '_').replace(' ', '_').replace('-', '_')


def get_card_db() -> dict:
    """
    Get card database indexed by normalized name (lazy loaded singleton).

    Different printings of the same card may exist with different IDs,
    but we just pick the first match since stats/abilities are identical.

    Returns:
        dict mapping normalized_card_name -> card data
    """
    global _CARD_DB
    if _CARD_DB is None:
        with open("data/cards.json") as f:
            data = json.load(f)

        _CARD_DB = {}
        for card in data["cards"]:
            normalized = normalize_card_name(card["fullName"])
            # First match wins (different printings don't matter)
            if normalized not in _CARD_DB:
                # Normalize type to lowercase for consistency with constants
                card = card.copy()
                card['type'] = card['type'].lower()
                _CARD_DB[normalized] = card

    return _CARD_DB


def get_strength(state, card_node: str) -> int:
    """
    Get effective strength of a character.

    Phase 1: Returns base strength from card DB.
    Phase 2+: Will walk effect edges for modifiers.

    Args:
        state: Game state
        card_node: Card node ID

    Returns:
        Effective strength (minimum 0)
    """
    card_db = get_card_db()
    card_name = get_node_attr(state.graph, card_node, 'label')
    card_data = card_db[card_name]

    # Base strength from card data
    base_strength = card_data.get('strength', 0)

    # TODO Phase 2: Walk APPLIES_TO edges for STR modifiers
    # modifiers = sum(effect modifiers)

    return max(0, base_strength)


def get_willpower(state, card_node: str) -> int:
    """
    Get effective willpower of a character.

    Phase 1: Returns base willpower from card DB.
    Phase 2+: Will walk effect edges for modifiers.

    Args:
        state: Game state
        card_node: Card node ID

    Returns:
        Effective willpower (minimum 0)
    """
    card_db = get_card_db()
    card_name = get_node_attr(state.graph, card_node, 'label')
    card_data = card_db[card_name]

    # Base willpower from card data
    base_willpower = card_data.get('willpower', 0)

    # TODO Phase 2: Walk APPLIES_TO edges for willpower modifiers
    # modifiers = sum(effect modifiers)

    return max(0, base_willpower)
