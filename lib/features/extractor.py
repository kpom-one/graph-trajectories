"""
Feature Extractor for Card Trajectories

Extracts human-readable features from game state for ML training.

DESIGN PRINCIPLES:
- Each feature is a pure function: (graph, card_node) -> value
- Features return raw values (int, str, bool) - NO normalization
- Features describe CURRENT STATE, not predictions or counterfactuals
- Features should be meaningful without knowing game rules

DO:
- Add features that describe observable state
- Use human-readable values (zone="hand", not zone=2)
- Keep features independent (no feature that depends on another)
- Document what the feature means and why it matters

DON'T:
- Compute derived "can_X" features (let model learn combinations)
- Normalize or scale values (do that in training pipeline)
- Add features that require simulating future states
- Add features specific to one card/ability (keep generic)

ADDING A FEATURE:
1. Write a function: def feature_name(graph, card_node, ctx) -> value
2. Add docstring explaining what and why
3. Add to CARD_FEATURES or GAME_FEATURES list
4. That's it

FEATURE FUNCTION SIGNATURE:
    def my_feature(graph, card_node: str, ctx: dict) -> str | int | bool

    ctx contains precomputed values:
        - owner: "p1" or "p2"
        - opponent: "p2" or "p1"
        - turn: int
        - current_player: "p1" or "p2"
"""
from lib.core.graph import edges_by_label, get_node_attr
from lib.lorcana.helpers import cards_in_zone
from lib.lorcana.constants import Zone, Edge


# =============================================================================
# CARD FEATURES - Describe the card's own state
# =============================================================================

def card_id(graph, card_node: str, ctx: dict) -> str:
    """
    The card's unique identifier.

    Example: "p1.mulan_disguised_soldier.a"

    Useful for: Grouping trajectories by card instance.
    """
    return card_node


def card_name(graph, card_node: str, ctx: dict) -> str:
    """
    The card's base name (without owner prefix or copy suffix).

    Example: "mulan_disguised_soldier"

    Useful for: Learning card-specific patterns across copies.
    """
    return get_node_attr(graph, card_node, 'label', '')


def owner(graph, card_node: str, ctx: dict) -> str:
    """
    Which player owns this card.

    Values: "p1" or "p2"

    Useful for: Knowing whose perspective this is.
    """
    return ctx['owner']


def zone(graph, card_node: str, ctx: dict) -> str:
    """
    What zone the card is currently in.

    Values: "hand", "play", "ink", "discard", "deck", "unknown"

    Useful for: Understanding card's current position/role.
    """
    return get_node_attr(graph, card_node, 'zone', 'unknown')


def is_exerted(graph, card_node: str, ctx: dict) -> int:
    """
    Whether the card is exerted (tapped).

    Values: 0 (ready) or 1 (exerted)

    Useful for: Knowing if card can take actions or is vulnerable.
    """
    return int(get_node_attr(graph, card_node, 'exerted', '0'))


def damage(graph, card_node: str, ctx: dict) -> int:
    """
    How much damage the card has taken.

    Values: 0+

    Useful for: Knowing how close to being banished.
    """
    return int(get_node_attr(graph, card_node, 'damage', '0'))


def turns_in_play(graph, card_node: str, ctx: dict) -> int:
    """
    How many turns the card has been in play.

    Values: -1 (not in play), 0 (just entered), 1+ (been in play)

    Useful for: Knowing if card can act (summoning sickness).
    Calculated as: current_turn - entered_play_turn
    """
    entered = get_node_attr(graph, card_node, 'entered_play', None)
    if entered is None:
        return -1
    return ctx['turn'] - int(entered)


# =============================================================================
# OWNER FEATURES - Describe the card owner's state
# =============================================================================

def owner_lore(graph, card_node: str, ctx: dict) -> int:
    """
    Owner's current lore (victory points).

    Values: 0-20+

    Useful for: Understanding game progress from owner's perspective.
    """
    return int(get_node_attr(graph, ctx['owner'], 'lore', '0'))


def owner_ink(graph, card_node: str, ctx: dict) -> int:
    """
    Owner's currently available ink (mana).

    Values: 0+

    Useful for: Knowing what owner can afford to play.
    """
    return int(get_node_attr(graph, ctx['owner'], 'ink_available', '0'))


def owner_ink_total(graph, card_node: str, ctx: dict) -> int:
    """
    Owner's total ink pool size.

    Values: 0+

    Useful for: Understanding owner's ramp/development.
    """
    return int(get_node_attr(graph, ctx['owner'], 'ink_total', '0'))


def owner_hand_size(graph, card_node: str, ctx: dict) -> int:
    """
    Number of cards in owner's hand.

    Values: 0+

    Useful for: Understanding owner's options/resources.
    """
    return len(cards_in_zone(graph, ctx['owner'], Zone.HAND))


def owner_board_size(graph, card_node: str, ctx: dict) -> int:
    """
    Number of cards in owner's play zone.

    Values: 0+

    Useful for: Understanding owner's board presence.
    """
    return len(cards_in_zone(graph, ctx['owner'], Zone.PLAY))


