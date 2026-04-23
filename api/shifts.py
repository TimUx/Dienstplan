"""
Shifts API: composed routers for shift types, schedule, planning, assignments, exports, and exchanges.

Submodules live in ``api/shift_types_routes.py`` and ``api/shifts_*_routes.py``; this file only aggregates them.
Importing ``shifts_planning_pool`` initialises the shared process pool once at application startup.
"""

from fastapi import APIRouter

from . import shifts_planning_pool  # noqa: F401
from .shift_types_routes import router as shift_types_router
from .shifts_assignments_routes import router as shifts_assignments_router
from .shifts_exchange_routes import router as shifts_exchange_router
from .shifts_export_routes import router as shifts_export_router
from .shifts_planning_routes import router as shifts_planning_router
from .shifts_schedule_routes import router as shifts_schedule_router

router = APIRouter()
router.include_router(shift_types_router)
router.include_router(shifts_schedule_router)
router.include_router(shifts_planning_router)
router.include_router(shifts_assignments_router)
router.include_router(shifts_export_router)
router.include_router(shifts_exchange_router)
