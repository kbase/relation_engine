# Gunicorn configuration file.
import os
import multiprocessing
from src.relation_engine_server.utils import pull_spec

# server
bind = ':5000'

# workers
worker_class = 'gevent'
timeout = 1800
# See: http://docs.gunicorn.org/en/stable/design.html#how-many-workers
if os.environ.get("WORKERS"):
    workers = int(os.environ["WORKERS"])
else:
    workers = multiprocessing.cpu_count() * 2 + 1

if os.environ.get("DEVELOPMENT"):
    reload = True


def on_starting(server):
    print("Pulling specs")
    pull_spec.download_latest(init_collections=False)
