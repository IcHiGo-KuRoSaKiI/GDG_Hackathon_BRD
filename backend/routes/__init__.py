"""
Routes module exports.
Provides all API routers.
"""
from .projects import router as projects_router
from .documents import router as documents_router
from .brds import router as brds_router

__all__ = [
    "projects_router",
    "documents_router",
    "brds_router"
]
