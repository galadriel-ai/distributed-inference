from prometheus_client import multiprocess


# needed for prometheus multiprocessing metrics when gunicorn is used
# https://github.com/prometheus/client_python#multiprocess-mode-eg-gunicorn
def child_exit(server, worker):
    multiprocess.mark_process_dead(worker.pid)
