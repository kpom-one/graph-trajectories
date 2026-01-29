#!/usr/bin/env python3
"""
Generate a narrative story from a card's trajectory.

Reads the trajectory JSONL and game.jsonl to produce a human-readable
story from the card's perspective, focusing on meaningful moments.

Usage:
    python bin/trajectory-story.py <episode_path> <card_id>
    python bin/trajectory-story.py output/episodes/abc.episode p1.aladdin_prince_ali.d
    python bin/trajectory-story.py --narrative <episode_path> <card_id>
"""
import sys
import json
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file into a list of dicts."""
    records = []
    with open(path) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def load_result(episode_path: Path) -> dict:
    """Load result.json for game outcome."""
    result_path = episode_path / "result.json"
    if result_path.exists():
        with open(result_path) as f:
            return json.load(f)
    return {}


def load_game_states(episode_path: Path) -> dict[int, dict]:
    """Load game.jsonl indexed by state number."""
    game_path = episode_path / "trajectories" / "game.jsonl"
    records = load_jsonl(game_path)
    return {r["state"]: r for r in records}


def get_lore_delta(prev_game: dict, curr_game: dict, player: str) -> int | None:
    """Get lore change for a player between two game states."""
    if not prev_game or not curr_game:
        return None
    prev_lore = int(prev_game.get(f"{player}_lore", 0))
    curr_lore = int(curr_game.get(f"{player}_lore", 0))
    delta = curr_lore - prev_lore
    return delta if delta != 0 else None


def load_trajectory(episode_path: Path, card_id: str) -> list[dict]:
    """Load a card's trajectory."""
    traj_path = episode_path / "trajectories" / f"{card_id}.jsonl"
    if not traj_path.exists():
        raise FileNotFoundError(f"No trajectory for {card_id}")
    return load_jsonl(traj_path)


def edges_changed(prev_edges: list, curr_edges: list) -> tuple[list, list]:
    """Return (gained, lost) edges."""
    prev_set = set(prev_edges or [])
    curr_set = set(curr_edges or [])
    gained = sorted(curr_set - prev_set)
    lost = sorted(prev_set - curr_set)
    return gained, lost


def infer_actor_owner(action: str) -> str | None:
    """Infer which player is acting from the action string."""
    actor = extract_actor(action)
    if actor and actor.startswith("p1"):
        return "p1"
    elif actor and actor.startswith("p2"):
        return "p2"
    return None


def is_my_turn(game_state: dict, card_id: str, action: str) -> bool:
    """Check if it's this card's owner's turn."""
    owner = card_id.split(".")[0]  # p1 or p2
    current = game_state.get("current_player")
    if current:
        return current == owner
    # Fallback: infer from action
    actor_owner = infer_actor_owner(action)
    return actor_owner == owner


def format_edges(edges: list) -> str:
    """Format edge list for display."""
    if not edges:
        return ""
    return ", ".join(e.replace("can_", "") for e in edges)


def get_action_type(action: str) -> str:
    """Extract action type from action string."""
    if ":" in action:
        return action.split(":")[0]
    return action


def extract_actor(action: str) -> str | None:
    """Extract who did the action."""
    if action in ("initial", "end", "unknown"):
        return None
    if "->" in action:
        # challenge:p1.card->p2.target
        actor_part = action.split("->")[0]
        if ":" in actor_part:
            return actor_part.split(":", 1)[1]
    elif ":" in action:
        return action.split(":", 1)[1]
    return None


