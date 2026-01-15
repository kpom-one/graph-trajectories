"""
Lorcana game setup - initialization and shuffling.
"""
import hashlib
import random
import re
import shutil
from pathlib import Path

from lib.core.graph import load_dot, save_dot
from lib.core.file_store import FileStore
from lib.core.seed import parse_seed
from lib.core.navigation import format_actions
from lib.lorcana.cards import get_card_db
from lib.lorcana.state import LorcanaState
from lib.lorcana.compute import compute_all

DECK1_SOURCE = "deck1.txt"
DECK2_SOURCE = "deck2.txt"


def normalize_card_name(name: str) -> str:
    """Convert 'Tinker Bell - Giant Fairy' to 'tinker_bell_giant_fairy'."""
    return name.lower().replace(' - ', '_').replace(' ', '_').replace('-', '_')


def build_deck(deck_txt: Path) -> list[str]:
    """
    Build unshuffled deck from decklist.

    Returns:
        List of 60 card IDs in decklist order
    """
    cards = []
    with open(deck_txt) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            match = re.match(r"(\d+)\s+(.+)", line)
            if match:
                cards.append((int(match.group(1)), match.group(2).strip()))

    deck = []
    for count, name in cards:
        base = normalize_card_name(name)
        for i in range(count):
            suffix = chr(ord('a') + i)
            deck.append(f"{base}.{suffix}")

    return deck


def build_shuffled_deck(deck_txt: Path, shuffle_seed: str, hand_indices: list[int] | None = None) -> list[str]:
    """
    Build shuffled deck from decklist.

    Args:
        deck_txt: Path to decklist.txt (format: "4 Tinker Bell - Giant Fairy")
        shuffle_seed: Seed string for deterministic shuffling
        hand_indices: Optional 7 indices selecting starting hand from unique cards.
                      If None, does true random shuffle.

    Returns:
        List of 60 card IDs (top 7 become hand)
    """
    # Parse decklist
    cards = []
    with open(deck_txt) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            match = re.match(r"(\d+)\s+(.+)", line)
            if match:
                cards.append((int(match.group(1)), match.group(2).strip()))

    # Build card map
    card_map = {}
    for count, name in cards:
        base = normalize_card_name(name)
        card_map[name] = []
        for i in range(count):
            suffix = chr(ord('a') + i)
            card_map[name].append(f"{base}.{suffix}")

    rng = random.Random(shuffle_seed)

    if hand_indices is None:
        # True random shuffle
        deck = [card_id for ids in card_map.values() for card_id in ids]
        rng.shuffle(deck)
        return deck

    # Hand-spec mode: specific cards go to hand first
    unique_cards = [name for count, name in cards]
    hand_cards = []
    for idx in hand_indices:
        if idx >= len(unique_cards):
            raise ValueError(f"Hand index {idx} out of range (deck has {len(unique_cards)} unique cards)")

        card_name = unique_cards[idx]
        if not card_map[card_name]:
            raise ValueError(f"Not enough copies of '{card_name}' for hand")

        hand_cards.append(card_map[card_name].pop(0))

    remaining = [card_id for ids in card_map.values() for card_id in ids]
    rng.shuffle(remaining)

    return hand_cards + remaining


def init_game(deck1_txt: str | Path, deck2_txt: str | Path) -> str:
    """
    Initialize a game from deck text files.

    Args:
        deck1_txt: Path to P1's decklist.txt
        deck2_txt: Path to P2's decklist.txt

    Returns:
        matchup_hash: Directory name for this matchup
    """
    deck1_txt = Path(deck1_txt)
    deck2_txt = Path(deck2_txt)

    # Generate hash from deck contents
    matchup_hash = _generate_matchup_hash(deck1_txt, deck2_txt)
    matchdir = Path("output") / matchup_hash
    matchdir.mkdir(parents=True, exist_ok=True)

    # Load template
    G = load_dot(Path("data/template.dot"))

    # Preload card database (singleton)
    get_card_db()

    # Copy deck files to matchup directory for reference
    shutil.copy(deck1_txt, matchdir / DECK1_SOURCE)
    shutil.copy(deck2_txt, matchdir / DECK2_SOURCE)

    # Compute initial legal actions
    compute_all(G)

    # Save initial game state
    save_dot(G, matchdir / "game.dot")

    return matchup_hash


def _generate_matchup_hash(deck1: Path, deck2: Path) -> str:
    """Generate 4-char hash from deck contents."""
    content1 = deck1.read_text()
    content2 = deck2.read_text()
    combined = content1 + content2
    return hashlib.md5(combined.encode()).hexdigest()[:4]


def shuffle_and_draw(matchdir: str | Path, seed: str) -> str:
    """
    Shuffle decks and draw starting hands (7 cards each).

    Creates output/<matchdir>/<seed>/ with:
    - deck1.dek (53 cards remaining)
    - deck2.dek (53 cards remaining)
    - game.dot (14 cards in hands)

    Args:
        matchdir: Matchup directory (e.g., "output/b013")
        seed: Either a simple seed string (true random shuffle)
              or hand-spec format (xxxxxxx.xxxxxxx.xx)

    Returns:
        Seed (for display)
    """
    matchdir = Path(matchdir)
    store = FileStore()

    # Load parent state
    parent = store.load_state(matchdir, LorcanaState)

    # Build shuffled decks from .txt files
    deck1_txt = matchdir / DECK1_SOURCE
    deck2_txt = matchdir / DECK2_SOURCE

    if '.' in seed:
        # Hand-spec format
        hand_spec = parse_seed(seed)
        if not hand_spec:
            raise ValueError(f"Invalid hand-spec seed format: {seed}")
        deck1_ids = build_shuffled_deck(deck1_txt, seed, hand_spec['p1_hand'])
        deck2_ids = build_shuffled_deck(deck2_txt, seed, hand_spec['p2_hand'])
    else:
        # Simple seed - true random shuffle
        deck1_ids = build_shuffled_deck(deck1_txt, seed + "_p1")
        deck2_ids = build_shuffled_deck(deck2_txt, seed + "_p2")

    # Create new state with decks
    state = LorcanaState(parent.graph, deck1_ids, deck2_ids)

    # Draw hands
    state.draw(player=1, count=7)
    state.draw(player=2, count=7)

    # Recompute legal actions
    compute_all(state.graph)

    # Save to seed path
    store.save_state(state, matchdir / seed, format_actions_fn=format_actions, action_taken="initial")

    return seed
