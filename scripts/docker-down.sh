#!/bin/bash
set -e

echo "Stopping Docker Compose services..."
docker compose down

echo ""
echo "Services stopped!"
echo "To remove volumes as well: docker compose down -v"
