"""
FastAPI authentication dependency.
Extracts and validates Firebase token from Authorization header.
"""
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

from ..models import User
from ..services.auth_service import auth_service

logger = logging.getLogger(__name__)

# Security scheme for Bearer token
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> User:
    """
    Dependency to get current authenticated user.

    Extracts token from Authorization: Bearer <token> header,
    verifies with Firebase, and returns user.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        Authenticated User model

    Raises:
        HTTPException 401: If authentication fails

    Usage:
        @router.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.user_id}
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication token"
        )

    try:
        # Verify token and get user
        user = await auth_service.verify_token(credentials.credentials)
        return user

    except Exception as e:
        logger.warning(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=401,
            detail=str(e)
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Optional[User]:
    """
    Optional authentication - returns user if token provided, None otherwise.

    Use for routes that work both authenticated and unauthenticated.

    Args:
        credentials: HTTP Bearer credentials (optional)

    Returns:
        User model if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        user = await auth_service.verify_token(credentials.credentials)
        return user
    except Exception as e:
        logger.warning(f"Optional auth failed: {e}")
        return None
