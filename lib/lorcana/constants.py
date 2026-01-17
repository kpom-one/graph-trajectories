"""
Lorcana game constants.

Namespaced constants for zones, keywords, edge labels, actions, and node types.

TODO: Develop a "minimal" mode where these can be integers. Hard to debug, but
      easier for modelling (maybe?)
"""


class Zone:
    """Zone constants for card locations."""
    HAND = "hand"
    PLAY = "play"
    INK = "ink"
    DISCARD = "discard"
    DECK = "deck"


class Keyword:
    """Keyword edge labels (boolean keywords - presence = has keyword)."""
    RUSH = "rush"
    EVASIVE = "evasive"
    ALERT = "alert"
    BODYGUARD = "bodyguard"
    RECKLESS = "reckless"


class Edge:
    """Edge labels for graph relationships."""
    SOURCE = "source"
    CURRENT_TURN = "current_turn"
    CURRENT_STEP = "current_step"
    CANT_QUEST = "cant_quest"


class Step:
    """Step phase constants for turn structure."""
    READY = "ready"
    SET = "set"
    DRAW = "draw"
    MAIN = "main"
    END = "end"


class Action:
    """Action type constants for available actions."""
    PASS = "can_pass"
    INK = "can_ink"
    PLAY = "can_play"
    QUEST = "can_quest"
    CHALLENGE = "can_challenge"


class CardType:
    """Card type constants."""
    CHARACTER = "character"
    ACTION = "action"
    ITEM = "item"
    LOCATION = "location"


class NodeType:
    """Node type constants for graph nodes."""
    GAME = "game"
    PLAYER = "player"
    CARD = "card"
    STEP = "step"
    ABILITY = "ability"
