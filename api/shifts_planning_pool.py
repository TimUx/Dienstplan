"""
Process pool and worker budget for asynchronous shift planning jobs.

Imported by planning routes and planning core so a single executor is shared.
"""

import logging
import threading
from concurrent.futures import ProcessPoolExecutor

from .planning_runtime import load_planning_runtime_config

logger = logging.getLogger(__name__)

_runtime_cfg = load_planning_runtime_config()
MAX_CONCURRENT_JOBS = _runtime_cfg.max_concurrent_jobs
SOLVER_WORKERS_PER_JOB = _runtime_cfg.solver_workers_per_job

_solver_pool = ProcessPoolExecutor(max_workers=MAX_CONCURRENT_JOBS)
_active_futures: dict = {}
_futures_lock = threading.Lock()

logger.info(
    "Planning worker budget configured: cpu=%s, max_jobs=%s, solver_workers_per_job=%s",
    _runtime_cfg.cpu_count,
    MAX_CONCURRENT_JOBS,
    SOLVER_WORKERS_PER_JOB,
)
