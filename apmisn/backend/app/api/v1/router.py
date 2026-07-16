"""
Aggregates all v1 endpoint routers into a single APIRouter mounted by main.py.
Adding a new resource = add its router here, nothing else.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, health, identity, permissions, roles, sessions, users

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(roles.router, prefix="/roles", tags=["Roles"])
api_router.include_router(permissions.router, prefix="/permissions", tags=["Permissions"])
api_router.include_router(identity.router, prefix="/identity", tags=["Identity"])
