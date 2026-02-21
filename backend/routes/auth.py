"""
Authentication API routes.
Handles user registration and token verification.
"""
from fastapi import APIRouter, HTTPException, Depends
import logging

from ..models import UserCreate, UserLogin, AuthToken, User
from ..services.auth_service import auth_service
from ..utils.auth_dependency import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=AuthToken, status_code=201)
async def register(user_data: UserCreate):
    """
    Register a new user.

    Creates user in Firebase Auth and Firestore.
    Returns authentication token for immediate login.

    Args:
        user_data: User registration data (email, password, display_name)

    Returns:
        AuthToken with Firebase custom token and user info

    Raises:
        400: If email already exists or validation fails
    """
    try:
        token = await auth_service.register_user(user_data)
        logger.info(f"User registered: {token.user.email}")
        return token

    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


@router.get("/me", response_model=User)
async def get_current_user_info(user: User = Depends(get_current_user)):
    """
    Get current authenticated user's information.

    Requires: Authorization header with valid Firebase ID token

    Args:
        user: Current authenticated user (from dependency)

    Returns:
        User information

    Example:
        GET /auth/me
        Authorization: Bearer <firebase-id-token>
    """
    return user


@router.post("/verify")
async def verify_token(user: User = Depends(get_current_user)):
    """
    Verify authentication token.

    Use this endpoint to check if a token is still valid.

    Args:
        user: Current authenticated user (from dependency)

    Returns:
        Success message with user_id

    Raises:
        401: If token is invalid or expired
    """
    return {
        "valid": True,
        "user_id": user.user_id,
        "email": user.email
    }
