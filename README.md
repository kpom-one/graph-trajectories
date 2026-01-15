# graph-trajectories

Graph-based state modeling with entity trajectory tracking. Explore game trees as a filesystem - each directory is a state, subdirectories are actions. Built for ML training data generation and case-based reasoning.

**Test platform**: Lorcana (trading card game)

## Quick Start

```bash
# Install dependencies
just setup

# Create a test game
just test

# Explore the game tree
just play output/b013/b123456.0123456.ab/0/1/0/6

```

## Understanding Paths

A path like `output/b013/b123456.0123456.ab/0/1/0/6` tells a story:

```
output/b013/b123456.0123456.ab/0/1/0/6
       │    └────seed─────┘  └─moves─┘
       └─matchup (which decks)
```

- **`b013`** - Matchup between two specific decks
- **`b123456.0123456.ab`** - Starting hands (deterministic shuffle)
- **`0/1/0/6`** - Sequence of moves taken

Each directory contains:
- **`game.dot`** - Complete game state as a graph
- **`actions.txt`** - Available moves from here
- **`diff.txt`** - What changed from the parent state

### Reading the Files

**actions.txt** shows your options:
```
0: play:p2.diablo_obedient_raven.d
1: end
```

Pick an action number, `just play <whole_path>` with that directory → new game state computed.

## Commands

```bash
# Create a matchup from two decks
just match data/decks/deck1.txt data/decks/deck2.txt

# Shuffle and draw starting hands (with seed for reproducibility)
just shuffle b013 "b123456.0123456.ab"

# Navigate to a state (computes it if needed)
just play output/b013/b123456.0123456.ab/0/1

# Clear all games
just clear
```

## What Works

- ✅ Ink cards, play characters, quest for lore, challenge characters, end turn
- ✅ Win detection (20 lore victory, deck-out)
- ✅ Deterministic shuffle with reproducible seeds
- ✅ Lazy state computation (only compute paths you explore)
- ✅ Sequential action IDs (0, 1, 2...) - no collisions
- ✅ Navigation files (actions.txt, diff.txt)
- ✅ In-memory API for fast batch operations (GameSession)
- ✅ Recursive path building (`just play long/path/to/state` works)

## What Doesn't (Yet)

- ❌ Card abilities and effects
- ❌ Singing songs
- ❌ Web viewer for visual exploration
- ❌ Effect modifiers (strength/willpower buffs)

## Example: Replaying a Game

```bash
# Start fresh
just clear

# Set up a specific matchup
just match data/decks/bs01.txt data/decks/rp01.txt

# Shuffle with known seed (reproducible)
just shuffle b013 "b123456.0123456.ab"

# Replay a sequence of moves
just play output/b013/b123456.0123456.ab/0/1/0/1/1/0/6

# See what changed
cat output/b013/b123456.0123456.ab/0/1/0/1/1/0/6/diff.txt
```

The same seed + same moves = same game state. Perfect for playtesting, bug reports, or AI training data.

---

## [Advanced] How It Works

**Game state as a graph**: Nodes are cards, players, and game metadata. Edges are relationships (ownership, turn order, legal actions).

**Filesystem as game tree**: Each state is a directory. Actions are subdirectories. The tree structure mirrors possible game paths.

**On-demand computation**: Empty directories don't exist. Navigate to `0/` → system computes what happens, creates `game.dot`.

**Sequential action IDs**: Actions sorted deterministically, numbered 0, 1, 2... No hash collisions, easy indexing.

**Navigation files**: Human-readable summaries (actions.txt, diff.txt) alongside machine-readable graph (game.dot).

For deep technical details (graph schema, state representation, AI/ML use cases) → see [ARCHITECTURE.md](ARCHITECTURE.md)
