#!/usr/bin/env python3
"""
Build per-card trajectory files from game states.

Replays game tree in-memory (fast) rather than reading each game.dot from disk.
Creates trajectories/{card_name}.txt showing each card's journey with features.

OUTPUT FORMAT:
    Tab-separated values, one row per card per game state.
    Header row lists all feature names + action + score.
    Human-readable values, no normalization.

USAGE:
    python bin/build-trajectories.py output/459b
"""
import json
import sys
from pathlib import Path
from collections import defaultdict

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.core.file_store import FileStore
from lib.core.graph import can_edges, get_edge_attr
from lib.core.diff import diff_graphs
from lib.lorcana.state import LorcanaState
from lib.lorcana.game_api import GameSession
from lib.features.extractor import extract_all_cards, get_feature_names

_OUTCOMES_JSON = "outcomes.json"


def get_score(state_path: Path, owner: str) -> str:
    """
    Get owner's win rate from outcomes.json at state_path.

    Returns empty string if no outcomes data available.
    """
    outcomes_file = state_path / _OUTCOMES_JSON
    if not outcomes_file.exists():
        return ""

    try:
        with open(outcomes_file) as f:
            data = json.load(f)

        p1_wins = len(data.get("p1_wins", []))
        p2_wins = len(data.get("p2_wins", []))
        total = p1_wins + p2_wins

        if total == 0:
            return ""

        owner_wins = p1_wins if owner == "p1" else p2_wins
        return f"{owner_wins / total:.2f}"
    except (json.JSONDecodeError, IOError):
        return ""


def get_action_description(state: LorcanaState, action_id: str) -> str:
    """Get human-readable description for an action."""
    for u, v, key, action_type, edge_action_id in can_edges(state.graph):
        if edge_action_id == action_id:
            return get_edge_attr(state.graph, u, v, key, "description", f"{action_type}:{u}")
    return "unknown"


def traverse_and_extract(
    session: GameSession,
    fs_path: Path,
    action: str,
    game_path: str,
    diff: str,
    trajectories: dict[str, list[dict]]
) -> None:
    """
    DFS traverse game tree, extracting features at each state.

    Args:
        session: GameSession positioned at current state
        fs_path: Filesystem path corresponding to current state
        action: Action that led to this state
        game_path: Path from seed root (e.g., "0/1/2")
        diff: Semicolon-separated diff lines from parent state
        trajectories: Dict to accumulate results
    """
    state = session.get_state()

    # Extract features for all cards at this state
    for features in extract_all_cards(state.graph):
        card_id = features['card_id']
        card_name = features['card_name']
        owner = features['owner']

        # Only emit row if this card is involved in the action or diff
        # (active, target, or side effect)
        if card_id not in action and card_id not in diff:
            continue

        features['action'] = action
        features['path'] = game_path
        features['diff'] = diff
        features['score'] = get_score(fs_path, owner)

        trajectories[card_name].append(features)

    # Find child directories (actions taken - short base-36 names)
    children = []
    for child in fs_path.iterdir():
        if child.is_dir() and is_action_dir(child.name):
            children.append(child)

    # Process children in sorted order for determinism
    for child in sorted(children, key=lambda p: p.name):
        action_id = child.name
        action_desc = get_action_description(state, action_id)

        # Save parent state for diffing
        parent_graph = state.graph
        parent_key = session.current_key

        if session.apply_action(action_id):
            # Compute diff
            child_state = session.get_state()
            diff_lines = diff_graphs(parent_graph, child_state.graph)
            child_diff = "; ".join(diff_lines)

            # Build child path
            child_path = f"{game_path}/{action_id}" if game_path else action_id

            traverse_and_extract(session, child, action_desc, child_path, child_diff, trajectories)
            session.goto(parent_key)


def is_action_dir(name: str) -> bool:
    """Check if directory name looks like an action ID (short base-36)."""
    return len(name) <= 2 and name[0:1].isalnum()


def is_seed_dir(path: Path) -> bool:
    """Check if directory is a seed (has game.dot with cards)."""
    game_file = path / "game.dot"
    return game_file.exists() and len(path.name) > 2


def build_trajectories(matchdir: Path) -> dict[str, list[dict]]:
    """
    Replay game tree in memory and build per-card trajectories.

    Handles matchup structure: matchdir contains seed directories,
    each seed has its own game tree.

    Returns:
        dict mapping card_name -> list of feature dicts
    """
    trajectories = defaultdict(list)
    file_store = FileStore()

    # Find all seed directories
    seeds = [d for d in matchdir.iterdir() if d.is_dir() and is_seed_dir(d)]

    if not seeds:
        # No seeds - maybe matchdir is itself a seed
        if (matchdir / "game.dot").exists():
            seeds = [matchdir]

    for seed_path in sorted(seeds):
        print(f"  Processing seed {seed_path.name}...")

        # Load seed state from disk (once per seed)
        seed_state = file_store.load_state(seed_path, LorcanaState)

        # Create in-memory session for this seed
        session = GameSession(seed_state, root_key=str(seed_path))

        # DFS traverse this seed's game tree
        traverse_and_extract(session, seed_path, "initial", "", "", trajectories)

    return trajectories


def write_trajectories(matchdir: Path, trajectories: dict[str, list[dict]]):
    """Write trajectory files."""
    traj_dir = matchdir / "trajectories"
    traj_dir.mkdir(exist_ok=True)

    # Get column names (feature names + action + path + diff + score)
    columns = get_feature_names() + ['action', 'path', 'diff', 'score']

    for card_name, rows in trajectories.items():
        outfile = traj_dir / f"{card_name}.txt"
        with open(outfile, "w") as f:
            # Header
            f.write("\t".join(columns) + "\n")

            # Data rows
            for row in rows:
                values = [str(row.get(col, "")) for col in columns]
                f.write("\t".join(values) + "\n")


def main(matchdir: str):
    matchdir = Path(matchdir)
    if not matchdir.exists():
        print(f"Error: {matchdir} does not exist", file=sys.stderr)
        sys.exit(1)

    print(f"Building trajectories from {matchdir}...")
    trajectories = build_trajectories(matchdir)

    print(f"Found {len(trajectories)} unique cards")
    total_rows = sum(len(rows) for rows in trajectories.values())
    print(f"Total data points: {total_rows}")

    write_trajectories(matchdir, trajectories)
    print(f"Wrote trajectory files to {matchdir}/trajectories/")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: build-trajectories.py <matchdir>", file=sys.stderr)
        print("  e.g., build-trajectories.py output/459b", file=sys.stderr)
        sys.exit(1)
    main(sys.argv[1])