def generate_story(episode_path: Path, card_id: str) -> str:
    """Generate narrative story for a card."""
    game_states = load_game_states(episode_path)
    trajectory = load_trajectory(episode_path, card_id)
    result = load_result(episode_path)

    owner = card_id.split(".")[0]
    opponent = "p2" if owner == "p1" else "p1"

    lines = []
    lines.append(f"{card_id}")
    lines.append("=" * len(card_id))
    lines.append("")

    current_turn = None
    prev_edges = []
    prev_game = {}
    noise_count = 0

    for i, record in enumerate(trajectory):
        state_idx = record["state"]
        game = game_states.get(state_idx, {})
        role = record.get("role", "observer")
        action = record.get("action", "")
        zone = record.get("zone")
        edges = record.get("edges", [])
        exerted = record.get("exerted")
        damage = record.get("damage")

        turn = game.get("turn", "?")
        p1_lore = game.get("p1_lore", "0")
        p2_lore = game.get("p2_lore", "0")
        current_player = game.get("current_player")
        my_turn = is_my_turn(game, card_id, action)

        # Turn header
        if turn != current_turn:
            if noise_count > 0:
                lines.append(f"    ... ({noise_count} actions)")
                noise_count = 0
            lines.append("")
            turn_marker = f"Turn {turn}"
            player_marker = f"({current_player})" if current_player else ""
            lore_marker = f"{owner}:{p1_lore if owner == 'p1' else p2_lore} | {opponent}:{p2_lore if owner == 'p1' else p1_lore}"
            lines.append(f"═══ {turn_marker} {player_marker} ═══ {lore_marker}")
            current_turn = turn

        # Check edge changes
        gained, lost = edges_changed(prev_edges, edges)

        # Determine if this line is signal or noise
        is_signal = False
        line_parts = []

        if role == "actor":
            is_signal = True
            action_type = get_action_type(action).upper()
            if action_type == "PLAY":
                line_parts.append(f"[{state_idx}] >>> PLAYED <<<")
                line_parts.append(f"      zone: {zone}")
            elif action_type == "QUEST":
                line_parts.append(f"[{state_idx}] >>> QUESTED <<<")
                line_parts.append(f"      exerted")
                lore_delta = get_lore_delta(prev_game, game, owner)
                if lore_delta:
                    prev_lore = int(prev_game.get(f"{owner}_lore", 0))
                    curr_lore = int(game.get(f"{owner}_lore", 0))
                    line_parts.append(f"      {owner} lore: {prev_lore} → {curr_lore} (+{lore_delta})")
            elif action_type == "INK":
                line_parts.append(f"[{state_idx}] >>> INKED (removed from game) <<<")
            elif action_type == "CHALLENGE":
                target = action.split("->")[1] if "->" in action else "?"
                line_parts.append(f"[{state_idx}] >>> CHALLENGED {target} <<<")
            else:
                line_parts.append(f"[{state_idx}] >>> {action_type} <<<")

        elif role == "target":
            is_signal = True
            action_type = get_action_type(action).upper()
            actor = extract_actor(action)
            if action_type == "CHALLENGE":
                line_parts.append(f"[{state_idx}] !!! CHALLENGED by {actor} !!!")
                if zone == "discard":
                    line_parts.append(f"      → BANISHED")
                elif damage and damage != "0":
                    line_parts.append(f"      damage: {damage}")
            else:
                line_parts.append(f"[{state_idx}] !!! TARGETED by {action} !!!")

        elif role == "byproduct":
            is_signal = True
            if action == "initial":
                line_parts.append(f"[{state_idx}] Drawn into hand")
            elif zone == "ink":
                # This shouldn't happen - ink should be actor
                line_parts.append(f"[{state_idx}] Moved to ink")
            elif zone == "discard":
                line_parts.append(f"[{state_idx}] Banished")
            elif zone is None:
                line_parts.append(f"[{state_idx}] Removed from game")
            elif exerted == "0" and i > 0 and trajectory[i-1].get("exerted") == "1":
                line_parts.append(f"[{state_idx}] Readied")
            else:
                line_parts.append(f"[{state_idx}] State changed: zone={zone}")

        elif role == "observer":
            # Check if this is a meaningful decision point
            action_type = get_action_type(action)
            actor = extract_actor(action)

            # Did they choose something else when I had the same option?
            # Only show if it changed my edges (gained or lost something)
            if my_turn and action_type in ("play", "ink", "quest", "challenge"):
                can_key = f"can_{action_type}"
                my_could = can_key in prev_edges
                if my_could and actor and card_id not in action and (gained or lost):
                    is_signal = True
                    line_parts.append(f"[{state_idx}] {owner} chose to {action_type} {actor}")
                    remaining = [e for e in prev_edges if e != can_key]
                    if remaining:
                        line_parts.append(f"      I could still: {format_edges(remaining)}")

        # Edge changes are signal, but format nicely
        if gained and zone in ("hand", "play"):
            is_signal = True
            if not line_parts:
                # Show what action caused this edge change
                action_type = get_action_type(action)
                if action_type == "end":
                    line_parts.append(f"[{state_idx}] (turn ended)")
                else:
                    line_parts.append(f"[{state_idx}] (after {action_type})")
            line_parts.append(f"      +++ gained: {format_edges(gained)}")

        if lost and zone in ("hand", "play") and role not in ("actor", "target"):
            # Don't show "lost" for actor/target - it's implicit
            is_signal = True
            if not line_parts:
                action_type = get_action_type(action)
                if action_type == "end":
                    line_parts.append(f"[{state_idx}] (turn ended)")
                else:
                    line_parts.append(f"[{state_idx}] (after {action_type})")
            line_parts.append(f"      --- lost: {format_edges(lost)}")

        # Output or count noise
        if is_signal:
            if noise_count > 0:
                lines.append(f"    ... ({noise_count} actions)")
                noise_count = 0
            for part in line_parts:
                lines.append(part)
        else:
            noise_count += 1

        prev_edges = edges
        prev_game = game

    # Final noise
    if noise_count > 0:
        lines.append(f"    ... ({noise_count} actions)")

    # Game outcome
    if result:
        lines.append("")
        lines.append("═══ GAME RESULT ═══")
        winner = result.get("winner", "?")
        final_lore = result.get("final_lore", {})
        p1_final = final_lore.get("p1", "?")
        p2_final = final_lore.get("p2", "?")
        total_turns = result.get("total_turns", "?")

        outcome = "WIN" if winner == owner else "LOSS"
        lines.append(f"  {outcome}: {winner} wins")
        lines.append(f"  Final: p1={p1_final}, p2={p2_final}")
        lines.append(f"  Turns: {total_turns}")

    return "\n".join(lines)


