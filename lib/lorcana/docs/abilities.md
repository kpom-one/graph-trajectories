# Abilities

Abilities are the source of effects. Every rule modification comes from an ability node.

---

## Node

```
id: {effect}.t{turn}.{seq}
type: Ability
```

Example: `rush.t3.1` (first Rush created on turn 3)

---

## Edges

Every ability has:

```
ability --[Keyword.*]--> target_card   # what it does
ability --[Edge.SOURCE]--> origin_card # where it came from
```

---

## Lifecycle

### Creation

**Printed abilities**: `execute_play()` after card enters play
- Create ability node (type: NodeType.ABILITY)
- Create effect edge (Keyword.*) to self
- Create Edge.SOURCE edge to self

### Removal

**Permanent**: when source card leaves play
- Find abilities where `Edge.SOURCE --> card`
- Remove those ability nodes
