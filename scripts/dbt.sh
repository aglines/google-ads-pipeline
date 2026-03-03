#!/bin/bash
# dbt wrapper - runs dbt with correct directories from project root
# Usage: ./scripts/dbt.sh run
#        ./scripts/dbt.sh test
#        ./scripts/dbt.sh compile

set -e

# Get project root (parent of scripts/)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Change to project root
cd "$PROJECT_ROOT"

# Load .env file if it exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# Run dbt with correct paths
uv run dbt "$@" --project-dir dbt_project --profiles-dir dbt_project