# =============================================================================
# OPPONENT FEATURES - Describe the opponent's state
# =============================================================================

def opp_lore(graph, card_node: str, ctx: dict) -> int:
    """
    Opponent's current lore.

    Values: 0-20+

    Useful for: Understanding threat level / game progress.
    """
    return int(get_node_attr(graph, ctx['opponent'], 'lore', '0'))


def opp_ink(graph, card_node: str, ctx: dict) -> int:
    """
    Opponent's currently available ink.

    Values: 0+

    Useful for: Predicting what opponent might do.
    """
    return int(get_node_attr(graph, ctx['opponent'], 'ink_available', '0'))


def opp_ink_total(graph, card_node: str, ctx: dict) -> int:
    """
    Opponent's total ink pool size.

    Values: 0+

    Useful for: Understanding opponent's development.
    """
    return int(get_node_attr(graph, ctx['opponent'], 'ink_total', '0'))


def opp_hand_size(graph, card_node: str, ctx: dict) -> int:
    """
    Number of cards in opponent's hand.

    Values: 0+

    Useful for: Understanding opponent's options.
    """
    return len(cards_in_zone(graph, ctx['opponent'], Zone.HAND))


def opp_board_size(graph, card_node: str, ctx: dict) -> int:
    """
    Number of cards in opponent's play zone.

    Values: 0+

    Useful for: Understanding opponent's threats.
    """
    return len(cards_in_zone(graph, ctx['opponent'], Zone.PLAY))


# =============================================================================
# GAME FEATURES - Describe overall game state
# =============================================================================

def turn(graph, card_node: str, ctx: dict) -> int:
    """
    Current turn number.

    Values: 0+

    Useful for: Understanding game phase (early/mid/late).
    """
    return ctx['turn']


def current_player(graph, card_node: str, ctx: dict) -> str:
    """
    Whose turn it is.

    Values: "p1" or "p2"

    Useful for: Context about who is acting.
    """
    return ctx['current_player']


def is_owners_turn(graph, card_node: str, ctx: dict) -> int:
    """
    Whether it's the card owner's turn.

    Values: 0 or 1

    Useful for: Knowing if owner can take actions.
    """
    return 1 if ctx['current_player'] == ctx['owner'] else 0


def lore_diff(graph, card_node: str, ctx: dict) -> int:
    """
    Owner's lore minus opponent's lore.

    Values: -20 to +20

    Useful for: Understanding who's winning.
    """
    owner_l = int(get_node_attr(graph, ctx['owner'], 'lore', '0'))
    opp_l = int(get_node_attr(graph, ctx['opponent'], 'lore', '0'))
    return owner_l - opp_l


# =============================================================================
# FEATURE REGISTRY - Add/remove features here
# =============================================================================

# All features to extract, in order they'll appear in output
FEATURES = [
    # Card identity
    card_id,
    card_name,
    owner,

    # Card state
    zone,
    is_exerted,
    damage,
    turns_in_play,

    # Owner state
    owner_lore,
    owner_ink,
    owner_ink_total,
    owner_hand_size,
    owner_board_size,

    # Opponent state
    opp_lore,
    opp_ink,
    opp_ink_total,
    opp_hand_size,
    opp_board_size,

    # Game state
    turn,
    current_player,
    is_owners_turn,
    lore_diff,
]


def get_feature_names() -> list[str]:
    """Get list of feature names in order."""
    return [f.__name__ for f in FEATURES]


def build_context(graph) -> dict:
    """Build context dict with precomputed values."""
    # Get current player
    turn_edges = edges_by_label(graph, Edge.CURRENT_TURN)
    current = turn_edges[0][1] if turn_edges else "p1"

    return {
        'turn': int(get_node_attr(graph, 'game', 'turn', '0')),
        'current_player': current,
    }


def extract_features(graph, card_node: str) -> dict:
    """
    Extract all features for a card at a given game state.

    Args:
        graph: NetworkX game graph
        card_node: Card node ID (e.g., "p1.mulan_disguised_soldier.a")

    Returns:
        dict mapping feature_name -> value
    """
    # Build context
    ctx = build_context(graph)

    # Add owner/opponent based on card
    ctx['owner'] = 'p1' if card_node.startswith('p1.') else 'p2'
    ctx['opponent'] = 'p2' if ctx['owner'] == 'p1' else 'p1'

    # Extract each feature
    result = {}
    for feature_fn in FEATURES:
        result[feature_fn.__name__] = feature_fn(graph, card_node, ctx)

    return result


def extract_all_cards(graph) -> list[dict]:
    """
    Extract features for all card nodes in the graph.

    Returns:
        List of feature dicts, one per card
    """
    results = []

    for node in graph.nodes():
        # Card nodes match: p1.something.a or p2.something.b
        if node.startswith(('p1.', 'p2.')) and node.count('.') == 2:
            results.append(extract_features(graph, node))

    return results
