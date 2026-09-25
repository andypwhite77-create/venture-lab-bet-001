#!/usr/bin/env bash
set -euo pipefail

cd /home/deploy/venture-lab

git fetch origin main
git reset --hard origin/main

docker compose up -d --build --remove-orphans

docker compose ps
