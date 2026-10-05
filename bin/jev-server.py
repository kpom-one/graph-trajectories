#!/usr/bin/env python3
"""
Local server for browsing Lorcana states and asking Jev.

Real-time: serves rendered HTML directly from output/episodes/<id>.episode/
without pre-generating any files. Each request loads the episode's graph.dot,
extracts the requested state, and renders through the same template the CLI
uses.

Routes:
    GET  /                                  list of episodes
    GET  /<episode>/                        list of states for an episode
    GET  /<episode>/<state>                 rendered HTML board
    GET  /<episode>/<state>/state.json      raw state JSON
    GET  /<episode>/<state>/criteria.json   raw criteria JSON
    POST /api/jev                           proxy to Jev (api.typesafe.ai)

The API key lives in .env / TYPESAFE_API_KEY on this machine; the browser
never sees it.

Usage:
    python bin/jev-server.py [--port 8765]
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, abort, jsonify, request, send_file  # noqa: E402

from lib.render import (  # noqa: E402
    INFORMATION_FIELDS,
    TYPE_ORDER,
    _load_graph_cached,
    build_jev_default_questions,
    build_jev_questions,
    build_jev_state,
    load_action_history,
    load_episode_state,
    render,
    render_action_description,
    turn_buckets,
)
from lib.typesafe import JevError, ask  # noqa: E402


EPISODES_ROOT = Path("output/episodes").resolve()


def create_app() -> Flask:
    app = Flask(__name__)

    def episode_dir(episode_id: str) -> Path:
        """Resolve and guard an episode directory under output/episodes/."""
        # Episode dirs are named `<id>.episode`. URLs use `<id>`.
        ep = (EPISODES_ROOT / f"{episode_id}.episode").resolve()
        try:
            ep.relative_to(EPISODES_ROOT)
        except ValueError:
            abort(404)
        return ep

    def list_states(episode_id: str) -> list[int]:
        ep = episode_dir(episode_id)
        if not (ep / "graph.dot").exists():
            abort(404)
        graph = (ep / "graph.dot").read_text()
        # Every state index appears as `game@<N>` in the DOT file.
        indices = set()
        for marker in ('game@',):
            i = 0
            while True:
                j = graph.find(marker, i)
                if j == -1:
                    break
                i = j + len(marker)
                k = graph.find('"', i)
                if k == -1:
                    break
                try:
                    indices.add(int(graph[i:k]))
                except ValueError:
                    pass
        return sorted(indices)

    # ── Index / lists ─────────────────────────────────────────────

    @app.get("/")
    def index():
        if not EPISODES_ROOT.exists():
            return "no output/episodes/ — run just generate-games first", 404
        links = []
        for ep_dir in sorted(EPISODES_ROOT.iterdir()):
            if not ep_dir.is_dir() or not ep_dir.name.endswith(".episode"):
                continue
            if not (ep_dir / "graph.dot").exists():
                continue
            episode_id = ep_dir.name.removesuffix(".episode")
            n_states = len(list_states(episode_id))
            links.append(
                f'<li><a href="/{episode_id}/">{episode_id}</a> '
                f'<span style="opacity:0.5">({n_states} states)</span></li>'
            )
        body = (
            "<!doctype html><meta charset=utf-8>"
            "<title>Lorcana states</title>"
            "<style>body{font-family:-apple-system,sans-serif;background:#1d2a1f;color:#cfe0d4;"
            "padding:24px;max-width:780px;margin:0 auto}h1{font-size:18px}"
            "a{color:#5fb4ff}li{margin:4px 0}</style>"
            "<h1>Lorcana states</h1><ul>" + "".join(links) + "</ul>"
        )
        return body

    @app.get("/<episode>/")
    def episode_index(episode: str):
        states = list_states(episode)
        links = "".join(
            f'<li><a href="/{episode}/{i}">state {i}</a></li>'
            for i in states
        )
        body = (
            "<!doctype html><meta charset=utf-8>"
            f"<title>{escape(episode)}</title>"
            "<style>body{font-family:-apple-system,sans-serif;background:#1d2a1f;color:#cfe0d4;"
            "padding:24px;max-width:780px;margin:0 auto}h1{font-size:18px}"
            "a{color:#5fb4ff}li{margin:4px 0}</style>"
            f"<h1>{escape(episode)}</h1>"
            f"<p>{len(states)} states</p><ul>{links}</ul>"
        )
        return body

    # ── Rendered board ────────────────────────────────────────────

    @app.get("/<episode>/<int:state>")
    def render_state(episode: str, state: int):
        ep = episode_dir(episode)
        state_dict, criteria = load_episode_state(ep, state)
        state_dir = f"{episode}/{state}"
        graph = _load_graph_cached(ep / "graph.dot")
        buckets = turn_buckets(graph)
        history = load_action_history(ep)
        action_labels = {i: render_action_description(d) for i, d in history.items()}
        # Highlight the action the current player will take from this state
        # (i.e. the next-state action). For state 92 in the example, this
        # is the first action of the new turn, not the "end" that closed
        # the previous turn.
        taken_label = action_labels.get(state + 1, "")
        return render(state_dict, criteria, state_dir=state_dir,
                      turn_buckets_=buckets, episode_id=episode,
                      action_labels=action_labels, taken_label=taken_label)

    @app.get("/<episode>/<int:state>/state.json")
    def state_json(episode: str, state: int):
        ep = episode_dir(episode)
        state_dict, _ = load_episode_state(ep, state)
        return jsonify(state_dict)

    @app.get("/<episode>/<int:state>/criteria.json")
    def criteria_json(episode: str, state: int):
        ep = episode_dir(episode)
        _, criteria = load_episode_state(ep, state)
        return jsonify(criteria)

    # ── Jev proxy ─────────────────────────────────────────────────

    @app.post("/api/jev")
    def api_jev():
        body = request.get_json(silent=True)
        if body is None:
            body = {}
        if not isinstance(body, dict):
            return jsonify({"error": "request body must be an object"}), 400
        state_dir = body.get("state_dir", "")
        question_specs = body.get("questions")
        information = body.get("information", {})

        if not isinstance(state_dir, str):
            return jsonify({"error": "state_dir must be a string"}), 400
        state_dir = state_dir.strip()
        if not state_dir:
            return jsonify({"error": "state_dir required"}), 400
        if not isinstance(question_specs, list):
            return jsonify({"error": "questions must be a list"}), 400
        if not 1 <= len(question_specs) <= 10:
            return jsonify({"error": "questions must contain between 1 and 10 items"}), 400
        if not isinstance(information, dict):
            return jsonify({"error": "information must be an object"}), 400

        normalized_questions = []
        valid_action_types = set(TYPE_ORDER)
        for index, spec in enumerate(question_specs, start=1):
            if not isinstance(spec, dict):
                return jsonify({"error": f"question {index} must be an object"}), 400
            prompt = spec.get("prompt", "")
            action_types = spec.get("action_types")
            if not isinstance(prompt, str) or not prompt.strip():
                return jsonify({"error": f"question {index} prompt required"}), 400
            if not isinstance(action_types, list) or not action_types:
                return jsonify({"error": f"question {index} action_types required"}), 400
            if not all(isinstance(action_type, str) for action_type in action_types):
                return jsonify({"error": f"question {index} action_types must be strings"}), 400
            if not set(action_types) <= valid_action_types:
                return jsonify({"error": f"question {index} has unknown action_types"}), 400
            normalized_questions.append({
                "prompt": prompt.strip(),
                "action_types": list(dict.fromkeys(action_types)),
            })

        if not all(
            isinstance(information.get(field, ""), str)
            for field in INFORMATION_FIELDS
        ):
            return jsonify({"error": "information fields must be strings"}), 400
        information = {
            field: information.get(field, "").strip()
            for field in INFORMATION_FIELDS
        }

        # state_dir is "<episode>/<state>".
        parts = state_dir.split("/")
        if len(parts) != 2:
            return jsonify({"error": "state_dir must be <episode>/<state>"}), 400
        episode, state_str = parts
        try:
            state = int(state_str)
        except ValueError:
            return jsonify({"error": "bad state index"}), 400

        ep = episode_dir(episode)
        state_dict, criteria = load_episode_state(ep, state)

        request_state = build_jev_state(state_dict, information)
        questions, label_maps = build_jev_questions(criteria, normalized_questions)
        for index, question in enumerate(questions.values(), start=1):
            if not question["criteria"]:
                return jsonify({
                    "error": f"question {index} has no answers after action_types filter"
                }), 400

        try:
            response = ask(request_state, questions)
        except JevError as e:
            return jsonify({"error": str(e)}), 502

        answers = response.get("answers", {})
        results = []
        for index, spec in enumerate(normalized_questions, start=1):
            question_id = f"question_{index}"
            answer = answers.get(question_id, {})
            label = answer.get("choice", "")
            results.append({
                "question_id": question_id,
                "prompt": spec["prompt"],
                "chosen_label": label,
                "engine_description": label_maps[question_id].get(label, ""),
                "probabilities": answer.get("probabilities", {}),
                "confidence": answer.get("confidence"),
            })
        return jsonify({
            "results": results,
            "usage": response.get("usage", {}),
        })

    @app.post("/api/jev/default")
    def api_jev_default():
        body = request.get_json(silent=True)
        if body is None:
            body = {}
        if not isinstance(body, dict):
            return jsonify({"error": "request body must be an object"}), 400

        state_dir = body.get("state_dir", "")
        information = body.get("information", {})
        if not isinstance(state_dir, str):
            return jsonify({"error": "state_dir must be a string"}), 400
        state_dir = state_dir.strip()
        if not state_dir:
            return jsonify({"error": "state_dir required"}), 400
        if not isinstance(information, dict):
            return jsonify({"error": "information must be an object"}), 400
        if not all(
            isinstance(information.get(field, ""), str)
            for field in INFORMATION_FIELDS
        ):
            return jsonify({"error": "information fields must be strings"}), 400
        information = {
            field: information.get(field, "").strip()
            for field in INFORMATION_FIELDS
        }

        parts = state_dir.split("/")
        if len(parts) != 2:
            return jsonify({"error": "state_dir must be <episode>/<state>"}), 400
        episode, state_str = parts
        try:
            state = int(state_str)
        except ValueError:
            return jsonify({"error": "bad state index"}), 400

        ep = episode_dir(episode)
        state_dict, criteria = load_episode_state(ep, state)
        questions, metadata = build_jev_default_questions(criteria, information)
        if not questions:
            return jsonify({"error": "state has no legal actions"}), 400

        request_state = build_jev_state(state_dict, information)
        started_at = time.perf_counter()
        try:
            response = ask(request_state, questions)
        except JevError as e:
            return jsonify({"error": str(e)}), 502
        elapsed_ms = round((time.perf_counter() - started_at) * 1000)

        answers = response.get("answers", {})
        bundles = {}

        for question_id, item in metadata.items():
            answer = answers.get(question_id, {})
            bundle_key = item["lens_id"] or "base"
            bundle = bundles.setdefault(bundle_key, {
                "id": item["lens_id"],
                "label": item["lens_label"],
                "per_action": [],
                "by_class": {},
                "rank_action_groups": None,
                "question_count": 0,
            })
            bundle["question_count"] += 1
            if item["layer"] == "action":
                bundle["per_action"].append({
                    "question_id": question_id,
                    "action_id": item["id"],
                    "action_type": item["type"],
                    "label": item["label"],
                    "engine_description": item["engine_description"],
                    "noul": answer.get("noul"),
                })
                continue

            if item["layer"] == "action_group":
                options = item["options"]
                probabilities = answer.get("probabilities", {})
                ranking = [
                    {
                        "action_id": action_id,
                        "label": option["label"],
                        "engine_description": option["engine_description"],
                        "probability": probabilities.get(action_id),
                    }
                    for action_id, option in options.items()
                ]
                ranking.sort(
                    key=lambda row: (
                        row["probability"] is not None,
                        row["probability"] or 0,
                    ),
                    reverse=True,
                )
                chosen_id = answer.get("choice", "")
                chosen = options.get(chosen_id, {})
                bundle["by_class"][item["action_type"]] = {
                    "question_id": question_id,
                    "chosen_action_id": chosen_id,
                    "chosen_label": chosen.get("label", ""),
                    "engine_description": chosen.get("engine_description", ""),
                    "confidence": answer.get("confidence"),
                    "ranking": ranking,
                }
                continue

            if item["layer"] == "action_groups":
                probabilities = answer.get("probabilities", {})
                ranking = [
                    {
                        "action_type": action_type,
                        "description": description,
                        "probability": probabilities.get(action_type),
                    }
                    for action_type, description in item["options"].items()
                ]
                ranking.sort(
                    key=lambda row: (
                        row["probability"] is not None,
                        row["probability"] or 0,
                    ),
                    reverse=True,
                )
                bundle["rank_action_groups"] = {
                    "question_id": question_id,
                    "chosen_action_group": answer.get("choice", ""),
                    "confidence": answer.get("confidence"),
                    "ranking": ranking,
                }

        for bundle in bundles.values():
            actions_by_class = {}
            for action in bundle["per_action"]:
                actions_by_class.setdefault(action["action_type"], []).append(action)
            for action_type, actions in actions_by_class.items():
                if action_type == "end" or len(actions) != 1:
                    continue
                action = actions[0]
                bundle["by_class"][action_type] = {
                    "question_id": None,
                    "chosen_action_id": action["action_id"],
                    "chosen_label": action["label"],
                    "engine_description": action["engine_description"],
                    "confidence": None,
                    "ranking": [],
                }

        base = bundles.pop("base", {
            "per_action": [],
            "by_class": {},
            "rank_action_groups": None,
            "question_count": 0,
        })
        return jsonify({
            "per_action": base["per_action"],
            "by_class": base["by_class"],
            "rank_action_groups": base["rank_action_groups"],
            "base_question_count": base["question_count"],
            "lenses": list(bundles.values()),
            "question_count": len(questions),
            "elapsed_ms": elapsed_ms,
            "model": response.get("model", ""),
            "usage": response.get("usage", {}),
        })

    return app


def escape(s):
    from html import escape as _e
    return _e(str(s))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    app = create_app()
    print(f"jev-server listening on http://{args.host}:{args.port}")
    # debug=True enables the Werkzeug reloader: edits to .py or .j2 files
    # are picked up automatically on the next request, no manual restart.
    app.run(host=args.host, port=args.port, debug=True, use_reloader=True)


if __name__ == "__main__":
    main()
