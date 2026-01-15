# Trajectory-Based Learning in Graph Systems

## Setting the Stage

### What Kind of Problems Are We Talking About?

- **Single-threaded, time-ordered systems** — Something acts, then the world changes
- **Locally finite action space** — At any moment, only a handful of legal moves
- **Deterministic state transitions** — Once you choose, what happens next is predictable

Over time, those choices compound into an enormous space of futures.

### Predictable Systems Can Still Be Uncertain

- Too many possible futures
- Too few explored ones

Nothing here is random. Outcomes are predictable once you choose. But the number of possible futures explodes — we can only explore a tiny fraction of them. Uncertainty comes from scale, not randomness. (Uncertainty here isn't stochastic, it's epistemic.)

### You Never See All Possible Futures

- Exploration is always incomplete
- Decisions must be made anyway

Even in a fully predictable system, you never get full coverage. You explore some futures, not all of them. But decisions can't wait for perfect information. So the problem becomes: **how do you make good decisions with partial exploration?**

---

## Act 1 — Graph Neural Networks

### How GNNs Represent Knowledge

- Knowledge is encoded in node and edge embeddings
- Structure is generally assumed to be stable during inference

In a GNN, knowledge lives in learned embeddings attached to nodes and edges. The graph itself organizes meaning. During inference, that structure is effectively fixed — we learn within it.

### Message Passing: Learning From Neighbors

- Each node pulls data from adjacent nodes
- That data is compressed into a single summary
- Repeating this spreads information outward

Each layer, each node looks at its immediate neighbors. It doesn't walk the graph or branch — it collapses neighbor information into one representation. Repeating this lets information flow farther, but always through compression. You never keep the path — only the summary.

### What Temporal GNNs Change (and What They Don't)

- Time is added as input, not structure
- Aggregation still collapses history
- Paths are not preserved

Temporal GNNs add timestamps, ordering signals, or snapshots. They let the model know *when* something happened. But the core operation is unchanged: aggregate and compress. History influences the embedding, but the sequence itself is lost.

---

## Act 2 — Where GNNs Struggle

### Aggregation Collapses What Matters

- Global state requires aggressive compression
- Compression is inherently lossy
- Every bit influences the whole

GNN-style reasoning repeatedly aggregates and compresses information. That works well, but it necessarily throws details away. The challenge: you don't know which discarded details will matter later. Two compressed summaries can look similar while leading to very different futures.

### States Don't Capture Trends

- Similar snapshots can lead to wildly different futures
- What matters is how the system got here and where it's going

When we compress a system into a snapshot, we lose motion. Two states can look nearly identical and still behave very differently. The difference isn't in the state — it's in the trajectory. Trends, pressure, and momentum live across time, not in a single frame.

### What's Happened Before Will Happen Again

- Repeated patterns shape future outcomes
- History carries predictive signal

When the same kinds of situations repeat, the same kinds of outcomes tend to follow. This isn't about exact states repeating — it's about recurring patterns of interaction. If you ignore history, you keep relearning the same lessons.

### Where This Leaves Us

- Systems are predictable, but exploration is limited
- Compression loses information we can't afford to lose
- History contains signal snapshots can't represent

The question: how to represent and learn from history directly?

---

## Shifting Perspective

### States Describe Position, Not Process

- States summarize where the system is
- Decisions often depend on how it got there

A state tells you what exists right now. But it doesn't tell you what pressures built up, what was avoided, or what was nearly chosen. If two states look the same but arrived there differently, treating them as equivalent can be misleading. This suggests **the unit we're modeling may be incorrect for the questions we're asking**.

### Trajectories as First-Class Objects

- A trajectory is a node-local, time-ordered history
- It is defined by what a node can see and experience

Each node has its own trajectory — the sequence of changes *as that node experienced them*. Different nodes in the same system observe different trajectories, even at the same time. This is why nodes can disagree — they are shaped by different perspectives.

### Experience Lives Locally

- Nodes observe different parts of the same system
- Learning is shaped by what each node experiences

There is no single, global experience of the system. Each node only sees what it can interact with or be affected by. Over time, that local experience shapes how the node understands the world. If experience is local, then any learned representation must be local too.

### Meaning Emerges From Flow, Not Position

- Importance is revealed by what happens in a node's lifetime
- Repeated trajectories shape what a node expects next

