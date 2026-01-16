# Keywords

"Card has X" = card has incoming X edge. See [abilities.md](../abilities.md).

---

## Boolean

### Keyword.RUSH
```
ability --[Keyword.RUSH]--> card
```
knows: `has_keyword(G, card, Keyword.RUSH)`
effect: `compute_can_challenge()` - skip drying check

### Keyword.EVASIVE
```
ability --[Keyword.EVASIVE]--> card
```
knows: `has_keyword(G, card, Keyword.EVASIVE)`
effect: `compute_can_challenge()` - defender has Evasive → attacker must too
