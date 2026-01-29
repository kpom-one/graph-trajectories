#!/usr/bin/env python3
"""
Build narrative files for all cards across episodes.

Generates narrative stories for each card and organizes them by card type.

Usage:
    python bin/build-narratives.py                    # Process all episodes
    python bin/build-narratives.py <episode_path>    # Process single episode
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Import from sibling scripts
from importlib.util import spec_from_file_location, module_from_spec


def load_module(name: str, path: Path):
    """Load a Python module from a file path."""
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Load sibling modules
build_trajectories_mod = load_module(
    "build_trajectories",
    Path(__file__).parent / "build-trajectories.py"
)
trajectory_story_mod = load_module(
    "trajectory_story",
    Path(__file__).parent / "trajectory-story.py"
)

build_trajectories = build_trajectories_mod.build_trajectories
generate_narrative = trajectory_story_mod.generate_narrative


def extract_card_label(card_id: str) -> str:
    """Extract card label from card_id: p2.mulan_free_spirit.b -> mulan_free_spirit"""
    parts = card_id.split(".")
    if len(parts) >= 2:
        return parts[1]
    return card_id


def extract_instance_parts(card_id: str) -> tuple[str, str]:
    """Extract player and instance from card_id: p2.mulan_free_spirit.b -> (p2, b)"""
    parts = card_id.split(".")
    if len(parts) >= 3:
        return parts[0], parts[2]
    elif len(parts) == 2:
        return parts[0], "a"
    return "p1", "a"


def get_episode_id(episode_path: Path) -> str:
    """Extract episode ID from path: output/episodes/0xuebtpz-1.episode -> 0xuebtpz-1"""
    name = episode_path.name
    if name.endswith(".episode"):
        return name[:-8]
    return name


def get_card_trajectories(episode_path: Path) -> list[str]:
    """Get list of card IDs that have trajectory files."""
    traj_dir = episode_path / "trajectories"
    if not traj_dir.exists():
        return []

    card_ids = []
    for f in traj_dir.glob("*.jsonl"):
        if f.name != "game.jsonl":
            card_ids.append(f.stem)

    return sorted(card_ids)


def ensure_trajectories(episode_path: Path) -> bool:
    """Ensure trajectories exist for episode, building if needed."""
    traj_dir = episode_path / "trajectories"
    game_jsonl = traj_dir / "game.jsonl"

    if game_jsonl.exists():
        return True

    print(f"  Building trajectories for {episode_path.name}...")
    try:
        build_trajectories(episode_path)
        return True
    except Exception as e:
        print(f"  Error building trajectories: {e}")
        return False


def process_episode(episode_path: Path, output_base: Path) -> int:
    """Process a single episode, generating narratives for all cards.

    Returns number of narratives generated.
    """
    episode_id = get_episode_id(episode_path)

    # Ensure trajectories exist
    if not ensure_trajectories(episode_path):
        return 0

    # Get all card trajectories
    card_ids = get_card_trajectories(episode_path)
    if not card_ids:
        print(f"  No card trajectories found in {episode_path.name}")
        return 0

    count = 0
    for card_id in card_ids:
        try:
            # Generate narrative
            narrative = generate_narrative(episode_path, card_id)

            # Determine output path
            card_label = extract_card_label(card_id)
            player, instance = extract_instance_parts(card_id)

            output_dir = output_base / card_label
            output_dir.mkdir(parents=True, exist_ok=True)

            output_file = output_dir / f"{episode_id}.{player}.{instance}.txt"
            output_file.write_text(narrative)

            count += 1
        except Exception as e:
            print(f"  Error processing {card_id}: {e}")

    return count


def find_all_episodes(base_path: Path = None) -> list[Path]:
    """Find all episode directories."""
    if base_path is None:
        base_path = Path("output/episodes")

    if not base_path.exists():
        return []

    return sorted(base_path.glob("*.episode"))


def main():
    output_base = Path("output/narratives")

    if len(sys.argv) >= 2:
        # Process single episode
        episode_path = Path(sys.argv[1])
        if not episode_path.exists():
            print(f"Error: {episode_path} does not exist")
            sys.exit(1)

        episodes = [episode_path]
    else:
        # Process all episodes
        episodes = find_all_episodes()
        if not episodes:
            print("No episodes found in output/episodes/")
            sys.exit(1)

    total_narratives = 0

    for episode_path in episodes:
        print(f"Processing {episode_path.name}...")
        count = process_episode(episode_path, output_base)
        total_narratives += count
        print(f"  Generated {count} narratives")

    print(f"\nTotal: {total_narratives} narratives in {output_base}/")


if __name__ == "__main__":
    main()
