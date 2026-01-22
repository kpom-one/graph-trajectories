#!/usr/bin/env python3
"""
Build a trajectory graph from a path through the game tree.

Given a leaf state path, produces a single graph that stacks all states
along that path and connects entities across time with NEXT edges.
"""
import sys
from pathlib import Path

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.core.trajectory import build_trajectory_from_path, path_to_state_dirs
from lib.core.graph import save_dot


def main():
    if len(sys.argv) < 2:
        print("Usage: trajectory-graph.py <path> [output.dot]")
        print()
        print("Arguments:")
        print("  path        Path to a leaf state (e.g., output/459b/seed/3/0/6)")
        print("  output.dot  Output file (default: trajectory.dot)")
        print()
        print("Example:")
        print("  trajectory-graph.py output/459b/1sh7asne/3/0/6/0 my-trajectory.dot")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "trajectory.dot"

    # Show what we're doing
    state_dirs = path_to_state_dirs(input_path)
    print(f"Building trajectory from {len(state_dirs)} states:")
    for i, d in enumerate(state_dirs):
        print(f"  State {i}: {d}")

    # Build and save
    trajectory = build_trajectory_from_path(input_path)
    save_dot(trajectory, output_path)

    print()
    print(f"Trajectory graph saved to: {output_path}")
    print(f"  Nodes: {trajectory.number_of_nodes()}")
    print(f"  Edges: {trajectory.number_of_edges()}")


if __name__ == "__main__":
    main()
