#!/bin/bash
set -e

echo "Building Docker image..."
docker build -t google-ads-pipeline:latest .

echo ""
echo "Build complete!"
echo "To start the services, run: ./scripts/docker-up.sh"
