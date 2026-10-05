"""
Shared rendering and state extraction for the Jev views.

This is the single rendering entry point: both `bin/render-state.py` (CLI)
and `bin/jev-server.py` (HTTP) call `render(state, criteria, state_dir=...)`
to produce the same HTML string.

State extraction lives here too, so the CLI and server agree on what a
"state" means and don't drift.
"""
from html import escape as _escape
from pathlib import Path
import re

import networkx as nx
from jinja2 import Environment, FileSystemLoader

from lib.lorcana.cards import get_card_db


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
TEMPLATE_NAME = "state.html.j2"

# Keywords carried as edge labels on Card nodes.
KEYWORD_LABELS = ("rush", "evasive", "alert", "bodyguard", "reckless", "ward", "support")

# Lorcana card-back as an inline SVG data URL.
CARD_BACK_SVG = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 200 280'>"
    "<rect width='200' height='280' fill='%23070a14'/>"
    "<circle cx='100' cy='140' r='90' fill='%23261a4a'/>"
    "<circle cx='100' cy='140' r='40' fill='%23a36bd9' opacity='0.6'/>"
    "</svg>"
)

# Engine action type -> human rubric (used by Jev instructions/criteria).
RUBRIC_FOR_TYPE = {
    "can_pass":    "End the turn without taking an action.",
    "can_ink":     "Put this card into the inkwell to gain +1 ink next turn.",
    "can_play":    "Pay this card's cost and put it into play.",
    "can_quest":   "Send this character to quest for lore (exerting it).",
    "can_challenge": "Have this ready character fight an exerted opposing one.",
}

TYPE_ORDER = ("end", "ink", "play", "quest", "challenge")

ACTION_CLASS_DESCRIPTIONS = {
    "end": "End the turn and preserve the current board and cards for later turns.",
    "ink": "Convert a card from hand into ink to improve resources on future turns.",
    "play": "Spend ink to play a card and develop the current turn.",
    "quest": "Exert a character to gain lore and advance toward winning the game.",
    "challenge": "Exert a character to challenge an opposing character and change the board.",
}

LENS_VARIANTS = (
    {"id": "player", "label": "Player", "fields": ("player",)},
    {"id": "deck", "label": "Deck", "fields": ("deck",)},
    {"id": "future", "label": "Future", "fields": ("future_lines",)},
    {"id": "history", "label": "History", "fields": ("past_matches",)},
    {
        "id": "player_deck_history",
        "label": "Player + Deck + History",
        "fields": ("player", "deck", "past_matches"),
    },
    {
        "id": "player_deck",
        "label": "Player + Deck",
        "fields": ("player", "deck"),
    },
)

INFORMATION_FIELDS = ("player", "deck", "past_matches", "future_lines")


# ────────────────────────── State extraction ──────────────────────────


def card_stats(card_name: str) -> dict:
    """Look up a card's stats from data/cards.json by normalized DB key."""
    db = get_card_db()
    key = card_name.strip('"')
    if key not in db:
        key = key.lower()
    if key not in db:
        raise KeyError(f"card not in db: {key!r}")
    data = db[key]
    keywords = [a["keyword"] for a in data.get("abilities", []) if "keyword" in a]
    return {
        "name": key,
        "display_name": data.get("fullName", key),
        "cost": data.get("cost", 0),
        "strength": data.get("strength"),
        "willpower": data.get("willpower"),
        "lore": data.get("lore", 0),
        "type": data.get("type", "").lower(),
        "keywords": keywords,
        "abilities_text": data.get("fullText", "") or data.get("bodyText", "") or "",
        "image": (data.get("images") or {}).get("full", ""),
    }


