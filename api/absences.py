"""
Absences API: composed routers for absences, absence types, vacation requests, and vacation year data.

Implementation is split across ``absences_*_routes.py`` modules.
"""

from fastapi import APIRouter

from .absences_records_routes import router as absences_records_router
from .absences_types_routes import router as absences_types_router
from .absences_vacation_requests_routes import router as absences_vacation_requests_router
from .absences_year_approvals_routes import router as absences_year_approvals_router
from .absences_year_plan_routes import router as absences_year_plan_router

router = APIRouter()
router.include_router(absences_records_router)
router.include_router(absences_types_router)
router.include_router(absences_vacation_requests_router)
router.include_router(absences_year_approvals_router)
router.include_router(absences_year_plan_router)
