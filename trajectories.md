---
marp: true
title: Phase 1 — Context Setting
---

# Setting the Stage

---

## What Kind of Problems Are We Talking About?

- Single-threaded, time-ordered systems
- Locally finite action space
- Deterministic state transitions

<!--
Speaker notes:
- This isn’t a system where everything happens at once.
- Something acts, then the world changes.
- At any moment, there are only a handful of legal moves.
- Once you choose one, what happens next is predictable.
- Over time, those choices compound into an enormous space of futures.
-->

---

## Predictable Systems Can Still Be Uncertain

- Too many possible futures
- Too few explored ones

<!--
Speaker notes:
- Nothing here is random.
- Outcomes are predictable once you choose.
- But the number of possible futures explodes.
- We can only explore a tiny fraction of them.
- Uncertainty comes from scale, not randomness.
- Smart people words: Uncertainty here isn’t stochastic, it’s epistemic
-->

---

## You Never See All Possible Futures

- Exploration is always incomplete
- Decisions must be made anyway

<!--
Speaker notes:
- Even in a fully predictable system, you never get full coverage.
- You explore some futures, not all of them.
- But decisions can’t wait for perfect information.
- So the problem becomes: how do you make good decisions with partial exploration?
- This is the constraint everything else builds on.

-->

---

# Act 1 — Graph Neural Networks

---

## How Graph Neural Networks Represent Knowledge

- Knowledge is encoded in node and edge embeddings
- Structure is generally assumed to be stable during inference

<!--
Speaker notes:
- I’m going to assume everyone here is comfortable with graphs.
- In a GNN, knowledge lives in learned embeddings attached to nodes and edges.
- The graph itself is treated as the thing that organizes meaning.
- During inference, that structure is effectively fixed — we learn within it.
- This is incredibly powerful for many problems.
-->

---

## Message Passing: Learning From Neighbors

- Each node pulls data from adjacent nodes
- That data is compressed into a single summary
- Repeating this spreads information outward

<!--
Speaker notes:
- Each step (or layer) in a GNN, each node looks at its immediate neighbors.
- It doesn’t walk the graph or branch.
- It collapses neighbor information into one representation.
- Repeating this lets information flow farther, but always through compression.
- Every step collapses more of the graph into fewer representations
- You never keep the path — only the summary.
-->

---

## What Temporal GNNs Change (and What They Don’t)

- Time is added as input, not structure
- Aggregation still collapses history
- Paths are not preserved

<!--
Speaker notes:
- Temporal GNNs add timestamps, ordering signals, or snapshots.
- They let the model know *when* something happened in relation to something else.
- But the core operation is unchanged: aggregate and compress.
- History influences the embedding, but the sequence itself is lost.
- You still get summaries of neighborhoods, not the paths that led there.
-->

---

# Act 2 — Where GNNs Struggle

---

## Aggregation Collapses What Matters

- Global state requires aggressive compression
- Compression is inherently lossy
- Every bit influences the whole

<!--
Speaker notes:
- From Act 1: GNN-style reasoning repeatedly aggregates and compresses information.
- That works well, but it necessarily throws details away.
- The challenge is you don’t know which discarded details will matter later.
- Two compressed summaries can look similar while leading to very different futures.
-->

---

## States Don’t Capture Trends

- Similar snapshots can lead to wildly different futures
- What matters is how the system got here and where it's going

<!--
Speaker notes:
- When we compress a system into a snapshot, we lose motion.
- Two states can look nearly identical and still behave very differently.
- The difference isn’t in the state — it’s in the trajectory.
- Trends, pressure, and momentum live across time, not in a single frame.
-->

---

## What’s Happened Before Will Happen Again

- Repeated patterns shape future outcomes
- History carries predictive signal

<!--
Speaker notes:
- When the same kinds of situations repeat, the same kinds of outcomes tend to follow.
- This isn’t about exact states repeating.
- It’s about recurring patterns of interaction.
- If you ignore history, you keep relearning the same lessons.
-->

