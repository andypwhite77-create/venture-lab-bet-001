#!/usr/bin/env bash
set -euo pipefail

cd /home/deploy/venture-lab

docker compose up -d --build --remove-orphans

docker compose ps
