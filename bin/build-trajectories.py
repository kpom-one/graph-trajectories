#!/usr/bin/env python3
"""
Extract per-card trajectory files from an episode.

Each card gets one .jsonl file with exactly N lines (one per state).
Each line contains: node attributes, edges, and global game state.

Usage:
    python bin/build-trajectories.py output/episodes/abc.episode
"""
import sys
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.core.graph import load_dot


def clean_value(val):
    """Strip extra quotes from DOT-parsed values."""
    if isinstance(val, str):
        return val.strip('"')
    return val


def clean_dict(d: dict) -> dict:
    """Clean all values in a dict."""
    return {k: clean_value(v) for k, v in d.items()}


def parse_actions_from_history(episode_path: Path) -> list[str]:
    """Extract action names from history.txt."""
    history_path = episode_path / "history.txt"
    actions = []

    if not history_path.exists():
        return actions

    content = history_path.read_text()
    for match in re.finditer(r"# action: (.+)", content):
        actions.append(match.group(1).strip())

    return actions


def extract_game_state(graph, state_index: int) -> dict:
    """Extract global game state at a given state index."""
    game_node = f"game@{state_index}"
    p1_node = f"p1@{state_index}"
    p2_node = f"p2@{state_index}"

    game_attrs = clean_dict(graph.nodes.get(game_node, {}))
    p1_attrs = clean_dict(graph.nodes.get(p1_node, {}))
    p2_attrs = clean_dict(graph.nodes.get(p2_node, {}))

    # Find current player from CURRENT_TURN edge
    current_player = None
    for u, v, data in graph.edges(data=True):
        if u == game_node and data.get("label") == "CURRENT_TURN":
            current_player = v.replace(f"@{state_index}", "")
            break

    return {
        "turn": game_attrs.get("turn", "0"),
        "game_over": game_attrs.get("game_over", "0"),
        "winner": game_attrs.get("winner"),
        "current_player": current_player,
        "p1_lore": p1_attrs.get("lore", "0"),
        "p2_lore": p2_attrs.get("lore", "0"),
    }


def extract_node_state(graph, base_id: str, state_index: int) -> dict | None:
    """Extract a node's state at a given state index."""
    node_id = f"{base_id}@{state_index}"

    if node_id not in graph.nodes:
        return None

    return clean_dict(graph.nodes[node_id])


def extract_node_edges(graph, base_id: str, state_index: int) -> list[str]:
    """Extract outgoing action edge types for a node."""
    node_id = f"{base_id}@{state_index}"

    edges = []
    for u, v, data in graph.edges(data=True):
        if u == node_id:
            if data.get("label") == "next":
                continue
            action_type = clean_value(data.get("action_type", ""))
            if action_type:
                edges.append(action_type)

    return edges


def determine_role(action: str, card_id: str, prev_state: dict | None, curr_state: dict | None) -> str:
    """Determine the card's role in this action.

    Returns: "actor" | "target" | "byproduct" | "observer"
    """
    # Check if this card is the actor (action contains card_id before any ->)
    if "->" in action:
        actor_part = action.split("->")[0]
        target_part = action.split("->")[1]
        if card_id in actor_part:
            return "actor"
        if card_id in target_part:
            return "target"
    elif card_id in action:
        return "actor"

    # Check if state changed (byproduct)
    if prev_state and curr_state:
        if (prev_state.get("zone") != curr_state.get("zone") or
            prev_state.get("exerted") != curr_state.get("exerted") or
            prev_state.get("damage") != curr_state.get("damage")):
            return "byproduct"
    elif prev_state is None and curr_state is not None:
        # Card just appeared (drawn)
        return "byproduct"
    elif prev_state is not None and curr_state is None:
        # Card just disappeared (banished/inked)
        return "byproduct"

    return "observer"


