#!/usr/bin/env python3
"""
Build a Jev Choice request from a state directory and a question.

Reads:
    <state_dir>/state.json     the world
    <state_dir>/criteria.json  the {description: label} map

By default: writes the request JSON to stdout (so a runner can post it).

With --ask: posts the request to the Jev API and prints the chosen label
plus the engine description it resolves to.

The candidate set passed to Jev is the set of `label` strings from
criteria.json (the human-readable option names). Player, deck, past-match,
and future-line information is added to the request state. --action-types
filters the criteria to a subset of types ("ink,play") before posting; omit
to send all.

Usage:
    python bin/build-jev-choice.py <state_dir> "<question>"
    python bin/build-jev-choice.py --ask <state_dir> "<question>"
    python bin/build-jev-choice.py --ask <state_dir> "What to ink?" \
        --player "I favor tempo over value." \
        --deck "This is an amber steel deck." \
        --past-matches "Evasive threats have been difficult." \
        --future-lines "Set up a two-turn lore race." \
        --action-types ink,play
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.render import build_jev_questions, build_jev_state, filter_criteria  # noqa: E402
from lib.typesafe import ask  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description="Build a Jev Choice request from a state directory and a question"
    )
    parser.add_argument("state_dir", help="Path to a jev/<episode>/<state>/ directory")
    parser.add_argument("question", help="The Choice question for Jev")
    parser.add_argument("--player", default="", help="Free-form player description sent to Jev")
    parser.add_argument("--deck", default="", help="Free-form deck description sent to Jev")
    parser.add_argument("--past-matches", default="", help="Relevant past-match context sent to Jev")
    parser.add_argument("--future-lines", default="", help="Future lines under consideration sent to Jev")
    parser.add_argument(
        "--action-types",
        default="",
        help="Comma-separated types to include (e.g. 'ink,play'). Omit to send all.",
    )
    parser.add_argument(
        "--ask",
        action="store_true",
        help="Post the request to the Jev API and print the chosen label + engine description",
    )
    parser.add_argument(
        "--model",
        default="jev-latest",
        help="Jev model alias (default: jev-latest)",
    )
    args = parser.parse_args()

    state_dir = Path(args.state_dir)
    state_path = state_dir / "state.json"
    criteria_path = state_dir / "criteria.json"

    if not state_path.exists():
        print(f"error: {state_path} not found", file=sys.stderr)
        sys.exit(1)
    if not criteria_path.exists():
        print(f"error: {criteria_path} not found", file=sys.stderr)
        sys.exit(1)

    state = json.loads(state_path.read_text())
    criteria = json.loads(criteria_path.read_text())

    action_types = [t.strip() for t in args.action_types.split(",") if t.strip()]
    filtered = filter_criteria(criteria, action_types)
    if not filtered:
        print("error: action-types filter produced empty criteria", file=sys.stderr)
        sys.exit(2)

    information = {
        "player": args.player,
        "deck": args.deck,
        "past_matches": args.past_matches,
        "future_lines": args.future_lines,
    }
    request_state = build_jev_state(state, information)
    question_specs = [{
        "prompt": args.question,
        "action_types": action_types,
    }]
    questions, label_maps = build_jev_questions(criteria, question_specs)

    if not args.ask:
        # Default mode: emit the request so a runner / web proxy can send it.
        request = {
            "model": args.model,
            "state": request_state,
            "questions": questions,
        }
        json.dump(request, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return

    response = ask(request_state, questions, model=args.model)
    answer = response.get("answers", {}).get("question_1", {})
    label = answer.get("choice", "")
    description = label_maps["question_1"].get(label, "")
    probs = answer.get("probabilities", {})
    confidence = answer.get("confidence")

    out = {
        "question": args.question,
        "information": information,
        "action_types": action_types,
        "chosen_label": label,
        "engine_description": description,
        "probabilities": probs,
        "confidence": confidence,
        "usage": response.get("usage", {}),
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