A node's meaning isn't defined by where it sits in a snapshot. It's defined by the kinds of trajectories that pass through it over time. Pressure, risk, and opportunity show up as patterns of flow. We don't label meaning — it emerges from repeated exposure to similar futures.

---

## Act 4 — Using Experience to Inform Decisions

### Nodes Learn From What Happens When They Act

- Nodes accumulate experience across many trajectories
- Experience is tied to actions, not just states

Once we treat trajectories as node-local, learning becomes grounded in action. A node doesn't learn "what the world is like" in general. It learns: **"when I act in situations like this, what tends to follow?"** Over time, nodes build up a memory of consequences — reusable across different futures and starting points.

Importantly, this learning is not about optimal play — it's about expectation.

### Experience Is Action-Centered

- Learning is indexed by (node, action)
- Outcomes are observed, not inferred

Experience is not stored as abstract rules — it's attached to concrete choices. Each node-action pair accumulates evidence over time. The node doesn't need to know the entire system. It only needs to know what tends to happen after *it* does something. This keeps learning local, scalable, and composable.

### Nodes Form Opinions About Their Own Actions

- Actions are ranked by past outcomes
- Opinions are probabilistic and contextual

A node doesn't output a single "best move." It forms opinions about its available actions:
- Some actions feel urgent
- Some feel dangerous
- Some feel safe but low-impact

These opinions are shaped entirely by past trajectories. They are not guaranteed to be correct — just informed.

### Opinions Are Local, Partial, and Sometimes Wrong

- Nodes disagree by design
- Disagreement reflects different experiences

Because trajectories are local, opinions will differ. Two nodes in the same state can strongly disagree about what should happen next. This isn't noise — it's signal. Disagreement tells us where experience diverges and where uncertainty still exists.

### Aggregating Opinions Without Central Control

- No single node has a global view
- Decisions emerge from competing local signals

There is no omniscient planner. Nodes do not coordinate explicitly. Instead, each node expresses pressure around its own actions. The system produces a field of competing signals. The question becomes: who should act next?

### Decisions Are Informed, Not Solved

- The system provides guidance, not guarantees
- Final commitment is external to the model

This model does not choose actions — it informs a decision-maker. That decision-maker could be a human, a heuristic, or a search algorithm (MCTS). The key is separation: learning produces opinions, commitment chooses an action. This keeps responsibility explicit.

### What the Model Outputs

- Relative preference of actions
- Confidence based on experience density
- Sensitivity to context

Outputs are local, experience-based, and comparable. This makes them easy to integrate with existing systems.

---

## Act 5 — Scope, Limits, and Honesty

### This Complements Search, It Doesn't Replace It

- Search explores futures
- Experience reuses what was already explored

This is not a replacement for MCTS, planning, or simulation. Search is still how futures are discovered. This model focuses on what we *learn* from explored futures. It allows experience from one search to inform another — especially when full search is impossible.

### Why This Is Different From Pure Search

- Search is instance-specific
- Experience generalizes across instances

A search tree is tied to a single starting point. Once you leave that starting point, much of the work is discarded. Trajectory-based experience persists. It transfers across seeds, scenarios, and partial explorations.

### This Is Not Optimal Control

- No guarantees of best action
- No claim of convergence to optimal play

This system does not promise optimal decisions. It does not minimize regret globally. It does not converge to perfect play — those guarantees require exhaustive exploration. Instead, this system aims to be **usefully correct** more often than naive approaches.

### Where This Approach Can Fail

- Rare but critical trajectories may be missed
- Biased exploration produces biased opinions
- Early experience can dominate without correction

These are real failure modes. They are also explicit and inspectable.

### Why These Limits Are Acceptable

- Perfect coverage is impossible
- Explicit uncertainty is better than hidden assumptions

Any system operating at scale must make tradeoffs. Pretending uncertainty doesn't exist doesn't remove it. This approach surfaces uncertainty instead of hiding it. That makes downstream decisions safer, not riskier.

### Guidance Beats Optimality at Scale

- Better decisions with limited information
- Reusable learning across futures

When systems are large, optimality becomes theoretical. What matters is making fewer catastrophic mistakes. Reusing experience helps avoid repeating known failures.

### What This Is (and Isn't)

**Is**: Experience reuse under partial exploration

**Isn't**: A silver bullet or a full decision system

This is a modeling approach, not a product. It's a way to think about learning from history directly. It doesn't eliminate hard problems — it makes them more tractable.
