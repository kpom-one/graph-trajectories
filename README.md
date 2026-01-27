# graph-trajectories

Generate ML training data from game simulations. Games are modeled as graphs, played to completion, and exported as self-contained **episodes** for downstream analysis.

**Test platform**: Lorcana (trading card game)

## Quick Start

```bash
# Install dependencies
just setup

# Generate 6 random games (2 seeds × 3 games each)
just generate-games 2 3

# Check output
ls output/episodes/
```

Each `.episode` directory is a complete game ready for ML pipelines.

## What's an Episode?

An **episode** is a complete game from start to finish, packaged as a directory:

```
output/episodes/abc123-0.episode/
├── graph.dot      # All states stacked into one graph with temporal edges
├── history.txt    # Human-readable play-by-play
├── result.json    # Winner, final scores, metadata
├── deck1.dek      # Player 1's starting deck
└── deck2.dek      # Player 2's starting deck
```

The `graph.dot` connects entities across time with `next` edges:

```
p1.mulan.a@0 [zone=hand]
      ↓ next
p1.mulan.a@1 [zone=play]
      ↓ next
p1.mulan.a@2 [zone=play, exerted=true]
      ↓ next
      ✕ (banished - no @3)
```

This structure enables extracting **trajectories** - a single card's path through the game - for training models on card behavior patterns.

## Commands

```bash
# Generate random games
just generate-games [num_seeds] [games_per_seed] [--output-tree]

# Run tests
just test

# Clear all output
just clear
```

The `--output-tree` flag writes the full game tree to `output/tree/` for debugging. Without it, only episodes are saved (faster, smaller).

## Architecture

**Game state = graph**: Nodes are entities (game, players, cards). Edges are relationships and legal actions.

**GameSession**: Orchestrates gameplay. Applies actions, tracks state history, detects wins.

**StateStore**: Pluggable storage. `MemoryStore` (fast, in-memory) or `FileStore` (writes tree to disk).

**Episode export**: When a game ends, all states are stacked into a single temporal graph and written to `.episode/`.

See [ARCHITECTURE.md](ARCHITECTURE.md) for full details.

## What Works

- Core game mechanics (play, pass, actions)
- Win detection and random action selection
- Deterministic replay (same seed + moves = same game)
- Episode export for ML training data

## What Doesn't (Yet)

- A TON of rules/mechanics for the engine
- The actual trajectory part... I'm still working that out :) 