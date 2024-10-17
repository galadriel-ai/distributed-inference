#!/usr/bin/env bash

mkdir -p shared/nginx

# needed for prometheus multiprocessing metrics when gunicorn is used
# https://github.com/prometheus/client_python#multiprocess-mode-eg-gunicorn
rm -rf prometheus
mkdir prometheus

docker compose up --build --remove-orphans -d

docker image prune -f
docker container prune -f
docker volume prune -f
docker network prune -f