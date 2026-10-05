import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from lib.render import (  # noqa: E402
    active_jev_lenses,
    build_jev_default_questions,
    build_jev_questions,
    build_jev_state,
    filter_criteria,
    render,
)


@pytest.fixture
def state():
    player = {
        "lore": 0,
        "inkwell": 0,
        "hand": [],
        "in_play": {},
        "discard": [],
    }
    return {
        "cards": {},
        "board_state": {
            "turn": 1,
            "phase": "main",
            "me": player,
            "opponent": player,
        },
    }


@pytest.fixture
def server_module():
    spec = importlib.util.spec_from_file_location(
        "jev_server", ROOT / "bin" / "jev-server.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_jev_state_prunes_information_and_stores_lens_paths(state):
    request_state = build_jev_state(state, {
        "player": "Tempo player",
        "deck": "Amber Steel",
    })

    assert "information" not in state
    assert request_state["information"] == {
        "player": "Tempo player",
        "deck": "Amber Steel",
    }
    assert request_state["decision_lenses"]["player_deck"] == {
        "label": "Player + Deck",
        "information_paths": ["information.player", "information.deck"],
    }


def test_build_jev_state_omits_empty_information(state):
    request_state = build_jev_state(state, {})

    assert "information" not in request_state
    assert "decision_lenses" not in request_state


def test_build_jev_questions_contains_ordered_prompts_and_generated_answers():
    criteria = {
        "end": "End the turn",
        "play:p1.simba.a": "Play Simba",
        "quest:p1.simba.a": "Quest with Simba (1 lore)",
    }

    questions, label_maps = build_jev_questions(criteria, [
        {"prompt": "What should I play?", "action_types": ["play"]},
        {"prompt": "How should I gain lore?", "action_types": ["end", "quest"]},
    ])

    assert questions == {
        "question_1": {
            "type": "choice",
            "instructions": "What should I play?",
            "criteria": {
                "Play Simba": "Pay this card's cost and put it into play.",
            },
        },
        "question_2": {
            "type": "choice",
            "instructions": "How should I gain lore?",
            "criteria": {
                "End the turn": "End the turn without taking an action.",
                "Quest with Simba (1 lore)": (
                    "Send this character to quest for lore (exerting it)."
                ),
            },
        }
    }
    assert label_maps == {
        "question_1": {"Play Simba": "play:p1.simba.a"},
        "question_2": {
            "End the turn": "end",
            "Quest with Simba (1 lore)": "quest:p1.simba.a",
        },
    }


def test_filter_criteria_keeps_only_selected_action_types():
    criteria = {
        "end": "End the turn",
        "ink:p1.card.a": "Ink Card",
        "play:p1.card.a": "Play Card",
    }

    assert filter_criteria(criteria, ["play"]) == {
        "play:p1.card.a": "Play Card",
    }


def test_build_jev_default_questions_emits_all_three_layers():
    criteria = {
        "end": "End the turn",
        "play:p1.simba.a": "Play Simba",
        "play:p1.nala.a": "Play Nala",
        "quest:p1.simba.a": "Quest with Simba (1 lore)",
    }

    questions, metadata = build_jev_default_questions(criteria)

    assert [qid for qid in questions if qid.startswith("should_action_")] == [
        "should_action_1",
        "should_action_2",
        "should_action_3",
        "should_action_4",
    ]
    assert questions["should_action_2"]["type"] == "noul"
    assert questions["should_action_2"]["instructions"]["candidate_action"] == {
        "id": "action_2",
        "class": "play",
        "description": "Play Simba",
    }
    assert set(questions["rank_play"]["criteria"]) == {
        "action_2",
        "action_3",
    }
    assert "rank_end" not in questions
    assert "rank_quest" not in questions
    assert set(questions["rank_action_groups"]["criteria"]) == {
        "end",
        "play",
        "quest",
    }
    assert metadata["should_action_2"] == {
        "layer": "action",
        "lens_id": None,
        "lens_label": "All information",
        "id": "action_2",
        "type": "play",
        "label": "Play Simba",
        "engine_description": "play:p1.simba.a",
    }
    assert metadata["rank_play"]["options"]["action_3"]["label"] == "Play Nala"


def test_build_jev_default_questions_adds_permissive_lens_bundles():
    criteria = {
        "end": "End the turn",
        "play:p1.simba.a": "Play Simba",
    }

    questions, metadata = build_jev_default_questions(criteria, {
        "player": "Aggressively pursue lore.",
        "deck": "",
    })

    assert set(lens["id"] for lens in active_jev_lenses({"player": "Aggressive"})) == {
        "player",
        "player_deck_history",
        "player_deck",
    }
    assert "lens_player__should_action_1" in questions
    assert "lens_player_deck__rank_play" not in questions
    assert "lens_player_deck_history__rank_action_groups" in questions
    assert "lens_deck__should_action_1" not in questions
    player_question = questions["lens_player__should_action_1"]["instructions"]["question"]
    assert "`decision_lenses.player`" in player_question
    assert "Aggressively pursue lore" not in player_question
    assert "lens_player__rank_play" not in metadata


def test_build_jev_default_questions_keeps_duplicate_labels_distinct():
    criteria = {
        "play:p1.simba.a": "Play Simba",
        "play:p1.simba.b": "Play Simba",
    }

    questions, metadata = build_jev_default_questions(criteria)

    assert set(questions["rank_play"]["criteria"]) == {"action_1", "action_2"}
    assert metadata["rank_play"]["options"]["action_1"]["engine_description"] != (
        metadata["rank_play"]["options"]["action_2"]["engine_description"]
    )


def test_build_jev_default_questions_handles_no_actions():
    questions, metadata = build_jev_default_questions({})

    assert questions == {}
    assert metadata == {}


def test_render_has_default_question_and_information_tabs(state):
    html = render(
        state,
        {"end": "End the turn"},
        state_dir="game/1",
        episode_id="game",
    )

    assert 'id="default-tab"' in html
    assert 'id="questions-tab"' in html
    assert 'id="information-tab"' in html
    assert html.index('id="default-tab"') < html.index('id="questions-tab"')
    assert 'id="default-panel"' in html
    assert 'id="questions-panel"' in html
    assert 'id="information-panel"' in html
    assert '<label for="player">Player</label>' in html
    assert '<label for="deck">Deck</label>' in html
    assert '<label for="past-matches">Past matches</label>' in html
    assert '<label for="future-lines">Future Lines I See</label>' in html
    assert 'id="question-list"' in html
    assert 'id="question-row-template"' in html
    assert 'id="add-question"' in html
    assert 'id="ask-all"' in html
    assert "const questionLimit = 10;" in html
    assert 'Array.isArray(saved.questions)' in html
    assert 'typeof saved.question === "string"' in html
    assert 'const INFORMATION_STORAGE_KEY = "jev-information";' in html
    assert 'const QUESTION_STORAGE_KEY = "jev-question:" + window.STATE_DIR;' in html
    assert 'const DEFAULT_RESULT_STORAGE_KEY = "jev-default-result:" + window.STATE_DIR;' in html
    assert 'fetch("/api/jev/default"' in html
    assert 'localStorage.setItem(DEFAULT_RESULT_STORAGE_KEY' in html
    assert 'class="lens-table"' in html
    assert "function renderLensTable" in html
    assert 'class="result-metadata"' in html
    assert "function renderDefaultMetadata" in html
    assert "lens-winner" in html
    assert "lens-error" in html
    assert "Math.abs(value - otherAverage) >= 0.15" in html
    assert "lens-error-label" not in html


def test_api_asks_multiple_questions_in_one_call(
    monkeypatch, tmp_path, server_module, state
):
    criteria = {
        "end": "End the turn",
        "play:p1.card.a": "Play Card",
        "quest:p1.card.a": "Quest with Card",
    }
    captured = {}

    monkeypatch.setattr(server_module, "EPISODES_ROOT", tmp_path)
    monkeypatch.setattr(
        server_module,
        "load_episode_state",
        lambda _episode, _index: (state, criteria),
    )

    def fake_ask(request_state, questions):
        captured["state"] = request_state
        captured["questions"] = questions
        return {
            "answers": {
                "question_1": {
                    "choice": "Play Card",
                    "probabilities": {"Play Card": 1.0},
                    "confidence": 1.0,
                },
                "question_2": {
                    "choice": "Quest with Card",
                    "probabilities": {"Quest with Card": 0.8, "End the turn": 0.2},
                    "confidence": 0.8,
                },
            },
            "usage": {"input_tokens": 100, "output_tokens": 20},
        }

    monkeypatch.setattr(server_module, "ask", fake_ask)
    client = server_module.create_app().test_client()

    response = client.post("/api/jev", json={
        "state_dir": "game/1",
        "questions": [
            {"prompt": "  What should I play?  ", "action_types": ["play"]},
            {
                "prompt": "How should I gain lore?",
                "action_types": ["end", "quest"],
            },
        ],
        "information": {
            "player": "  Tempo player  ",
            "deck": "Amber Steel",
            "past_matches": "Lost to evasive",
            "future_lines": "Race over two turns",
        },
    })

    assert response.status_code == 200
    assert captured["state"]["information"] == {
        "player": "Tempo player",
        "deck": "Amber Steel",
        "past_matches": "Lost to evasive",
        "future_lines": "Race over two turns",
    }
    assert captured["questions"]["question_1"] == {
        "type": "choice",
        "instructions": "What should I play?",
        "criteria": {"Play Card": "Pay this card's cost and put it into play."},
    }
    assert set(captured["questions"]["question_2"]["criteria"]) == {
        "End the turn",
        "Quest with Card",
    }
    assert response.get_json() == {
        "results": [
            {
                "question_id": "question_1",
                "prompt": "What should I play?",
                "chosen_label": "Play Card",
                "engine_description": "play:p1.card.a",
                "probabilities": {"Play Card": 1.0},
                "confidence": 1.0,
            },
            {
                "question_id": "question_2",
                "prompt": "How should I gain lore?",
                "chosen_label": "Quest with Card",
                "engine_description": "quest:p1.card.a",
                "probabilities": {"End the turn": 0.2, "Quest with Card": 0.8},
                "confidence": 0.8,
            },
        ],
        "usage": {"input_tokens": 100, "output_tokens": 20},
    }


def test_api_default_asks_all_three_layers(
    monkeypatch, tmp_path, server_module, state
):
    criteria = {
        "end": "End the turn",
        "play:p1.simba.a": "Play Simba",
        "play:p1.nala.a": "Play Nala",
    }
    captured = {}

    monkeypatch.setattr(server_module, "EPISODES_ROOT", tmp_path)
    monkeypatch.setattr(
        server_module,
        "load_episode_state",
        lambda _episode, _index: (state, criteria),
    )

    def fake_ask(request_state, questions):
        captured["state"] = request_state
        captured["questions"] = questions
        return {
            "model": "jev-test",
            "answers": {
                "should_action_1": {"type": "noul", "noul": 0.1},
                "should_action_2": {"type": "noul", "noul": 0.8},
                "should_action_3": {"type": "noul", "noul": 0.6},
                "rank_play": {
                    "type": "choice",
                    "choice": "action_2",
                    "probabilities": {"action_2": 0.7, "action_3": 0.3},
                    "confidence": 0.6,
                },
                "rank_action_groups": {
                    "type": "choice",
                    "choice": "play",
                    "probabilities": {"end": 0.1, "play": 0.9},
                    "confidence": 0.8,
                },
            },
            "usage": {"input_tokens": 300, "output_tokens": 60},
        }

    monkeypatch.setattr(server_module, "ask", fake_ask)
    client = server_module.create_app().test_client()

    response = client.post("/api/jev/default", json={
        "state_dir": "game/1",
        "information": {},
    })

    assert response.status_code == 200
    assert len(captured["questions"]) == 5
    assert captured["questions"]["should_action_1"]["type"] == "noul"
    assert captured["questions"]["rank_play"]["type"] == "choice"
    assert captured["questions"]["rank_action_groups"]["type"] == "choice"
    assert "information" not in captured["state"]

    data = response.get_json()
    assert data["question_count"] == 5
    assert data["base_question_count"] == 5
    assert data["lenses"] == []
    assert data["model"] == "jev-test"
    assert isinstance(data["elapsed_ms"], int)
    assert data["per_action"][1]["label"] == "Play Simba"
    assert data["per_action"][1]["noul"] == 0.8
    assert data["by_class"]["play"]["chosen_label"] == "Play Simba"
    assert data["by_class"]["play"]["ranking"][0]["label"] == "Play Simba"
    assert data["rank_action_groups"]["chosen_action_group"] == "play"
    assert data["rank_action_groups"]["ranking"][0]["action_type"] == "play"
    assert data["usage"] == {"input_tokens": 300, "output_tokens": 60}


def test_api_default_groups_active_lens_results(
    monkeypatch, tmp_path, server_module, state
):
    criteria = {
        "end": "End the turn",
        "play:p1.simba.a": "Play Simba",
    }
    monkeypatch.setattr(server_module, "EPISODES_ROOT", tmp_path)
    monkeypatch.setattr(
        server_module,
        "load_episode_state",
        lambda _episode, _index: (state, criteria),
    )

    def fake_ask(_request_state, questions):
        answers = {}
        for question_id, question in questions.items():
            if question["type"] == "noul":
                answers[question_id] = {"type": "noul", "noul": 0.75}
                continue
            options = list(question["criteria"])
            answers[question_id] = {
                "type": "choice",
                "choice": options[0],
                "probabilities": {
                    option: 1.0 if index == 0 else 0.0
                    for index, option in enumerate(options)
                },
                "confidence": 1.0,
            }
        return {"answers": answers, "usage": {}}

    monkeypatch.setattr(server_module, "ask", fake_ask)
    client = server_module.create_app().test_client()

    response = client.post("/api/jev/default", json={
        "state_dir": "game/1",
        "information": {"player": "Aggressive"},
    })

    assert response.status_code == 200
    data = response.get_json()
    assert data["question_count"] == 12
    assert [lens["id"] for lens in data["lenses"]] == [
        "player",
        "player_deck_history",
        "player_deck",
    ]
    assert data["lenses"][0]["per_action"][0]["noul"] == 0.75
    assert data["lenses"][0]["by_class"]["play"]["chosen_label"] == "Play Simba"
    assert data["lenses"][0]["by_class"]["play"]["confidence"] is None
    assert data["lenses"][0]["by_class"]["play"]["ranking"] == []


def test_api_default_has_no_generated_question_cap(
    monkeypatch, tmp_path, server_module, state
):
    monkeypatch.setattr(server_module, "EPISODES_ROOT", tmp_path)
    monkeypatch.setattr(
        server_module,
        "load_episode_state",
        lambda _episode, _index: (state, {"end": "End the turn"}),
    )
    monkeypatch.setattr(
        server_module,
        "build_jev_default_questions",
        lambda _criteria, _information: (
            {f"question_{index}": {} for index in range(31)},
            {},
        ),
    )
    monkeypatch.setattr(
        server_module,
        "ask",
        lambda _state, _questions: {"answers": {}, "usage": {}},
    )
    client = server_module.create_app().test_client()

    response = client.post("/api/jev/default", json={"state_dir": "game/1"})

    assert response.status_code == 200
    assert response.get_json()["question_count"] == 31


@pytest.mark.parametrize(
    "payload,error",
    [
        ([], "request body must be an object"),
        ({"state_dir": "game/1", "questions": "Q"}, "questions must be a list"),
        (
            {"state_dir": "game/1", "questions": []},
            "questions must contain between 1 and 10 items",
        ),
        (
            {
                "state_dir": "game/1",
                "questions": [
                    {"prompt": "Q", "action_types": ["play"]}
                ] * 11,
            },
            "questions must contain between 1 and 10 items",
        ),
        (
            {"state_dir": "game/1", "questions": [{"prompt": "", "action_types": ["play"]}]},
            "question 1 prompt required",
        ),
        (
            {"state_dir": "game/1", "questions": [{"prompt": "Q", "action_types": []}]},
            "question 1 action_types required",
        ),
        (
            {"state_dir": "game/1", "questions": [{"prompt": "Q", "action_types": ["fly"]}]},
            "question 1 has unknown action_types",
        ),
        (
            {
                "state_dir": "game/1",
                "questions": [{"prompt": "Q", "action_types": ["play"]}],
                "information": [],
            },
            "information must be an object",
        ),
    ],
)
def test_api_rejects_invalid_request_shapes(server_module, payload, error):
    client = server_module.create_app().test_client()

    response = client.post("/api/jev", json=payload)

    assert response.status_code == 400
    assert error in response.get_json()["error"]