---

## Where This Leaves Us

- Systems are predictable, but exploration is limited
- Compression loses information we can’t afford to lose
- History contains signal snapshots can’t represent

<!--
Speaker notes:
- We’re working in predictable systems, but the space is too large to fully explore.
- To reason at scale, we compress — and that compression is lossy.
- Snapshots lose trends, momentum, and pressure.
- But history isn’t noise.
- It carries structure that repeats.
- The question now is how to represent and learn from that history directly.
-->

---

# Shifting our Perspective

---

## States Describe Position, Not Process

- States summarize where the system is
- Decisions often depend on how it got there

<!--
Speaker notes:
- Up to now, we’ve been compressing everything into snapshots.
- A state tells you what exists right now.
- But it doesn’t tell you what pressures built up, what was avoided, or what was nearly chosen.
- If two states look the same but arrived there differently, treating them as equivalent can be misleading.
- This suggests the unit we’re modeling may be incorrect for the questions we're asking
-->

---

## Trajectories as First-Class Objects

- A trajectory is a node-local, time-ordered history
- It is defined by what a node can see and experience

<!--
Speaker notes:
- In this model, each node has its own trajectory.
- A trajectory is the sequence of changes *as that node experienced them*
- Different nodes in the same system observe different trajectories, even at the same time.
- This is why nodes can disagree — they are shaped by different perspectives
-->

---

## Experience Lives Locally

- Nodes observe different parts of the same system
- Learning is shaped by what each node experiences

<!--
Speaker notes:
- There is no single, global experience of the system.
- Each node only sees what it can interact with or be affected by.
- Over time, that local experience shapes how the node understands the world.
- Two nodes in the same system can have very different views of “what’s going on.”
- If experience is local, then any learned representation must be local too.
-->

---

## Meaning Emerges From Flow, Not Position

- Importance is revealed by what happens in a node's lifetime
- Repeated trajectories shape what a node expects next

<!--
Speaker notes:
- A node’s meaning isn’t defined by where it sits in a snapshot.
- It’s defined by the kinds of trajectories that pass through it over time.
- Pressure, risk, and opportunity show up as patterns of flow.
- This is how experience turns into expectation.
- We don’t label meaning — it emerges from repeated exposure to similar futures.
-->

---

# Act 4 — Using Experience to Inform Decisions

---

## Nodes Learn From What Happens When They Act

- Nodes accumulate experience across many trajectories
- Experience is tied to actions, not just states

<!--
Speaker notes:
- Once we treat trajectories as node-local, learning becomes grounded in action.
- A node doesn’t learn “what the world is like” in general.
- It learns: “when I act in situations like this, what tends to follow?”
- Over time, nodes build up a memory of consequences.
- This experience is reusable across different futures and starting points.
- Importantly, this learning is not about optimal play — it’s about expectation.
-->

---

## Experience Is Action-Centered

- Learning is indexed by (node, action)
- Outcomes are observed, not inferred

<!--
Speaker notes:
- Experience is not stored as abstract rules.
- It’s attached to concrete choices.
- Each node-action pair accumulates evidence over time.
- The node doesn’t need to know the entire system.
- It only needs to know what tends to happen after *it* does something.
- This keeps learning local, scalable, and composable.
-->

---

## Nodes Form Opinions About Their Own Actions

- Actions are ranked by past outcomes
- Opinions are probabilistic and contextual

<!--
Speaker notes:
- A node doesn’t output a single “best move.”
- It forms opinions about its available actions.
- Some actions feel urgent.
- Some feel dangerous.
- Some feel safe but low-impact.
- These opinions are shaped entirely by past trajectories.
- They are not guaranteed to be correct — just informed.
-->

---

## Opinions Are Local, Partial, and Sometimes Wrong

- Nodes disagree by design
- Disagreement reflects different experiences

