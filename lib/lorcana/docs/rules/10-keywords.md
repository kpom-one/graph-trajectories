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
effect: `compute_can_challenge()` - defender has Evasive → attacker must have Evasive or Alert

### Keyword.ALERT
```
ability --[Keyword.ALERT]--> card
```
knows: `has_keyword(G, card, Keyword.ALERT)`
effect: `compute_can_challenge()` - can challenge Evasive defenders

### Keyword.BODYGUARD
```
ability --[Keyword.BODYGUARD]--> card
```
knows: `has_keyword(G, card, Keyword.BODYGUARD)`
effect: `compute_can_challenge()` - if any valid defender has Bodyguard, must target Bodyguard
