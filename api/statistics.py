"""
Statistics APIRouter: dashboard stats, audit logs, notifications.

Implementation is split across ``statistics_*`` modules; this file only
composes the public ``router`` object (unchanged import path for the app).
"""

from fastapi import APIRouter

from .statistics_audit_routes import router as audit_router
from .statistics_dashboard_routes import router as dashboard_router
from .statistics_notifications_routes import router as notifications_router

router = APIRouter()
router.include_router(dashboard_router)
router.include_router(audit_router)
router.include_router(notifications_router)