def extract_state(graph: nx.MultiDiGraph, state_index: int) -> dict:
    """
    Pull the state_index slice out of a stacked episode graph.

    Returns a dict with two top-level keys: `cards` (raw card stats) and
    `board_state` (per-player lore/ink/zone occupancy).
    """
    suffix = f"@{state_index}"

    def _int_attr(node_attrs: dict, key: str, default: int = 0) -> int:
        """Read an int attr from a node, stripping pydot's quotes if present."""
        val = node_attrs.get(key, default)
        if isinstance(val, str):
            val = val.strip('"')
        try:
            return int(val)
        except (TypeError, ValueError):
            return default

    me_id = "p1"
    for u, v, data in graph.edges(data=True):
        if u != f"game{suffix}":
            continue
        if data.get("label", "").strip('"') == "current_turn":
            me_id = v[: -len(suffix)]
            break
    opp_id = "p2" if me_id == "p1" else "p1"

    game_attrs = graph.nodes.get(f"game{suffix}", {})
    turn = _int_attr(game_attrs, "turn", 0)
    current_step = "main"
    for u, v, data in graph.edges(data=True):
        if u != f"game{suffix}":
            continue
        if data.get("label", "").strip('"') == "current_step":
            current_step = graph.nodes.get(v, {}).get("step", "main").strip('"')
            break

    instances = []
    for node, attrs in graph.nodes(data=True):
        if not node.endswith(suffix):
            continue
        if attrs.get("type", "").strip('"') != "Card":
            continue
        base = node[: -len(suffix)]
        parts = base.split(".")
        if len(parts) < 3:
            continue
        label = attrs.get("label", "")
        if not label:
            continue
        instances.append((base, label, attrs))

    from collections import Counter
    name_counts = Counter(card_stats(label)["display_name"] for _, label, _ in instances)

    def card_key_for(base: str, label: str) -> str:
        stats = card_stats(label)
        display = stats["display_name"]
        letter = base.rsplit(".", 1)[-1]
        if name_counts[display] > 1:
            return f"{display} {letter}".lower()
        return display.lower()

    cards: dict[str, dict] = {}
    for base, label, _ in instances:
        stats = card_stats(label)
        display = stats["display_name"]
        letter = base.rsplit(".", 1)[-1]
        if name_counts[display] > 1:
            key = f"{display} {letter}".lower()
        else:
            key = display.lower()
        if key not in cards:
            cards[key] = {
                "display_name": display,
                "letter": letter if name_counts[display] > 1 else None,
                "cost": stats["cost"],
                "strength": stats["strength"],
                "willpower": stats["willpower"],
                "lore": stats["lore"],
                "type": stats["type"],
                "keywords": stats["keywords"],
                "abilities_text": stats["abilities_text"],
                "image": stats["image"],
            }

    def player_stats(player: str) -> dict:
        pnode = f"{player}{suffix}"
        attrs = graph.nodes.get(pnode, {})
        return {
            "lore": _int_attr(attrs, "lore", 0),
            "ink_total": _int_attr(attrs, "ink_total", 0),
            "ink_available": _int_attr(attrs, "ink_available", 0),
        }

    def in_play_dict(player: str) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for base, label, attrs in instances:
            if not base.startswith(f"{player}."):
                continue
            if attrs.get("zone", "") != "play":
                continue
            key = card_key_for(base, label)
            flags: dict = {"exerted": attrs.get("exerted", "0").strip('"') == "1"}
            dmg = _int_attr(attrs, "damage", 0)
            if dmg:
                flags["damage"] = dmg
            out[key] = flags
        return out

    def player_block(player: str) -> dict:
        s = player_stats(player)
        hand_keys = [
            card_key_for(base, label)
            for base, label, attrs in instances
            if base.startswith(f"{player}.") and attrs.get("zone", "") == "hand"
        ]
        return {
            "lore": s["lore"],
            "ink_available": s["ink_available"],
            "ink_total": s["ink_total"],
            "hand": (
                {"hidden": True, "size": len(hand_keys)} if player != me_id
                else hand_keys
            ),
            "in_play": in_play_dict(player),
            "inkwell": sum(
                1 for base, _, attrs in instances
                if base.startswith(f"{player}.") and attrs.get("zone", "") == "ink"
            ),
            "discard": [
                card_key_for(base, label)
                for base, label, attrs in instances
                if base.startswith(f"{player}.") and attrs.get("zone", "") == "discard"
            ],
            "deck_size": sum(
                1 for base, _, attrs in instances
                if base.startswith(f"{player}.") and attrs.get("zone", "") == "deck"
            ),
        }

    return {
        "cards": cards,
        "board_state": {
            "turn": turn,
            "phase": current_step,
            "win_target": 20,
            "me": player_block(me_id),
            "opponent": player_block(opp_id),
        },
    }


