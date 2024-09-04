#!/bin/bash
#cpu_units=$(getconf _NPROCESSORS_ONLN)
#workers_to_spawn=$((cpu_units * 2 + 1))
workers_to_spawn=1
echo "Starting service with ${workers_to_spawn} workers"
gunicorn --log-level debug --timeout 300 --bind 0.0.0.0:3000 --worker-class=uvicorn.workers.UvicornWorker --workers=$workers_to_spawn app:app
