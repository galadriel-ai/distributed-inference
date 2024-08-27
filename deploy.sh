#!/usr/bin/env bash

mkdir -p shared/nginx

docker compose up --build --remove-orphans -d

docker image prune -f
docker container prune -f
docker volume prune -f
docker network prune -f