# Cache parsed graphs keyed by (path, mtime). The DOT file is 1+ MB and
# pydot parsing takes 10+ seconds; in dev mode Flask is single-process so
# this cache lives for the life of the server.
_GRAPH_CACHE: dict[str, tuple[float, "nx.MultiDiGraph"]] = {}


# Lightweight DOT parser — episode graph.dot is structurally trivial:
# - "node@N" [type="..", k="v", ...];
# - "node@N" -> "node@N" [k="v", ...];
# pydot's parser is ~400x slower because it goes through pyparsing. This
# regex pass handles the format we actually emit (~30ms for a 1MB file).
_NODE_RE = re.compile(r'^\s*"([^"]+)"\s*\[([^\]]*)\]\s*;\s*$')
_EDGE_RE = re.compile(r'^\s*"([^"]+)"\s*->\s*"([^"]+)"\s*\[([^\]]*)\]\s*;\s*$')
# Match both quoted="..." and unquoted attributes (e.g. turn=7 vs label="x").
_ATTR_RE = re.compile(r'(\w+)=(?:"([^"]*)"|([^\s,\]]+))')


def _parse_attrs(attr_str: str) -> dict[str, str]:
    """Parse a DOT attribute block into a dict. Handles quoted + unquoted values."""
    out = {}
    for m in _ATTR_RE.finditer(attr_str):
        out[m.group(1)] = m.group(2) if m.group(2) is not None else m.group(3)
    return out


def _parse_dot_simple(text: str) -> "nx.MultiDiGraph":
    """Parse a Lorcana episode DOT file into a MultiDiGraph. Fast path."""
    G = nx.MultiDiGraph()
    for line in text.splitlines():
        m = _EDGE_RE.match(line)
        if m:
            src, dst, attrs = m.group(1), m.group(2), m.group(3)
            G.add_edge(src, dst, **_parse_attrs(attrs))
            continue
        m = _NODE_RE.match(line)
        if m:
            node_id, attrs = m.group(1), m.group(2)
            G.add_node(node_id, **_parse_attrs(attrs))
    return G


def _load_graph_cached(graph_path: Path) -> "nx.MultiDiGraph":
    """Load + parse graph.dot, caching by (path, mtime).

    Uses a custom regex parser instead of pydot — episode DOT files are
    structurally simple, and pydot takes ~13s on a 1MB file (vs ~30ms).
    """
    key = str(graph_path.resolve())
    mtime = graph_path.stat().st_mtime
    cached = _GRAPH_CACHE.get(key)
    if cached and cached[0] == mtime:
        return cached[1]
    text = graph_path.read_text()
    graph = _parse_dot_simple(text)
    _GRAPH_CACHE[key] = (mtime, graph)
    return graph


def load_episode_state(episode_dir: Path, state_index: int) -> tuple[dict, dict]:
    """
    Load `output/episodes/<id>.episode/graph.dot` and extract state N.

    Returns (state, criteria) ready for `render()` and `build_jev_questions()`.

    The parsed graph is cached per-(path, mtime) — first request after a
    fresh episode takes ~13s for the DOT parse; subsequent requests reuse
    the cached graph and run in ~30ms.
    """
    graph_path = episode_dir / "graph.dot"
    if not graph_path.exists():
        raise FileNotFoundError(f"no graph.dot in {episode_dir}")
    graph = _load_graph_cached(graph_path)
    state = extract_state(graph, state_index)
    criteria = build_criteria_from_actions(collect_legal_actions(graph, state_index))
    return state, criteria


