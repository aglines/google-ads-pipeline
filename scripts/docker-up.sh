#!/bin/bash
set -e

echo "Starting Docker Compose services..."
docker compose up -d

echo ""
echo "Services started!"
echo "Waiting for Airflow to be healthy..."
sleep 10

echo ""
docker compose ps

echo ""
echo "Access Airflow UI at: http://localhost:8080"
echo "To view logs: docker compose logs -f airflow"
echo "To stop services: ./scripts/docker-down.sh"