def get_all_card_ids(graph) -> set[str]:
    """Get all unique card base IDs (without @N suffix)."""
    card_ids = set()

    for node, attrs in graph.nodes(data=True):
        if attrs.get("type") == "Card" and "@" in node:
            base_id = node.rsplit("@", 1)[0]
            card_ids.add(base_id)

    return card_ids


def get_max_state_index(graph) -> int:
    """Find the highest state index in the graph."""
    max_idx = 0
    for node in graph.nodes():
        if "@" in node:
            try:
                idx = int(node.rsplit("@", 1)[1])
                max_idx = max(max_idx, idx)
            except ValueError:
                pass
    return max_idx


def build_trajectories(episode_path: Path) -> Path:
    """
    Build trajectory files for all cards in an episode.

    Returns path to trajectories directory.
    """
    episode_path = Path(episode_path)
    graph_path = episode_path / "graph.dot"

    if not graph_path.exists():
        raise FileNotFoundError(f"No graph.dot in {episode_path}")

    # Load the episode graph
    graph = load_dot(graph_path)

    # Get action names from history
    actions = parse_actions_from_history(episode_path)

    # Get all card IDs and state count
    card_ids = get_all_card_ids(graph)
    max_state = get_max_state_index(graph)
    num_states = max_state + 1

    # Pad actions if needed
    while len(actions) < num_states:
        actions.append("unknown")

    # Create trajectories directory
    traj_dir = episode_path / "trajectories"
    traj_dir.mkdir(exist_ok=True)

    # Write game.jsonl (global state per action)
    with open(traj_dir / "game.jsonl", "w") as f:
        for state_idx in range(num_states):
            game_state = extract_game_state(graph, state_idx)
            record = {"action": actions[state_idx], "state": state_idx, **game_state}
            f.write(json.dumps(record) + "\n")

    # Build trajectory for each card
    for card_id in sorted(card_ids):
        traj_file = traj_dir / f"{card_id}.jsonl"

        with open(traj_file, "w") as f:
            prev_exists = False
            prev_state = None

            for state_idx in range(num_states):
                node_state = extract_node_state(graph, card_id, state_idx)
                edges = extract_node_edges(graph, card_id, state_idx)

                # Card "exists" only when in hand or play
                zone = node_state.get("zone") if node_state else None
                exists = zone in ("hand", "play")

                # Build current state dict for comparison
                curr_state = None
                if exists and node_state:
                    curr_state = {
                        "zone": zone,
                        "exerted": node_state.get("exerted"),
                        "damage": node_state.get("damage"),
                    }

                # Determine role
                role = determine_role(actions[state_idx], card_id, prev_state, curr_state)

                # Write line if card exists OR if it just died (was existing, now isn't)
                if exists:
                    record = {
                        "role": role,
                        "action": actions[state_idx],
                        "state": state_idx,
                        "zone": zone,
                        "exerted": node_state.get("exerted"),
                        "damage": node_state.get("damage"),
                        "edges": edges,
                    }
                    f.write(json.dumps(record) + "\n")
                elif prev_exists:
                    # Card just died - write final line showing what killed it
                    role = determine_role(actions[state_idx], card_id, prev_state, None)
                    record = {
                        "role": role,
                        "action": actions[state_idx],
                        "state": state_idx,
                        "zone": zone,  # "ink", "discard", or None
                    }
                    f.write(json.dumps(record) + "\n")

                prev_exists = exists
                prev_state = curr_state

    print(f"Built {len(card_ids)} card trajectories + game.jsonl ({num_states} states)")
    print(f"  {traj_dir}/")

    return traj_dir


def main():
    if len(sys.argv) < 2:
        print("Usage: python bin/build-trajectories.py <episode_path>")
        print("Example: python bin/build-trajectories.py output/episodes/abc.episode")
        sys.exit(1)

    episode_path = Path(sys.argv[1])

    if not episode_path.exists():
        print(f"Error: {episode_path} does not exist")
        sys.exit(1)

    build_trajectories(episode_path)


if __name__ == "__main__":
    main()