def list_state_indices(graph: nx.MultiDiGraph) -> list[int]:
    """Return all state indices present in `graph`, sorted ascending."""
    indices = set()
    for node in graph.nodes():
        at = node.rfind("@")
        if at == -1:
            continue
        try:
            indices.add(int(node[at + 1:]))
        except ValueError:
            pass
    return sorted(indices)


def turn_buckets(graph: nx.MultiDiGraph) -> list[tuple[int, list[int]]]:
    """
    Group state indices by the `turn` attribute on the `game@<i>` node.

    Returns a list of `(turn_number, [state_indices...])` tuples sorted by
    turn number. States with no readable turn (default 0) get bucketed under
    turn 0.
    """
    out: dict[int, list[int]] = {}
    for i in list_state_indices(graph):
        attrs = graph.nodes.get(f"game@{i}", {})
        raw = attrs.get("turn", 0)
        if isinstance(raw, str):
            raw = raw.strip('"')
        try:
            t = int(raw)
        except (TypeError, ValueError):
            t = 0
        out.setdefault(t, []).append(i)
    return sorted(out.items())


# ────────────────────────── Legal actions ──────────────────────────


def collect_legal_actions(graph: nx.MultiDiGraph, state_index: int) -> list[dict]:
    """Walk CAN_* edges at state_index and return action dicts."""
    suffix = f"@{state_index}"
    actions = []
    for u, v, _, data in graph.edges(keys=True, data=True):
        if not u.endswith(suffix) or not v.endswith(suffix):
            continue
        action_type = data.get("action_type")
        if not action_type:
            continue
        atype = action_type.strip('"') if isinstance(action_type, str) else action_type
        src = u[: -len(suffix)]
        dst = v[: -len(suffix)]
        desc = data.get("description", "")
        if isinstance(desc, str):
            desc = desc.strip('"')
        actions.append({"type": atype, "src": src, "dst": dst, "description": desc})
    return actions


def action_label(action: dict) -> str:
    """Render a human-readable label for a legal action."""
    atype = action["type"].replace("can_", "")
    desc = action["description"]
    src = action["src"]

    if atype == "pass" or desc == "end":
        return "End the turn"

    if atype == "ink":
        return f"Ink {display_name_for(src)}"

    if atype == "play":
        parts = [display_name_for(src)]
        try:
            cost = card_stats(_extract_card_name(src))["cost"]
            parts.append(f"({cost})")
        except KeyError:
            pass
        return f"Play {' '.join(parts)}"

    if atype == "quest":
        try:
            lore = card_stats(_extract_card_name(src))["lore"]
            return f"Quest with {display_name_for(src)} ({lore} lore)"
        except KeyError:
            return f"Quest with {display_name_for(src)}"

    if atype == "challenge":
        dst = action["dst"]
        try:
            a_s = card_stats(_extract_card_name(src))["strength"]
            a_w = card_stats(_extract_card_name(src))["willpower"]
        except KeyError:
            a_s, a_w = "?", "?"
        try:
            d_s = card_stats(_extract_card_name(dst))["strength"]
            d_w = card_stats(_extract_card_name(dst))["willpower"]
        except KeyError:
            d_s, d_w = "?", "?"
        return (
            f"Challenge {display_name_for(dst)} ({d_s}/{d_w}) "
            f"with {display_name_for(src)} ({a_s}/{a_w})"
        )

    return desc


def _extract_card_name(card_id: str) -> str:
    """
    Extract the card-name portion from an engine node id like
    ``p2.mr._arrow_legacy's_first_mate.d``. Strips the ``p1.``/``p2.``
    player prefix and the trailing single-letter instance id. If the input
    doesn't match that pattern (e.g. already a bare card name like
    ``tinker_bell_fast_flier``), returns it unchanged.
    """
    if card_id.startswith("p1.") or card_id.startswith("p2."):
        rest = card_id.split(".", 1)[1]
        if len(rest) >= 2 and rest[-1].isalpha() and rest[-2] == ".":
            rest = rest[:-2]
        return rest
    return card_id


def display_name_for(card_id: str) -> str:
    name = _extract_card_name(card_id)
    try:
        return card_stats(name)["display_name"]
    except KeyError:
        return name


