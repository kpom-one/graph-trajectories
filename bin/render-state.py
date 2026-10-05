#!/usr/bin/env python3
"""
Render a Lorcana state.json + criteria.json as a static HTML board.

Reads:
    jev/<episode_id>/<state_index>/state.json
    jev/<episode_id>/<state_index>/criteria.json

Writes:
    jev/<episode_id>/<state_index>/state.html

The HTML is produced by `lib.render.render()`, the same function the
Jev HTTP server calls. CLI usage is provided for offline debugging.

Usage:
    python bin/render-state.py <jev_subdir>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.render import render  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("Usage: render-state.py <jev_subdir>", file=sys.stderr)
        sys.exit(1)
    subdir = Path(sys.argv[1]).resolve()
    state_path = subdir / "state.json"
    if not state_path.exists():
        print(f"error: {state_path} not found", file=sys.stderr)
        sys.exit(1)

    state = json.loads(state_path.read_text())
    cp = subdir / "criteria.json"
    criteria = json.loads(cp.read_text()) if cp.exists() else None

    try:
        rel = subdir.relative_to(Path("jev").resolve())
        state_dir = str(rel)
    except ValueError:
        state_dir = subdir.name

    out = subdir / "state.html"
    out.write_text(render(state, criteria, state_dir=state_dir))
    print(f"state.html -> {out}")
    print(f"ask form: {'enabled (state_dir=' + state_dir + ')' if state_dir else 'disabled'}")


if __name__ == "__main__":
    main()
