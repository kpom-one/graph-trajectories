"""
Trajectory graph: stack multiple game states along a path.

Given a path through the game tree, produces a single graph that:
1. Namespaces all nodes by state index (node -> node@i)
2. Preserves all edges within each state (with namespaced endpoints)
3. Adds temporal `next` edges connecting same entity across adjacent states
"""
from pathlib import Path
import networkx as nx
from lib.core.graph import load_dot


# Edge label for temporal connections (lowercase to match project convention)
TEMPORAL_EDGE = "next"


def path_to_state_dirs(path: str | Path) -> list[Path]:
    """
    Convert a leaf path to the sequence of state directories.

    Example:
        path_to_state_dirs("output/459b/seed/3/0/6")
        -> [
            Path("output/459b/seed"),      # State 0
            Path("output/459b/seed/3"),    # State 1
            Path("output/459b/seed/3/0"),  # State 2
            Path("output/459b/seed/3/0/6") # State 3
        ]

    The seed directory is the first game state. We stop at the matchup
    directory (which has deck1.txt/deck2.txt) since that's just a template,
    not an actual game state.
    """
    path = Path(path)

    # Walk up to find all state directories
    # Stop at matchup level (has deck1.txt = deck definitions, not game state)
    dirs = []
    current = path

    while current.parent != current:
        # Matchup directories have .txt deck files (definitions)
        # Game state directories have .dek files (remaining cards)
        is_matchup = (current / "deck1.txt").exists()

        if is_matchup:
            break  # Don't include matchup template

        if (current / "game.dot").exists():
            dirs.append(current)

        current = current.parent

    # Reverse to get root-to-leaf order
    dirs.reverse()

    if not dirs:
        raise ValueError(f"No game.dot files found in path hierarchy: {path}")

    return dirs


def namespace_node(node: str, state_index: int) -> str:
    """Add state index suffix to a node ID."""
    return f"{node}@{state_index}"


def build_trajectory_graph(state_dirs: list[Path]) -> nx.MultiDiGraph:
    """
    Build a trajectory graph from a sequence of state directories.

    Args:
        state_dirs: Ordered list of directories, each containing game.dot

    Returns:
        Combined graph with namespaced nodes and temporal edges
    """
    trajectory = nx.MultiDiGraph()
    trajectory.graph["name"] = "trajectory"

    prev_nodes = set()

    for i, state_dir in enumerate(state_dirs):
        game_file = state_dir / "game.dot"
        G = load_dot(game_file)

        current_nodes = set()

        # Add namespaced nodes
        for node, attrs in G.nodes(data=True):
            namespaced = namespace_node(node, i)
            current_nodes.add(node)

            # Copy all attributes, add state_index for reference
            node_attrs = dict(attrs)
            node_attrs["state_index"] = str(i)
            trajectory.add_node(namespaced, **node_attrs)

        # Add namespaced edges (preserve all attributes)
        for u, v, key, attrs in G.edges(keys=True, data=True):
            namespaced_u = namespace_node(u, i)
            namespaced_v = namespace_node(v, i)
            trajectory.add_edge(namespaced_u, namespaced_v, **attrs)

        # Add temporal edges from previous state
        if i > 0:
            for node in current_nodes & prev_nodes:
                prev_namespaced = namespace_node(node, i - 1)
                curr_namespaced = namespace_node(node, i)
                trajectory.add_edge(
                    prev_namespaced,
                    curr_namespaced,
                    label=TEMPORAL_EDGE
                )

        prev_nodes = current_nodes

    return trajectory


def build_trajectory_from_path(path: str | Path) -> nx.MultiDiGraph:
    """
    Build a trajectory graph from a leaf path.

    This is the main entry point. Given a path like:
        output/459b/seed/3/0/6

    It will:
    1. Find all state directories from seed to leaf
    2. Load each state's graph
    3. Build the combined trajectory graph

    Args:
        path: Path to a leaf state directory

    Returns:
        Combined trajectory graph
    """
    state_dirs = path_to_state_dirs(path)
    return build_trajectory_graph(state_dirs)
