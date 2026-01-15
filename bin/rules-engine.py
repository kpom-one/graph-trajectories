#!/usr/bin/env python3
"""
Dotcana Rules Engine

Commands:
    init <deck1.txt> <deck2.txt>   - Create matchup from decklists
    shuffle <matchdir> <seed>      - Shuffle and deal starting hands
    show <game.dot>                - Show available actions
    play <path> [--store=file|memory] - Navigate and show state

Options:
    --store=file|memory           Storage backend (default: file)
"""
import sys
import argparse
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.core.graph import get_node_attr, edges_by_label
from lib.core.file_store import FileStore
from lib.core.memory_store import MemoryStore
from lib.core.navigation import read_actions_file, format_actions
from lib.lorcana.setup import init_game, shuffle_and_draw
from lib.lorcana.state import LorcanaState
from lib.lorcana.execute import apply_action_at_path


def cmd_init(deck1: str, deck2: str) -> None:
    """Create matchup from decklist files."""
    matchup_hash = init_game(deck1, deck2)

    # Print hash to stdout for justfile to capture
    print(matchup_hash)
    print(f"[rules-engine] init: output/{matchup_hash}/game.dot", file=sys.stderr)


def cmd_shuffle(matchdir: str, seed: str) -> None:
    """Shuffle decks and draw starting hands."""
    seed = shuffle_and_draw(matchdir, seed)
    output_path = Path(matchdir) / seed

    print(seed)
    print(f"[rules-engine] shuffle: seed={seed} -> {output_path / 'game.dot'}", file=sys.stderr)

    # Show available actions from actions.txt
    actions = read_actions_file(output_path)

    if actions:
        print("\nAvailable actions:", file=sys.stderr)
        for a in actions:
            print(f"  [{a['id']}] {a['description']}", file=sys.stderr)


def cmd_show(game_dot: str) -> None:
    """Show available actions."""
    path = Path(game_dot).parent
    actions = read_actions_file(path)

    print(f"[rules-engine] show: {game_dot}", file=sys.stderr)

    if not actions:
        print("No actions available.")
        return

    print("Available actions:")
    for a in actions:
        print(f"  [{a['id']}] {a['description']}")


def cmd_play(path: str, store_type: str = 'file') -> None:
    """Navigate to state, apply action if needed, show available actions."""
    path = Path(path)

    # Create appropriate store
    if store_type == 'file':
        store = FileStore()
        # Ensure state exists (recursively applies actions if needed)
        apply_action_at_path(path)
    else:
        # Memory store - load from file first
        file_store = FileStore()
        if not file_store.state_exists(path):
            apply_action_at_path(path)
        state = file_store.load_state(path, LorcanaState)
        store = MemoryStore()
        store.save_state(state, str(path), format_actions_fn=format_actions)

    # Load state for display
    state = store.load_state(path, LorcanaState)

    # Get available actions from store
    actions = store.get_actions(path)

    print(f"[rules-engine] play: {path} (store={store_type})", file=sys.stderr)

    # Show game state summary

    # Get current turn
    turn_edges = edges_by_label(state.graph, "CURRENT_TURN")
    current_player = turn_edges[0][1] if turn_edges else "?"

    # Get player stats
    p1_lore = get_node_attr(state.graph, 'p1', 'lore', '0')
    p2_lore = get_node_attr(state.graph, 'p2', 'lore', '0')
    p1_ink_avail = get_node_attr(state.graph, 'p1', 'ink_available', '0')
    p1_ink_total = get_node_attr(state.graph, 'p1', 'ink_total', '0')
    p2_ink_avail = get_node_attr(state.graph, 'p2', 'ink_available', '0')
    p2_ink_total = get_node_attr(state.graph, 'p2', 'ink_total', '0')

    marker_p1 = "►" if current_player == "p1" else " "
    marker_p2 = "►" if current_player == "p2" else " "

    print(f"\n{marker_p1} P1: {p1_lore} lore, {p1_ink_avail}/{p1_ink_total} ink")
    print(f"{marker_p2} P2: {p2_lore} lore, {p2_ink_avail}/{p2_ink_total} ink")

    if not actions:
        print("\nNo actions available.")
        return

    print("\nAvailable actions:")
    for a in actions:
        print(f"  [{a['id']}] {a['description']}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "init":
        if len(sys.argv) != 4:
            print("Usage: rules-engine.py init <deck1.txt> <deck2.txt>")
            sys.exit(1)
        cmd_init(sys.argv[2], sys.argv[3])

    elif cmd == "shuffle":
        if len(sys.argv) != 4:
            print("Usage: rules-engine.py shuffle <matchdir> <seed>")
            sys.exit(1)
        cmd_shuffle(sys.argv[2], sys.argv[3])

    elif cmd == "show":
        if len(sys.argv) != 3:
            print("Usage: rules-engine.py show <game.dot>")
            sys.exit(1)
        cmd_show(sys.argv[2])

    elif cmd == "play":
        # Parse --store flag
        parser = argparse.ArgumentParser(prog='rules-engine.py play')
        parser.add_argument('path')
        parser.add_argument('--store', choices=['file', 'memory'], default='file')
        args = parser.parse_args(sys.argv[2:])
        cmd_play(args.path, args.store)

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