def build_criteria_from_actions(actions: list[dict]) -> dict:
    """Return {engine_description: human_label} from a list of action dicts."""
    return {a["description"]: action_label(a) for a in actions}


_ACTION_HISTORY_CACHE: dict[tuple[str, float], dict[int, str]] = {}


def load_action_history(episode_dir: Path) -> dict[int, str]:
    """
    Parse `history.txt` and return {state_index: raw_action_description}.

    Cached per-(path, mtime) — same lifetime as the graph cache.
    """
    history = episode_dir / "history.txt"
    if not history.exists():
        return {}
    key = (str(history), history.stat().st_mtime)
    cached = _ACTION_HISTORY_CACHE.get(key)
    if cached is not None:
        return cached

    out: dict[int, str] = {}
    cur_idx: int | None = None
    for line in history.read_text().splitlines():
        m = re.match(r"=== state (\d+) ===", line)
        if m:
            cur_idx = int(m.group(1))
            continue
        if cur_idx is None or not line.startswith("# action:"):
            continue
        out[cur_idx] = line.split(":", 1)[1].strip()

    _ACTION_HISTORY_CACHE[key] = out
    return out


def render_action_description(desc: str) -> str:
    """
    Convert a raw engine action description into a short human label.

    Mirrors `action_label()` but operates on historical descriptions like
    ``ink:p1.tinker_bell_fast_flier.d`` or
    ``challenge:p1.foo.a->p2.bar.b``. Falls back gracefully when card
    metadata is missing.
    """
    if not desc:
        return ""
    if desc == "initial":
        return "Initial state"
    if desc == "end":
        return "End the turn"

    if desc.startswith("challenge:"):
        payload = desc[len("challenge:"):]
        if "->" in payload:
            src, dst = payload.split("->", 1)
            try:
                d_s = card_stats(_extract_card_name(dst))["strength"]
                d_w = card_stats(_extract_card_name(dst))["willpower"]
                a_s = card_stats(_extract_card_name(src))["strength"]
                a_w = card_stats(_extract_card_name(src))["willpower"]
                return (
                    f"Challenge {display_name_for(dst)} ({d_s}/{d_w}) "
                    f"with {display_name_for(src)} ({a_s}/{a_w})"
                )
            except KeyError:
                return f"Challenge {display_name_for(dst)} with {display_name_for(src)}"
        return f"Challenge {display_name_for(payload)}"

    if ":" in desc:
        kind, src = desc.split(":", 1)
        name = display_name_for(src)
        card_name = _extract_card_name(src)
        if kind == "ink":
            return f"Ink {name}"
        if kind == "play":
            try:
                cost = card_stats(card_name)["cost"]
                return f"Play {name} ({cost})"
            except (KeyError, IndexError):
                return f"Play {name}"
        if kind == "quest":
            try:
                lore = card_stats(card_name)["lore"]
                return f"Quest with {name} ({lore} lore)"
            except (KeyError, IndexError):
                return f"Quest with {name}"
        if kind == "pass":
            return "End the turn"
        return f"{kind} {name}"

    return desc


# ────────────────────────── HTML rendering ──────────────────────────

# Module-level Jinja env so the parser, lexer, and bytecode cache live
# across requests. auto_reload watches the template file for edits.
_ENV = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=True,
    trim_blocks=True,
    lstrip_blocks=True,
    auto_reload=True,
)


