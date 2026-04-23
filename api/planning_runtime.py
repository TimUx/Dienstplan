"""Runtime configuration for asynchronous planning jobs."""

import os
from dataclasses import dataclass


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class PlanningRuntimeConfig:
    cpu_count: int
    max_concurrent_jobs: int
    solver_workers_per_job: int


def load_planning_runtime_config() -> PlanningRuntimeConfig:
    """Load CPU-safe planning runtime settings from environment."""
    cpu_count = os.cpu_count() or 1
    max_concurrent_jobs = max(
        1,
        _env_int("DIENSTPLAN_MAX_CONCURRENT_JOBS", min(4, cpu_count)),
    )
    solver_workers_per_job = max(
        1,
        _env_int(
            "DIENSTPLAN_SOLVER_WORKERS_PER_JOB",
            max(1, cpu_count // max_concurrent_jobs),
        ),
    )
    return PlanningRuntimeConfig(
        cpu_count=cpu_count,
        max_concurrent_jobs=max_concurrent_jobs,
        solver_workers_per_job=solver_workers_per_job,
    )
