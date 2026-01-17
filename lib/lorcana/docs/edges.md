# Edges

---

## Structural

### Edge.CURRENT_TURN
```
game --[Edge.CURRENT_TURN]--> player
```
knows: `edges_by_label(G, Edge.CURRENT_TURN)[0][1]` → current player
set by: `advance_turn()` - switches player

### Edge.CURRENT_STEP
```
game --[Edge.CURRENT_STEP]--> step.{player}.{phase}
```
knows: `edges_by_label(G, Edge.CURRENT_STEP)[0][1]` → step node, then `get_node_attr(step, 'step')` → phase name
set by: `advance_turn()` - walks through ready/set/draw/main/end

---

## Actions

Computed edges. Rebuilt after every state change via `compute_all()`.
Uses `action_type` attr (not `label`).

### Action.PASS
```
player --[action_type=Action.PASS]--> game
```
available: `compute_can_pass()` - during main phase only
execute: `advance_turn()` - end turn, switch player

### Action.INK
```
card --[action_type=Action.INK]--> player
```
available: `compute_can_ink()` - card in hand, inkwell=true, ink_drops > 0
execute: `execute_ink()` - move to ink zone, increment ink counters

### Action.PLAY
```
card --[action_type=Action.PLAY]--> player
```
available: `compute_can_play()` - card in hand, ink_available >= cost
execute: `execute_play()` - move to play/discard, spend ink, set entered_play

### Action.QUEST
```
card --[action_type=Action.QUEST]--> player
```
available: `compute_can_quest()` - in play, ready, dry (entered_play < current_turn)
execute: `execute_quest()` - exert, add lore to player

### Action.CHALLENGE
```
attacker --[action_type=Action.CHALLENGE]--> defender
```
available: `compute_can_challenge()`
    - attacker ready+(dry or Keyword.RUSH)
    - defender exerted+opponent
    - Evasive check (attacker needs Evasive or Alert)
    - Bodyguard check (must target Bodyguard if able)
execute: `execute_challenge()` - exert attacker, deal damage both ways

---

## Ability

See [abilities.md](abilities.md) for creation/lifecycle.
See [rules/10-keywords.md](rules/10-keywords.md) for keyword effects.