def render(state: dict, criteria: dict | None = None, *, state_dir: str | None = None,
           turn_buckets_: list[tuple[int, list[int]]] | None = None,
           episode_id: str = "",
           action_labels: dict[int, str] | None = None,
           taken_label: str = "") -> str:
    """
    Render a state.json + criteria.json (both loaded from disk or constructed)
    into the page HTML.

    `state_dir` is the path string the browser will send to /api/jev so the
    server knows which state the user is asking about. Pass None to skip
    embedding the ask form.

    `turn_buckets_` and `episode_id` are optional: when both are provided
    the template renders a turn navigation bar above the board.

    `action_labels` is an optional `{state_index: human_label}` map (e.g.
    from `render_action_description` over `load_action_history`) used to
    annotate the sub-steps in the turn nav.
    """
    cards = state.get("cards", {})
    board = state.get("board_state", {})
    me = board.get("me", {})
    opp = board.get("opponent", {})

    def hand_size(p):
        h = p.get("hand", [])
        if isinstance(h, dict):
            return int(h.get("size", 0))
        return len(h)

    def stat_lane(p):
        # Deck: 60 starting - visible cards - 7 (opening hand already drawn).
        seen = (
            hand_size(p)
            + len(p.get("in_play", {}))
            + len(p.get("discard", []))
            + int(p.get("inkwell", 0))
        )
        deck = max(60 - seen - 7, 0)
        return (
            '<div class="lane counters">'
            f'<div class="stat"><span class="label">lore</span><span class="val">{p.get("lore", 0)}</span></div>'
            f'<div class="stat"><span class="label">discard</span><span class="val">{len(p.get("discard", []))}</span></div>'
            f'<div class="stat"><span class="label">deck</span><span class="val">{deck}</span></div>'
            f'<div class="stat"><span class="label">inkwell</span><span class="val">{p.get("inkwell", 0)}</span></div>'
            f'<div class="stat"><span class="label">hand</span><span class="val">{hand_size(p)}</span></div>'
            '</div>'
        )

    def tile_back() -> str:
        return f'<div class="card face-down"><img src="{CARD_BACK_SVG}" alt=""/></div>'

    def tile(card_key: str, exerted: bool, damage: int = 0) -> str:
        info = cards.get(card_key, {})
        cls = "card" + (" exerted" if exerted else "")
        img = info.get("image", "")
        dmg = f'<div class="dmg">{damage}</div>' if damage else ""
        display = info.get("display_name", card_key)
        letter = info.get("letter")
        if letter:
            display = f"{display} ({letter})"
        stats = []
        if info.get("cost") is not None:
            stats.append(f"{info['cost']}")
        if info.get("strength") is not None:
            stats.append(f"⚔{info['strength']}")
        if info.get("willpower") is not None:
            stats.append(f"❤{info['willpower']}")
        if info.get("lore"):
            stats.append(f"⭐{info['lore']}")
        stats_str = " · ".join(stats)
        tooltip = (
            f' data-tooltip="{_escape(display)} | {_escape(stats_str)}"'
            if stats_str else ""
        )
        body = f'<img src="{_escape(img)}" alt=""/>' if img else '<div class="placeholder"></div>'
        return f'<div class="{cls}"{tooltip}>{body}{dmg}</div>'

    def render_in_play(player: dict) -> str:
        out = []
        for key, flags in player.get("in_play", {}).items():
            out.append(tile(
                key,
                exerted=bool(flags.get("exerted")),
                damage=int(flags.get("damage", 0) or 0),
            ))
        return "".join(out)

    def render_hand(player: dict) -> str:
        hand = player.get("hand", [])
        if isinstance(hand, dict) and hand.get("hidden"):
            return "".join(tile_back() for _ in range(int(hand.get("size", 0))))
        if not hand:
            return ""
        return "".join(tile(k, exerted=False) for k in hand)

    def render_actions_panel(crit: dict, taken_label: str = "") -> str:
        by_type: dict[str, list[str]] = {}
        for desc, label in crit.items():
            atype = desc.split(":", 1)[0] if ":" in desc else desc
            escaped = _escape(label)
            cls = ' class="taken"' if taken_label and label == taken_label else ''
            by_type.setdefault(atype, []).append((escaped, cls))
        sections = []
        for t in TYPE_ORDER:
            items = by_type.get(t)
            if not items:
                continue
            lis = "".join(f"<li{cls}>{esc}</li>" for esc, cls in items)
            sections.append(
                f'<div class="action-group" data-type="{_escape(t)}">'
                f'<h4>{_escape(t)}</h4>'
                f'<ul>{lis}</ul>'
                f'</div>'
            )
        return "".join(sections)

    template = _ENV.get_template(TEMPLATE_NAME)
    current_state = None
    current_turn = None
    if state_dir:
        try:
            current_state = int(state_dir.rsplit("/", 1)[-1])
        except ValueError:
            current_state = None
    if current_state is not None:
        try:
            current_turn = int(board.get("turn", 0))
        except (TypeError, ValueError):
            current_turn = 0
    return template.render(
        board=board,
        me=me,
        opp=opp,
        cards=cards,
        criteria=criteria,
        state_dir=state_dir,
        episode_id=episode_id,
        turn_buckets=turn_buckets_ or [],
        current_state=current_state,
        current_turn=current_turn,
        action_labels=action_labels or {},
        taken_label=taken_label,
        stat_lane={"opp": stat_lane(opp), "me": stat_lane(me)},
        render_in_play=render_in_play,
        render_hand=render_hand,
        render_actions=lambda c: render_actions_panel(c, taken_label),
    )


