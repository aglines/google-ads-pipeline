#!/bin/bash
set -e

echo "Stopping services..."
docker compose down

echo ""
echo "Rebuilding Docker image (no cache)..."
docker compose build --no-cache

echo ""
echo "Starting services..."
docker compose up -d

echo ""
echo "Rebuild complete!"
docker compose ps

echo ""
echo "Access Airflow UI at: http://localhost:8080"
