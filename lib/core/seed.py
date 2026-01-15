"""
Generic seed parsing utilities.

Seed format: xxxxxxx.xxxxxxx.xx
- First 7 chars (0-9a-z): First player's hand indices
- Second 7 chars (0-9a-z): Second player's hand indices
- Last 2 chars: RNG suffix for shuffling remainder

Character mapping: 0-9 → 0-9, a-z → 10-35
"""


def parse_seed(seed: str) -> dict | None:
    """
    Parse hand-spec seed format into indices.

    Args:
        seed: Hand-spec string (format: "xxxxxxx.xxxxxxx.xx")

    Returns:
        dict with 'p1_hand', 'p2_hand' (lists of indices), 'shuffle_seed'
        None if invalid format
    """
    parts = seed.split('.')
    if len(parts) != 3:
        return None

    p1_spec, p2_spec, suffix = parts
    if len(p1_spec) != 7 or len(p2_spec) != 7 or len(suffix) != 2:
        return None

    p1_hand = [char_to_index(c) for c in p1_spec]
    p2_hand = [char_to_index(c) for c in p2_spec]

    if None in p1_hand or None in p2_hand:
        return None

    return {
        'p1_hand': p1_hand,
        'p2_hand': p2_hand,
        'shuffle_seed': seed
    }


def char_to_index(c: str) -> int | None:
    """
    Convert character to index.

    Args:
        c: Character (0-9 or a-z)

    Returns:
        Index 0-35, or None if invalid
    """
    if '0' <= c <= '9':
        return ord(c) - ord('0')
    elif 'a' <= c <= 'z':
        return ord(c) - ord('a') + 10
    return None