<!--
Speaker notes:
- Because trajectories are local, opinions will differ.
- Two nodes in the same state can strongly disagree about what should happen next.
- This isn’t noise — it’s signal.
- Disagreement tells us where experience diverges.
- It also tells us where uncertainty still exists.
-->

---

## Aggregating Opinions Without Central Control

- No single node has a global view
- Decisions emerge from competing local signals

<!--
Speaker notes:
- There is no omniscient planner here.
- Nodes do not coordinate explicitly.
- Instead, each node expresses pressure around its own actions.
- The system produces a field of competing signals.
- The question becomes: who should act next?
-->

---

## Decisions Are Informed, Not Solved

- The system provides guidance, not guarantees
- Final commitment is external to the model

<!--
Speaker notes:
- This model does not choose actions.
- It informs a decision-maker.
- That decision-maker could be:
  - a human
  - a heuristic
  - a search algorithm (MCTS)
- The key is separation:
  - learning produces opinions
  - commitment chooses an action
- This keeps responsibility explicit.
-->

---

## What the Model Actually Outputs (A/B options)

### Option B: Ranking Framing

- Relative preference of actions
- Confidence based on experience density
- Sensitivity to context

<!--
Speaker notes:
- You can think of the output as signals or rankings.
- The exact representation is flexible.
- What matters is that outputs are:
  - local
  - experience-based
  - comparable
- This makes them easy to integrate with existing systems.
-->

---

# Act 5 — Scope, Limits, and Honesty

---

## This Complements Search, It Doesn’t Replace It

- Search explores futures
- Experience reuses what was already explored

<!--
Speaker notes:
- This is not a replacement for MCTS, planning, or simulation.
- Search is still how futures are discovered.
- This model focuses on what we *learn* from explored futures.
- It allows experience from one search to inform another.
- Especially when full search is impossible.
-->

---

## Why This Is Different From Pure Search

- Search is instance-specific
- Experience generalizes across instances

<!--
Speaker notes:
- A search tree is tied to a single starting point.
- Once you leave that starting point, much of the work is discarded.
- Trajectory-based experience persists.
- It transfers across seeds, scenarios, and partial explorations.
-->

---

## This Is Not Optimal Control

- No guarantees of best action
- No claim of convergence to optimal play

<!--
Speaker notes:
- This system does not promise optimal decisions.
- It does not minimize regret globally.
- It does not converge to perfect play.
- Those guarantees require exhaustive exploration.
- Instead, this system aims to be *usefully correct* more often than naive approaches.
-->

---

## Where This Approach Can Fail

- Rare but critical trajectories
- Biased exploration
- Overfitting to early experience

<!--
Speaker notes:
- If important outcomes are extremely rare, they may be missed.
- If exploration is biased, opinions will reflect that bias.
- Early experience can dominate without correction.
- These are real failure modes.
- They are also explicit and inspectable.
-->

---

## Why These Limits Are Acceptable

- Perfect coverage is impossible
- Explicit uncertainty is better than hidden assumptions

<!--
Speaker notes:
- Any system operating at scale must make tradeoffs.
- Pretending uncertainty doesn’t exist doesn’t remove it.
- This approach surfaces uncertainty instead of hiding it.
- That makes downstream decisions safer, not riskier.
-->

---

## Guidance Beats Optimality at Scale

- Better decisions with limited information
- Reusable learning across futures

<!--
Speaker notes:
- When systems are large, optimality becomes theoretical.
- What matters is making fewer catastrophic mistakes.
- Reusing experience helps avoid repeating known failures.
- This is where guidance outperforms brittle optimization.
-->

---

## What This Is (and Isn’t)

- Is: experience reuse under partial exploration
- Isn’t: a silver bullet or a full decision system

<!--
Speaker notes:
- This is a modeling approach, not a product.
- It’s a way to think about learning from history directly.
- It doesn’t eliminate hard problems.
- It makes them more tractable.
-->
