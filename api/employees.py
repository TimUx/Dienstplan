"""
Employees API: composed routers for employees, teams, vacation periods, rotation groups, and CSV I/O.

Implementation is split across ``employees_*_routes.py`` modules.
"""

from fastapi import APIRouter

from .employees_crud_routes import router as employees_crud_router
from .employees_import_export_routes import router as employees_import_export_router
from .employees_rotation_groups_routes import router as employees_rotation_groups_router
from .employees_teams_routes import router as employees_teams_router
from .employees_vacation_periods_routes import router as employees_vacation_periods_router

router = APIRouter()
router.include_router(employees_crud_router)
router.include_router(employees_teams_router)
router.include_router(employees_vacation_periods_router)
router.include_router(employees_rotation_groups_router)
router.include_router(employees_import_export_router)
