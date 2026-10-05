#!/usr/bin/env python3
"""
Extract a state from a stacked episode graph and write it as a Jev view.

Reads an episode's graph.dot, extracts the requested state, and writes:
    jev/<episode_id>/<state_index>/state.json
    jev/<episode_id>/<state_index>/criteria.json

State extraction lives in `lib.render` — the same function the HTTP server
calls. This CLI exists for offline use and debugging.

Usage:
    python bin/build-jev-request.py <episode_dir> <state_index>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.render import (  # noqa: E402
    collect_legal_actions,
    extract_state,
    build_criteria_from_actions,
)


OUTPUT_ROOT = Path("jev")


def main():
    if len(sys.argv) < 3:
        print("Usage: build-jev-request.py <episode_dir> <state_index>", file=sys.stderr)
        sys.exit(1)

    episode = Path(sys.argv[1])
    state_index = int(sys.argv[2])
    graph_path = episode / "graph.dot"
    if not graph_path.exists():
        print(f"error: {graph_path} not found", file=sys.stderr)
        sys.exit(1)

    from lib.core.graph import load_dot
    from lib.lorcana.cards import get_card_db
    graph = load_dot(graph_path)
    get_card_db()

    state = extract_state(graph, state_index)
    actions = collect_legal_actions(graph, state_index)
    criteria = build_criteria_from_actions(actions)

    episode_id = episode.name.removesuffix(".episode")
    out_dir = OUTPUT_ROOT / episode_id / str(state_index)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "state.json").write_text(json.dumps(state, indent=2))
    (out_dir / "criteria.json").write_text(json.dumps(criteria, indent=2))

    print(f"state.json    -> {out_dir / 'state.json'}")
    print(f"criteria.json -> {out_dir / 'criteria.json'}")
    print(f"criteria:     {len(criteria)}")


if __name__ == "__main__":
    main()