# ────────────────────────── Jev request ──────────────────────────


def filter_criteria(criteria: dict, action_types: list[str]) -> dict:
    """Restrict criteria to the selected action type prefixes."""
    if not action_types:
        return criteria
    wanted = set(action_types)
    return {
        description: label
        for description, label in criteria.items()
        if (description.split(":", 1)[0] if ":" in description else description)
        in wanted
    }


def _action_type(description: str) -> str:
    """Return the public action class encoded by an engine description."""
    return description.split(":", 1)[0] if ":" in description else description


def _action_rubric(action_type: str) -> str:
    rubric_key = "can_pass" if action_type == "end" else f"can_{action_type}"
    return RUBRIC_FOR_TYPE.get(rubric_key, "Take this legal game action.")


def _non_empty_information(information: dict[str, str] | None) -> dict[str, str]:
    """Return trimmed, non-empty information fields in their fixed order."""
    information = information or {}
    return {
        field: information.get(field, "").strip()
        for field in INFORMATION_FIELDS
        if isinstance(information.get(field, ""), str)
        and information.get(field, "").strip()
    }


def active_jev_lenses(information: dict[str, str] | None) -> list[dict]:
    """Return lens definitions with at least one populated source field."""
    populated = _non_empty_information(information)
    active = []
    for lens in LENS_VARIANTS:
        fields = [field for field in lens["fields"] if field in populated]
        if not fields:
            continue
        active.append({
            "id": lens["id"],
            "label": lens["label"],
            "fields": fields,
            "information_paths": [f"information.{field}" for field in fields],
        })
    return active


