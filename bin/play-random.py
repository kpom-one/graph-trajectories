#!/usr/bin/env python3
"""
Play random games from an initial state.

Default: fast in-memory play (MemoryStore), produces .episode files only.
With --output-tree: writes full game tree to disk (FileStore) + .episode files.
"""
import argparse
import time
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.lorcana.game_api import GameSession
from lib.core.file_store import FileStore
from lib.core.memory_store import MemoryStore


def play_game(session, game_num):
    print(f"Game {game_num}: ", end="", flush=True)
    t0 = time.time()
    final_path = session.play_until_game_over()
    elapsed = (time.time() - t0) * 1000
    actions = final_path.count('/') if final_path else 0
    print(f"{session.get_winner()} wins in {actions} actions ({elapsed:.0f}ms)")


def main():
    parser = argparse.ArgumentParser(description="Play random games from initial state")
    parser.add_argument("initial_path", help="Path to initial game state")
    parser.add_argument("count", type=int, nargs="?", default=1, help="Number of games to play")
    parser.add_argument("--output-tree", action="store_true",
                        help="Write full game tree to disk (slower, useful for debugging)")
    args = parser.parse_args()

    store = FileStore() if args.output_tree else MemoryStore()
    session = GameSession.from_file(args.initial_path, store)

    for i in range(args.count):
        session.reset()
        play_game(session, i + 1)


if __name__ == "__main__":
    main()
