"""
Tiny client for the TypeSafe / Jev API.

Single endpoint, three primitives. We only need a couple of helpers:

    from lib.typesafe import ask
    answer = ask(state={"cards": ...}, questions={
        "best_action": {
            "type": "choice",
            "instructions": "Pick the action most likely to win.",
            "criteria": {"Quest with X (1 lore)": ..., "End turn": ...},
        },
    })

API contract: https://docs.typesafe.ai/api

API key resolution: explicit `api_key=`, then TYPESAFE_API_KEY env var,
then a `TYPESAFE_API_KEY=...` line in ./.env (project root).
"""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


ENDPOINT = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"
MAX_RETRIES = 4


class JevError(RuntimeError):
    """Raised when the Jev API returns a non-retryable error."""


def _load_dotenv(path: Path) -> dict[str, str]:
    """Minimal .env loader: KEY=value lines, no expansion, no shell features."""
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def _resolve_key(api_key: str | None) -> str | None:
    if api_key:
        return api_key
    val = os.environ.get("TYPESAFE_API_KEY")
    if val:
        return val
    project_root = Path(__file__).resolve().parent.parent
    return _load_dotenv(project_root / ".env").get("TYPESAFE_API_KEY")


def _post_json(url: str, payload: dict, api_key: str) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "graph-trajectories/0.1 (+https://github.com/anomalyco/opencode)",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ask(
    state: dict | str | list,
    questions: dict,
    *,
    model: str = DEFAULT_MODEL,
    api_key: str | None = None,
    max_retries: int = MAX_RETRIES,
) -> dict:
    """
    Evaluate `state` against `questions` (a dict of typed question objects).

    Returns the raw response dict: {"answers": {qid: ...}, "model": ..., "usage": ...}.

    Retries on 429 (rate limit) and 529 (overloaded) with exponential backoff.
    """
    key = _resolve_key(api_key)
    if not key:
        raise JevError(
            "no API key — set TYPESAFE_API_KEY, pass api_key=, "
            "or add TYPESAFE_API_KEY=... to .env"
        )

    payload = {"model": model, "state": state, "questions": questions}

    delay = 1.0
    for attempt in range(max_retries):
        try:
            return _post_json(ENDPOINT, payload, key)
        except urllib.error.HTTPError as e:
            if e.code in (429, 529) and attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            detail = e.read().decode("utf-8", errors="replace")
            raise JevError(f"Jev API {e.code}: {detail}") from None
        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise JevError(f"network error: {e}") from None

    raise JevError("exhausted retries")

