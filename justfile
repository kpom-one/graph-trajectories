# Dotcana - Lorcana game state engine

set shell := ["bash", "-uc"]

# Use venv python
python := ".venv/bin/python"

# Show available commands
default:
    @just --list

# Set up development environment
setup:
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install networkx pydot flask pytest
    @echo "Environment ready. Dependencies installed."

# Run tests
test *args:
    {{python}} -m pytest tests/ {{args}}

# Clear all output
clear:
    rm -rf output/
    @echo "Cleared output/"

# Generate random games
# Usage: just generate-games 5 10              (5 seeds, 10 games each, memory-only)
#        just generate-games 5 10 --output-tree (also writes game tree to disk)
generate-games num_seeds="1" games_per_seed="1" *flags="":
    #!/usr/bin/env bash
    set -euo pipefail

    # Create matchup (uses debug decks by default)
    hash=$({{python}} bin/rules-engine.py init "data/decks/debug-gp.txt" "data/decks/debug-ys.txt")
    echo "Matchup: ${hash}"

    # Generate random seeds and play games
    for i in $(seq 1 {{num_seeds}}); do
        # Generate random seed (no dots = true random shuffle)
        seed=$({{python}} -c "import random, string; print(''.join(random.choices(string.ascii_lowercase + string.digits, k=8)))")

        echo "Seed $i: ${seed}"
        {{python}} bin/rules-engine.py shuffle "output/tree/${hash}" "${seed}" > /dev/null

        # Play games for this seed
        {{python}} bin/play-random.py "output/tree/${hash}/${seed}" {{games_per_seed}} {{flags}}
    done

    echo ""
    echo "Done. Generated {{num_seeds}} seeds with {{games_per_seed}} games each."
    echo "Episodes: $(ls -1d output/episodes/*.episode 2>/dev/null | wc -l)"
    du -sh output/ 2>/dev/null || true

# Extract per-card trajectory files from an episode
# Usage: just build-trajectories output/episodes/abc.episode
build-trajectories episode_path:
    {{python}} bin/build-trajectories.py "{{episode_path}}"

# Build narrative files for all cards across episodes
# Usage: just build-narratives                     (all episodes)
#        just build-narratives output/episodes/abc.episode  (single episode)
build-narratives *episode_path:
    {{python}} bin/build-narratives.py {{episode_path}}
