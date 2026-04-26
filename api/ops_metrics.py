"""Lightweight in-process operational metrics."""

import threading
import time
from typing import Dict

_lock = threading.Lock()
_started_at = time.time()
_counters = {
    'planning_jobs_started': 0,
    'planning_jobs_success': 0,
    'planning_jobs_error': 0,
    'planning_jobs_cancelled': 0,
    'planning_jobs_cleaned_up': 0,
}


def increment(counter: str, value: int = 1) -> None:
    with _lock:
        _counters[counter] = _counters.get(counter, 0) + value


def snapshot() -> Dict[str, int]:
    with _lock:
        data = dict(_counters)
    data['uptime_seconds'] = int(time.time() - _started_at)
    return data
