"""
Authentication service using Firebase Auth.
Handles user registration, login, and token verification.
"""
import logging
from datetime import datetime
from typing import Optional
from firebase_admin import auth
from ..models import User, UserCreate, UserLogin, UserResponse, AuthToken
from .firestore_service import firestore_service

logger = logging.getLogger(__name__)


class AuthService:
    """Service for user authentication using Firebase Auth."""

    def __init__(self):
        """Initialize auth service."""
        self.firestore = firestore_service

    async def register_user(self, user_data: UserCreate) -> AuthToken:
        """
        Register a new user with Firebase Auth.

        Args:
            user_data: User registration data

        Returns:
            AuthToken with user info and Firebase ID token

        Raises:
            Exception: If registration fails (email already exists, etc.)
        """
        try:
            # Create user in Firebase Auth
            firebase_user = auth.create_user(
                email=user_data.email,
                password=user_data.password,
                display_name=user_data.display_name
            )

            # Create custom token for immediate login
            custom_token = auth.create_custom_token(firebase_user.uid)

            # Create user record in Firestore
            now = datetime.utcnow()
            user = User(
                user_id=firebase_user.uid,
                email=user_data.email,
                display_name=user_data.display_name,
                created_at=now,
                last_login=now,
                project_count=0
            )

            # Store in Firestore
            user_ref = self.firestore.client.collection('users').document(firebase_user.uid)
            await user_ref.set(user.model_dump(mode='json'))

            logger.info(f"User registered: {firebase_user.uid}")

            # Return token and user info
            return AuthToken(
                token=custom_token.decode('utf-8'),
                user=UserResponse(
                    user_id=user.user_id,
                    email=user.email,
                    display_name=user.display_name,
                    created_at=user.created_at,
                    project_count=user.project_count
                )
            )

        except auth.EmailAlreadyExistsError:
            raise Exception("Email already registered")
        except Exception as e:
            logger.error(f"User registration failed: {e}", exc_info=True)
            raise Exception(f"Registration failed: {str(e)}")

    async def verify_token(self, id_token: str) -> User:
        """
        Verify Firebase ID token and return user.

        Args:
            id_token: Firebase ID token from client

        Returns:
            User model

        Raises:
            Exception: If token is invalid or expired
        """
        try:
            # Verify token with Firebase
            decoded_token = auth.verify_id_token(id_token)
            user_id = decoded_token['uid']

            # Get user from Firestore
            user = await self.get_user(user_id)

            if not user:
                raise Exception("User not found")

            # Update last login
            await self.update_last_login(user_id)

            return user

        except auth.InvalidIdTokenError:
            raise Exception("Invalid authentication token")
        except auth.ExpiredIdTokenError:
            raise Exception("Authentication token expired")
        except Exception as e:
            logger.error(f"Token verification failed: {e}", exc_info=True)
            raise Exception(f"Authentication failed: {str(e)}")

    async def get_user(self, user_id: str) -> Optional[User]:
        """
        Get user by ID from Firestore.

        Args:
            user_id: Firebase user ID

        Returns:
            User model or None if not found
        """
        user_ref = self.firestore.client.collection('users').document(user_id)
        doc = await user_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        # Convert ISO strings back to datetime
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('last_login'):
            data['last_login'] = datetime.fromisoformat(data['last_login'])

        return User(**data)

    async def update_last_login(self, user_id: str) -> None:
        """
        Update user's last login timestamp.

        Args:
            user_id: Firebase user ID
        """
        user_ref = self.firestore.client.collection('users').document(user_id)
        await user_ref.update({
            'last_login': datetime.utcnow().isoformat()
        })

    async def increment_project_count(self, user_id: str) -> None:
        """
        Increment user's project count.

        Args:
            user_id: Firebase user ID
        """
        user_ref = self.firestore.client.collection('users').document(user_id)
        await user_ref.update({
            'project_count': self.firestore.client.field('project_count').increment(1)
        })


# Global service instance
auth_service = AuthService()