def format_card_name(card_id: str) -> str:
    """Convert card_id to readable name: p1.mulan_free_spirit.b -> Mulan, Free Spirit"""
    parts = card_id.split(".")
    if len(parts) >= 2:
        name_part = parts[1]  # mulan_free_spirit or robin_hood_beloved_outlaw
        # Convert underscores to spaces and title case
        words = name_part.replace("_", " ").title()
        return words
    return card_id


def format_other_card(card_id: str) -> str:
    """Format another card's name for narrative."""
    return format_card_name(card_id)


def edge_to_verb(edge: str) -> str:
    """Convert edge to verb phrase."""
    mapping = {
        "can_play": "be played",
        "can_ink": "be inked",
        "can_quest": "quest",
        "can_challenge": "challenge",
    }
    return mapping.get(edge, edge.replace("can_", ""))


def edge_to_noun(edge: str) -> str:
    """Convert edge to noun phrase for abilities."""
    mapping = {
        "can_play": "play",
        "can_ink": "ink",
        "can_quest": "quest",
        "can_challenge": "challenge",
    }
    return mapping.get(edge, edge.replace("can_", ""))


def generate_narrative(episode_path: Path, card_id: str) -> str:
    """Generate prose narrative for a card's trajectory."""
    game_states = load_game_states(episode_path)
    trajectory = load_trajectory(episode_path, card_id)
    result = load_result(episode_path)

    owner = card_id.split(".")[0]
    owner_name = "my owner" if owner == "p1" else "my owner"
    opponent = "p2" if owner == "p1" else "p1"
    card_name = format_card_name(card_id)

    # Collect events by turn for grouping
    events_by_turn = {}  # turn -> list of event dicts

    # Stats for arc summary
    stats = {
        "turns_in_hand": 0,
        "turns_in_play": 0,
        "quests": 0,
        "challenges_made": 0,
        "challenges_received": 0,
        "damage_taken": 0,
        "final_state": "unknown",
        "play_turn": None,
        "death_turn": None,
        "lore_contributed": 0,
    }

    prev_edges = []
    prev_turn = None
    prev_zone = None
    prev_game = {}

    for i, record in enumerate(trajectory):
        state_idx = record["state"]
        game = game_states.get(state_idx, {})
        role = record.get("role", "observer")
        action = record.get("action", "")
        zone = record.get("zone")
        edges = record.get("edges", [])
        exerted = record.get("exerted")
        damage = record.get("damage")

        turn = int(game.get("turn", 0))
        my_turn = is_my_turn(game, card_id, action)
        action_type = get_action_type(action)

        # Calculate lore delta
        lore_delta = get_lore_delta(prev_game, game, owner)

        if turn not in events_by_turn:
            events_by_turn[turn] = []

        # Track zone time
        if zone == "hand" and prev_zone != "hand":
            pass  # entering hand
        if zone == "play" and prev_zone != "play":
            stats["play_turn"] = turn

        # Check edge changes
        gained, lost = edges_changed(prev_edges, edges)

        event = {
            "state": state_idx,
            "role": role,
            "action": action,
            "action_type": action_type,
            "zone": zone,
            "edges": edges,
            "gained": gained,
            "lost": lost,
            "exerted": exerted,
            "damage": damage,
            "my_turn": my_turn,
            "turn": turn,
            "prev_edges": prev_edges.copy(),
            "lore_delta": lore_delta,
            "prev_lore": int(prev_game.get(f"{owner}_lore", 0)) if prev_game else 0,
            "curr_lore": int(game.get(f"{owner}_lore", 0)),
        }

        # Classify event type
        if role == "actor":
            if action_type == "play":
                event["narrative_type"] = "played"
            elif action_type == "quest":
                event["narrative_type"] = "quested"
                stats["quests"] += 1
            elif action_type == "ink":
                event["narrative_type"] = "inked"
                stats["final_state"] = "inked"
                stats["death_turn"] = turn
            elif action_type == "challenge":
                event["narrative_type"] = "challenged"
                stats["challenges_made"] += 1
            else:
                event["narrative_type"] = "acted"

        elif role == "target":
            if action_type == "challenge":
                stats["challenges_received"] += 1
                if zone == "discard":
                    event["narrative_type"] = "banished"
                    stats["final_state"] = "banished"
                    stats["death_turn"] = turn
                    if damage:
                        stats["damage_taken"] = int(damage) if damage.isdigit() else 0
                else:
                    event["narrative_type"] = "damaged"
                    if damage:
                        stats["damage_taken"] = int(damage) if damage.isdigit() else 0
            else:
                event["narrative_type"] = "targeted"

        elif role == "byproduct":
            if action == "initial":
                event["narrative_type"] = "drawn"
            elif exerted == "0" and i > 0 and trajectory[i-1].get("exerted") == "1":
                event["narrative_type"] = "readied"
            elif zone == "discard":
                event["narrative_type"] = "banished"
                stats["final_state"] = "banished"
                stats["death_turn"] = turn
            elif zone is None:
                event["narrative_type"] = "removed"
            else:
                event["narrative_type"] = "changed"

        elif role == "observer":
            # Decision point check - only signal if it changed my edges
            if my_turn and action_type in ("play", "ink", "quest", "challenge"):
                can_key = f"can_{action_type}"
                actor = extract_actor(action)
                # Only show "passed over" if I lost an edge as a result
                if can_key in prev_edges and actor and card_id not in action and (gained or lost):
                    event["narrative_type"] = "passed_over"
                    event["chosen_card"] = actor
                    event["chosen_action"] = action_type
                else:
                    event["narrative_type"] = "observed"
            else:
                event["narrative_type"] = "observed"

        # Track edge changes as separate events if significant
        if gained and zone in ("hand", "play") and event.get("narrative_type") == "observed":
            event["narrative_type"] = "gained_ability"
        if lost and zone in ("hand", "play") and event.get("narrative_type") not in ("played", "quested", "inked", "challenged", "passed_over"):
            if event.get("narrative_type") == "observed":
                event["narrative_type"] = "lost_ability"

        events_by_turn[turn].append(event)
        prev_edges = edges
        prev_turn = turn
        prev_zone = zone
        prev_game = game

    # Count turns in each zone
    turns_seen = set()
    for turn, events in events_by_turn.items():
        for e in events:
            if e["zone"] == "hand":
                turns_seen.add(("hand", turn))
            elif e["zone"] == "play":
                turns_seen.add(("play", turn))

    stats["turns_in_hand"] = len([t for z, t in turns_seen if z == "hand"])
    stats["turns_in_play"] = len([t for z, t in turns_seen if z == "play"])

    # If card survived to end
    if stats["final_state"] == "unknown":
        last_event = trajectory[-1] if trajectory else {}
        if last_event.get("zone") == "play":
            stats["final_state"] = "survived"
        elif last_event.get("zone") == "hand":
            stats["final_state"] = "never_played"

    # Now generate prose
    lines = []
    lines.append(f"**{card_name}** — Narrative")
    lines.append("")

    sorted_turns = sorted(events_by_turn.keys())

    # Group consecutive quiet turns
    i = 0
    while i < len(sorted_turns):
        turn = sorted_turns[i]
        events = events_by_turn[turn]

        # Check if this turn has any significant events
        significant = [e for e in events if e.get("narrative_type") not in ("observed", None)]

        if not significant:
            # Find consecutive quiet turns
            quiet_start = turn
            quiet_end = turn
            j = i + 1
            while j < len(sorted_turns):
                next_turn = sorted_turns[j]
                next_events = events_by_turn[next_turn]
                next_significant = [e for e in next_events if e.get("narrative_type") not in ("observed", None)]
                if not next_significant:
                    quiet_end = next_turn
                    j += 1
                else:
                    break

            # Summarize quiet period
            zone = events[0].get("zone", "hand") if events else "hand"
            if quiet_start == quiet_end:
                lines.append(f"**Turn {quiet_start}:** I waited in {zone}.")
            else:
                lines.append(f"**Turns {quiet_start}-{quiet_end}:** I waited in {zone} while the game developed.")
            lines.append("")
            i = j
            continue

        # Process turn with significant events
        turn_lines = []
        turn_lines.append(f"**Turn {turn}:**")

        for event in events:
            narrative_type = event.get("narrative_type")

            if narrative_type == "drawn":
                turn_lines.append("I was drawn into hand.")

            elif narrative_type == "played":
                turn_lines.append("I was played onto the board.")

            elif narrative_type == "quested":
                lore_delta = event.get("lore_delta")
                if lore_delta:
                    prev_lore = event.get("prev_lore", 0)
                    curr_lore = event.get("curr_lore", 0)
                    turn_lines.append(f"I quested, becoming exerted. ({owner} lore: {prev_lore} → {curr_lore})")
                else:
                    turn_lines.append("I quested, becoming exerted.")

            elif narrative_type == "inked":
                turn_lines.append("I was inked, leaving the game permanently.")

            elif narrative_type == "challenged":
                target = event["action"].split("->")[1] if "->" in event["action"] else "an opponent"
                target_name = format_other_card(target)
                turn_lines.append(f"I challenged {target_name}.")

            elif narrative_type == "banished":
                actor = extract_actor(event["action"])
                if actor:
                    actor_name = format_other_card(actor)
                    turn_lines.append(f"I was challenged by {actor_name} and banished.")
                else:
                    turn_lines.append("I was banished.")

            elif narrative_type == "damaged":
                actor = extract_actor(event["action"])
                damage = event.get("damage", "?")
                if actor:
                    actor_name = format_other_card(actor)
                    turn_lines.append(f"I was challenged by {actor_name}, taking {damage} damage.")
                else:
                    turn_lines.append(f"I took {damage} damage.")

            elif narrative_type == "targeted":
                turn_lines.append(f"I was targeted by {event['action']}.")

            elif narrative_type == "readied":
                turn_lines.append("I readied at the start of the turn.")

            elif narrative_type == "passed_over":
                chosen = event.get("chosen_card", "another card")
                chosen_name = format_other_card(chosen)
                action = event.get("chosen_action", "use")
                remaining = [e for e in event.get("prev_edges", []) if e != f"can_{action}"]

                if remaining:
                    abilities = ", ".join(edge_to_noun(e) for e in remaining)
                    turn_lines.append(f"My owner chose to {action} {chosen_name} instead of me (I could still {abilities}).")
                else:
                    turn_lines.append(f"My owner chose to {action} {chosen_name} instead of me.")

            elif narrative_type == "gained_ability":
                gained = event.get("gained", [])
                if gained:
                    abilities = ", ".join(edge_to_noun(e) for e in gained)
                    turn_lines.append(f"I gained the ability to {abilities}.")

            elif narrative_type == "lost_ability":
                lost = event.get("lost", [])
                if lost:
                    abilities = ", ".join(edge_to_noun(e) for e in lost)
                    turn_lines.append(f"I lost my chance to {abilities}.")

            # Skip observed events with no significance
            elif narrative_type in ("observed", None):
                pass

        lines.append(" ".join(turn_lines))
        lines.append("")
        i += 1

    # Arc summary
    lines.append("---")
    lines.append("")
    lines.append("**Arc:**")

    arc_parts = []
    if stats["turns_in_hand"] > 0:
        arc_parts.append(f"Held in hand for {stats['turns_in_hand']} turn(s)")
    if stats["play_turn"]:
        arc_parts.append(f"Played on turn {stats['play_turn']}")
    if stats["turns_in_play"] > 0:
        arc_parts.append(f"{stats['turns_in_play']} turn(s) in play")
    if stats["quests"] > 0:
        arc_parts.append(f"{stats['quests']} quest(s)")
    if stats["challenges_made"] > 0:
        arc_parts.append(f"{stats['challenges_made']} challenge(s) made")
    if stats["challenges_received"] > 0:
        arc_parts.append(f"challenged {stats['challenges_received']} time(s)")
    if stats["damage_taken"] > 0:
        arc_parts.append(f"{stats['damage_taken']} damage taken")

    # Final state
    if stats["final_state"] == "banished":
        arc_parts.append(f"banished on turn {stats['death_turn']}")
    elif stats["final_state"] == "inked":
        arc_parts.append(f"inked on turn {stats['death_turn']}")
    elif stats["final_state"] == "survived":
        arc_parts.append("survived to end")
    elif stats["final_state"] == "never_played":
        arc_parts.append("never played")

    lines.append(" → ".join(arc_parts))

    # Game outcome
    if result:
        lines.append("")
        winner = result.get("winner", "?")
        final_lore = result.get("final_lore", {})
        p1_final = final_lore.get("p1", "?")
        p2_final = final_lore.get("p2", "?")

        outcome = "won" if winner == owner else "lost"
        lines.append(f"**Game Result:** We {outcome}. Final score: p1={p1_final}, p2={p2_final}. Winner: {winner}.")

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate narrative story from a card's trajectory"
    )
    parser.add_argument("episode_path", help="Path to the episode directory")
    parser.add_argument("card_id", help="Card ID (e.g., p1.mulan_free_spirit.b)")
    parser.add_argument(
        "--narrative", "-n",
        action="store_true",
        help="Output prose narrative instead of structured format"
    )

    args = parser.parse_args()
    episode_path = Path(args.episode_path)

    if not episode_path.exists():
        print(f"Error: {episode_path} does not exist")
        sys.exit(1)

    if args.narrative:
        story = generate_narrative(episode_path, args.card_id)
    else:
        story = generate_story(episode_path, args.card_id)

    print(story)


if __name__ == "__main__":
    main()
