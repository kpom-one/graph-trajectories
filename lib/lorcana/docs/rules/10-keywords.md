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
