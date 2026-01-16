# Nodes

---

## Game
```
id: game
type: NodeType.GAME
```
| attr | type | notes |
|------|------|-------|
| turn | string(int) | current turn number |
| game_over | "0" \| "1" | |
| winner | "" \| "p1" \| "p2" | |

---

## Player
```
id: p1, p2
type: NodeType.PLAYER
```
| attr | type | notes |
|------|------|-------|
| lore | string(int) | win at 20 |
| ink_drops | string(int) | 0 or 1, refreshes each turn |
| ink_total | string(int) | cards in inkwell |
| ink_available | string(int) | unexerted ink |

---

## Step
```
id: step.{player}.{phase}
type: NodeType.STEP
```
| attr | type | notes |
|------|------|-------|
| player | "p1" \| "p2" | |
| step | Step.READY \| Step.SET \| Step.DRAW \| Step.MAIN \| Step.END | |

All 10 exist at game start. Sequence: Step.READY → Step.SET → Step.DRAW → Step.MAIN → Step.END

---

## Card
```
id: {player}.{card_name}.{copy}
type: NodeType.CARD
```
| attr | type | notes |
|------|------|-------|
| label | string | normalized name, lookup key for card DB |
| zone | Zone.HAND \| Zone.PLAY \| Zone.INK \| Zone.DISCARD | |
| exerted | "0" \| "1" | |
| damage | string(int) | |
| entered_play | string(int) | turn number, for drying check |

Card types: CardType.CHARACTER, CardType.ACTION, CardType.ITEM, CardType.LOCATION

Created when drawn. Example: `p1.stitch_rock_star.a`

---

## Ability
```
id: {effect}.t{turn}.{seq}
type: NodeType.ABILITY
```

Source of effect edges. See [abilities.md](abilities.md).

Example: `rush.t3.1`
