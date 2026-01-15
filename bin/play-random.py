#!/usr/bin/env python3
"""
Demo script showing the in-memory game API.

Plays a random game using MemoryStore - much faster than file I/O.
"""
import time
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.lorcana.game_api import GameSession
from lib.core.file_store import FileStore


def play_game(session):

    print("Playing random game until completion...")
    t2 = time.time()
    final_path = session.play_until_game_over()
    t3 = time.time()
    print(f"Game completed in {(t3-t2)*1000:.1f}ms")
    print(f"Final path: {final_path}")
    print(f"Winner: {session.get_winner()}")
    print(f"Game over: {session.is_game_over()}")
    print(f"Actions taken: {final_path.count('/') if final_path else 0}")


def main():
    if len(sys.argv) < 2:
        print("Usage: play-random.py <initial_state_path> [count]")
        print("Example: play-random.py output/b013/b123456.0123456.ab 10")
        sys.exit(1)

    initial_path = sys.argv[1]
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    session = GameSession.from_file(initial_path, FileStore())
    for x in range(count):
        session.reset()  # Reset to initial state before each game
        play_game(session)


if __name__ == "__main__":
    main()
