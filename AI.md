# AI Training Approach

## Executive Summary

Memory-based decision-making using similarity lookup instead of neural networks. Two complementary views: state similarity (tactical) and entity trajectory similarity (strategic). No gradient descent, no model training - just record histories, vectorize states, and look up what worked.

---

## Core Philosophy

**Don't train a model. Remember everything. Look up similar situations. Do what worked.**

This is k-Nearest Neighbors / Case-Based Reasoning applied to game AI. Trade learning for memory. Trade abstraction for explainability.

---

## Two Types of Vectors

### 1. State Vectors (Tactical)

Snapshot of the current position.

```
Features (game-specific):
- Score/resources per player
- Entity counts by zone
- Aggregate stats (strength totals, etc.)
- Turn number
```

**Query**: "In similar positions, what action won most often?"

**Horizon**: This turn. Immediate tactical response.

### 2. Trajectory Vectors (Strategic)

An entity's journey through the system: where it's been, where it's going.

```
Trajectory = sequence of states:
  [zone_a, zone_a, zone_b, zone_b, zone_b, modified, removed]

Vectorize by encoding each timestep:
  - Location/zone
  - Status flags
  - Accumulated changes
  - Time in current state
```

**Query**: "Entities with similar arcs - how did their stories end?"

**Horizon**: Next 3-5 turns. Strategic investment.

---

## Decision Architecture

```
                    ┌─────────────────┐
                    │    Decision     │
                    │  Pick action X  │
                    └────────▲────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
    ┌─────────┴─────────┐       ┌──────────┴──────────┐
    │   Board Layer     │       │   Trajectory Layer   │
    │                   │       │                      │
    │ "Similar boards,  │       │ "Elsa's on a dying   │
    │  action X won 70%"│       │  arc, save her"      │
    └───────────────────┘       └──────────────────────┘
```

For each legal action:
1. Query board layer: "In similar positions, did this action type win?"
2. Query trajectory layer: "Does this action put my cards on winning paths?"
3. Combine scores (weighted average)
4. Pick highest

---

## Why This Approach

### Advantages

| Property | Benefit |
|----------|---------|
| Explainable | "I did X because these 5 similar games won" |
| Incremental | Play more games, add to memory, get smarter |
| No training | No hyperparameters, no convergence issues |
| Debuggable | Inspect the neighbors directly |
| Fast iteration | Change vectorization, re-index, test |

### Limitations

| Property | Mitigation |
|----------|------------|
| Storage scales linearly | Prune old/similar states, compress |
| Vector is hand-crafted | Iterate on features based on results |
| No abstraction | Might be fine - answers without "why" |
| Needs dense coverage | Generate lots of games |

### When This Works Well

- State space is small enough to cover (~50-100 features)
- Games are cheap to generate (fast simulator)
- Deterministic replay available (exact reproduction)
- Explainability matters

---

## Unique Dataset Properties

This codebase has unusual properties that enable this approach:

### 1. Full Game Trees (Not Just Logs)

Most game AI has linear game logs. This system stores the full tree:

```
output/matchup/seed/0/1/2/  ← took action 0, then 1, then 2
output/matchup/seed/0/1/3/  ← alternate: took action 3 instead
```

Enables counterfactual analysis: "What if I'd done X instead?"

### 2. Deterministic Replay

Same decks + same seed + same actions = identical game state.

Perfect for:
- Reproducing bugs
- A/B testing strategies
- Controlled experiments

### 3. Entity Identity Across Time

Entities have stable IDs that persist across states. Enables trajectory tracking without inference.

### 4. Graph-Based State

State is already a graph (NetworkX). Natural fit for:
- Graph neural networks (future)
- Structured queries
- Relationship modeling

---

## The 90-Degree Rotation

Traditional view: **Game = sequence of board states**

```
Board 1 → Board 2 → Board 3 → ...
```

Rotated view: **Game = bundle of card trajectories**

```
Elsa:    ●───────●───────●───────●───────✕ (died)
Mickey:  ●───────●───────●───────●───────●───────●
Simba:           ●───────●───────●───────●
```

Same data, different query axis. Board states become cross-sections of trajectory bundles.

Enables:
- "What usually happens to Elsa in spots like this?"
- "Cards with this trajectory shape tend to win"
- "When Elsa and Mickey are both in play, win rate jumps 12%"

---

## Blending with Modern Tools

The k-NN foundation can incorporate learned components:

### Learned Embeddings

Replace hand-crafted vectors with learned ones:

```
Board graph → [encoder] → embedding → k-NN lookup
```

Keep explainability (still lookup), improve representation.

### Graph Neural Networks

Board is already a graph. GNN can learn what structure matters:

```
Board graph → [GNN] → embedding → k-NN lookup
```

### Retrieval-Augmented Decisions

Like RAG for LLMs:

1. Query similar past states
2. Bundle as context
3. Small model synthesizes decision

---

## Storage Considerations

### Current Measurements

| Metric | Value |
|--------|-------|
| Per game | ~1.8 MB |
| Per state | ~26 KB |
| Actions/game | ~68 |
| 100 games | ~179 MB |
| 10,000 games | ~18 GB |

### The Real Cost

Directory/inode overhead dominates. Each action = new directory.

### Optimization Options

1. **Summary only**: Store final trajectory, not intermediate states (70x reduction)
2. **Flat files**: JSON lines instead of directory tree
3. **Memory-first**: MemoryStore for play, dump summary at end
4. **Compression**: gzip DOT files

---

## Implementation Phases

### Phase 1: Data Generation (Done)

- Play random games
- Write to filesystem
- Validate game engine at scale

### Phase 2: Trajectory Extraction (Done)

```python
def extract_trajectory(game_path, card_id) -> list[dict]:
    """Walk game path, return card's state at each step."""
    ...
```

### Phase 3: Vectorization (In Progress)

```python
def vectorize_board(state) -> np.array:
    """Board state → fixed-size vector."""
    ...

def vectorize_trajectory(traj) -> np.array:
    """Card trajectory → fixed-size vector."""
    ...
```

### Phase 4: Indexing

Build k-NN indexes for fast similarity search (FAISS, Annoy, or sklearn).

### Phase 5: Decision Layer

This is the final coat of paint, and the magic that brings everything together. 

```python
def pick_action(game):
    board_scores = board_layer.score_actions(game)
    traj_scores = traj_layer.score_actions(game)
    combined = blend(board_scores, traj_scores)
    return argmax(combined)
```

### Phase 6: Evaluation

Measure win rate against random baseline. Iterate on vectors and weights.

---

## What We're Not Doing (Yet)

- Neural network training
- Reinforcement learning
- Self-play
- Card ability parsing

These can layer on later. Start simple, see what breaks.

---

## Patterns This Resembles

| Pattern | Description |
|---------|-------------|
| k-Nearest Neighbors | Find similar examples, aggregate outcomes |
| Case-Based Reasoning | Solve new problems from similar past problems |
| Retrieval-Augmented Generation | Lookup context before deciding |
| Entity-Centric Modeling | Track entities through time, not snapshots |

---

## Open Questions

1. What's the right board vector? (Feature engineering)
2. What's the right trajectory length/encoding?
3. How to weight board vs trajectory layers?
4. How many games needed for dense coverage?
5. When does random play stop being informative?

---

## Success Criteria

1. Beat random baseline by significant margin
2. Decisions are explainable ("because these similar games...")
3. Scales to 100k+ games without infrastructure pain
4. Clear path to incorporating learned components later