def _build_jev_question_bundle(
    criteria: dict,
    *,
    lens: dict | None = None,
) -> tuple[dict, dict]:
    """Build one base or lens-specific three-layer question bundle."""
    actions = []
    by_class: dict[str, list[dict]] = {}
    for index, (description, label) in enumerate(criteria.items(), start=1):
        action_type = _action_type(description)
        action = {
            "id": f"action_{index}",
            "type": action_type,
            "label": label,
            "engine_description": description,
        }
        actions.append(action)
        by_class.setdefault(action_type, []).append(action)

    questions = {}
    metadata = {}
    prefix = f"lens_{lens['id']}__" if lens else ""
    lens_id = lens["id"] if lens else None
    lens_label = lens["label"] if lens else "All information"

    def instruction(question: str) -> str:
        if not lens:
            return f"{question} Consider `board_state` and any supplied `information`."
        return (
            f"{question} Base the judgment only on `board_state` and the information "
            f"paths listed in `decision_lenses.{lens_id}`. Ignore other fields in "
            "`information`."
        )

    for action in actions:
        question_id = f"{prefix}should_{action['id']}"
        questions[question_id] = {
            "type": "noul",
            "instructions": {
                "candidate_action": {
                    "id": action["id"],
                    "class": action["type"],
                    "description": action["label"],
                },
                "question": instruction(
                    "Would taking `candidate_action` as the player's next action "
                    "this turn be strategically sound? Judge whether it is a "
                    "reasonable action, not whether it is the single best legal action."
                ),
            },
            "criteria": {
                "true": (
                    "This is a reasonable action now and supports the player's "
                    "goals or current position."
                ),
                "false": (
                    "This action is strategically unsound now because it wastes "
                    "resources, gives up too much value, or conflicts with the "
                    "player's goals or current position."
                ),
            },
        }
        metadata[question_id] = {
            "layer": "action",
            "lens_id": lens_id,
            "lens_label": lens_label,
            **action,
        }

    for action_type in TYPE_ORDER:
        members = by_class.get(action_type, [])
        if len(members) < 2 or action_type == "end":
            continue
        question_id = f"{prefix}rank_{action_type}"
        questions[question_id] = {
            "type": "choice",
            "instructions": {
                "action_class": action_type,
                "question": instruction(
                    "Which available action in `action_class` is the best next "
                    "action this turn?"
                ),
            },
            "criteria": {
                action["id"]: {
                    "action": action["label"],
                    "meaning": _action_rubric(action_type),
                }
                for action in members
            },
        }
        metadata[question_id] = {
            "layer": "action_group",
            "lens_id": lens_id,
            "lens_label": lens_label,
            "action_type": action_type,
            "options": {action["id"]: action for action in members},
        }

    if by_class:
        present_types = [action_type for action_type in TYPE_ORDER if action_type in by_class]
        question_id = f"{prefix}rank_action_groups"
        questions[question_id] = {
            "type": "choice",
            "instructions": instruction(
                "Which action class contains the best next action this turn?"
            ),
            "criteria": {
                action_type: {
                    "what": ACTION_CLASS_DESCRIPTIONS[action_type],
                    "available_actions": [
                        action["label"] for action in by_class[action_type]
                    ],
                }
                for action_type in present_types
            },
        }
        metadata[question_id] = {
            "layer": "action_groups",
            "lens_id": lens_id,
            "lens_label": lens_label,
            "options": {
                action_type: ACTION_CLASS_DESCRIPTIONS[action_type]
                for action_type in present_types
            },
        }

    return questions, metadata


def build_jev_default_questions(
    criteria: dict,
    information: dict[str, str] | None = None,
) -> tuple[dict, dict]:
    """Build the base recommendation and every active information-lens bundle."""
    questions, metadata = _build_jev_question_bundle(criteria)
    for lens in active_jev_lenses(information):
        lens_questions, lens_metadata = _build_jev_question_bundle(
            criteria,
            lens=lens,
        )
        questions.update(lens_questions)
        metadata.update(lens_metadata)
    return questions, metadata


def build_jev_state(state: dict, information: dict[str, str]) -> dict:
    """Return request state with information text stored once and empty fields pruned."""
    request_state = dict(state)
    populated = _non_empty_information(information)
    if populated:
        request_state["information"] = populated
        request_state["decision_lenses"] = {
            lens["id"]: {
                "label": lens["label"],
                "information_paths": lens["information_paths"],
            }
            for lens in active_jev_lenses(populated)
        }
    return request_state


def build_jev_questions(
    criteria: dict,
    question_specs: list[dict],
) -> tuple[dict, dict]:
    """
    Build the Jev `questions` map from ordered question specifications.

    Returns:
        questions dict: {question_id: {type, instructions, criteria}}
        label maps: {question_id: {label: engine description}}
    """
    questions = {}
    label_maps = {}
    for index, spec in enumerate(question_specs, start=1):
        question_id = f"question_{index}"
        filtered = filter_criteria(criteria, spec.get("action_types", []))
        label_to_description = {
            label: description
            for description, label in filtered.items()
        }
        options = {}
        for label, description in label_to_description.items():
            action_type = (
                description.split(":", 1)[0]
                if ":" in description
                else description
            )
            rubric_key = (
                "can_pass" if action_type == "end" else f"can_{action_type}"
            )
            options[label] = RUBRIC_FOR_TYPE.get(rubric_key) or None
        questions[question_id] = {
            "type": "choice",
            "instructions": spec["prompt"],
            "criteria": options,
        }
        label_maps[question_id] = label_to_description
    return questions, label_maps
