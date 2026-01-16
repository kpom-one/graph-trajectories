# Turn Structure

```
ready → set → draw → main → end → (opponent's ready)
```

---

## Whose turn?

```
game --[CURRENT_TURN]--> p1|p2
```
query: `edges_by_label(G, "CURRENT_TURN")[0][1]`

---

## What phase?

```
game --[CURRENT_STEP]--> step.{player}.{phase}
```
query: `get_node_attr(step_node, 'step')` → "ready" | "set" | "draw" | "main" | "end"

---

## Steps

### Ready (4.2.1)
> "The active player readies all their cards in play."

impl: `_ready_step()` - set exerted=0 for all cards in play

### Set (4.2.2)
> "Characters are no longer drying."

impl: `_set_step()` - refill ink_available, grant ink_drops=1

Note: "drying" is computed (`entered_play == current_turn`), not stored.

### Draw (4.2.3)
> "Draw a card. Skip on turn 1 for starting player."

impl: `_draw_step()` - draw 1, or deck-out loss if empty

### Main (4.3)
> "Turn actions can only be taken during the Main phase."

All CAN_* edges computed here. Only phase where `compute_can_pass()` returns action.

### End (4.4)
> "Declare end of turn."

impl: `advance_turn()` - triggered by CAN_PASS, switches to opponent's ready
