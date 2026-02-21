"""
Authentication service using JWT tokens.
Handles user registration, login, and token verification.
NO Firebase Auth required - just Firestore + JWT!
"""
import logging
import bcrypt
import jwt
from datetime import datetime, timedelta
from typing import Optional
from google.cloud.firestore import Increment
from ..models import User, UserCreate, UserLogin, UserResponse, AuthToken
from ..config import settings
from .firestore_service import firestore_service
from ..utils import generate_project_id

logger = logging.getLogger(__name__)


class AuthService:
    """Service for JWT-based authentication."""

    def __init__(self):
        """Initialize auth service."""
        self.firestore = firestore_service
        self.jwt_secret = settings.jwt_secret_key
        self.jwt_algorithm = settings.jwt_algorithm
        self.jwt_expiration_hours = settings.jwt_expiration_hours

    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    def _generate_jwt(self, user_id: str, email: str) -> str:
        """Generate JWT token for user."""
        payload = {
            'user_id': user_id,
            'email': email,
            'exp': datetime.utcnow() + timedelta(hours=self.jwt_expiration_hours),
            'iat': datetime.utcnow()
        }
        token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        return token

    async def register_user(self, user_data: UserCreate) -> AuthToken:
        """
        Register a new user.

        Args:
            user_data: User registration data

        Returns:
            AuthToken with JWT and user info

        Raises:
            Exception: If registration fails (email already exists, etc.)
        """
        try:
            # Check if email already exists
            existing = await self._get_user_by_email(user_data.email)
            if existing:
                raise Exception("Email already registered")

            # Generate user ID
            user_id = f"user_{generate_project_id().split('_')[1]}"

            # Hash password
            password_hash = self._hash_password(user_data.password)

            # Create user record
            now = datetime.utcnow()
            user = User(
                user_id=user_id,
                email=user_data.email,
                display_name=user_data.display_name,
                created_at=now,
                last_login=now,
                project_count=0
            )

            # Store in Firestore (with password hash)
            user_ref = self.firestore.client.collection('users').document(user_id)
            user_dict = user.model_dump(mode='json')
            user_dict['password_hash'] = password_hash  # Store hash
            await user_ref.set(user_dict)

            # Generate JWT token
            token = self._generate_jwt(user_id, user_data.email)

            logger.info(f"User registered: {user_id}")

            # Return token and user info
            return AuthToken(
                token=token,
                user=UserResponse(
                    user_id=user.user_id,
                    email=user.email,
                    display_name=user.display_name,
                    created_at=user.created_at,
                    project_count=user.project_count
                ),
                expires_in=self.jwt_expiration_hours * 3600
            )

        except Exception as e:
            logger.error(f"User registration failed: {e}", exc_info=True)
            raise Exception(f"Registration failed: {str(e)}")

    async def login_user(self, login_data: UserLogin) -> AuthToken:
        """
        Login user with email and password.

        Args:
            login_data: Login credentials

        Returns:
            AuthToken with JWT and user info

        Raises:
            Exception: If login fails
        """
        try:
            # Get user by email
            user_ref = self.firestore.client.collection('users')
            query = user_ref.where('email', '==', login_data.email).limit(1)

            docs = []
            async for doc in query.stream():
                docs.append(doc)

            if not docs:
                raise Exception("Invalid email or password")

            user_doc = docs[0]
            user_data = user_doc.to_dict()

            # Verify password
            password_hash = user_data.get('password_hash')
            if not password_hash or not self._verify_password(login_data.password, password_hash):
                raise Exception("Invalid email or password")

            # Convert to User model
            user_data['created_at'] = datetime.fromisoformat(user_data['created_at'])
            if user_data.get('last_login'):
                user_data['last_login'] = datetime.fromisoformat(user_data['last_login'])

            # Remove password_hash from model
            user_data.pop('password_hash', None)
            user = User(**user_data)

            # Update last login
            await self.update_last_login(user.user_id)

            # Generate JWT token
            token = self._generate_jwt(user.user_id, user.email)

            logger.info(f"User logged in: {user.user_id}")

            return AuthToken(
                token=token,
                user=UserResponse(
                    user_id=user.user_id,
                    email=user.email,
                    display_name=user.display_name,
                    created_at=user.created_at,
                    project_count=user.project_count
                ),
                expires_in=self.jwt_expiration_hours * 3600
            )

        except Exception as e:
            logger.error(f"Login failed: {e}", exc_info=True)
            raise Exception(f"Login failed: {str(e)}")

    async def verify_token(self, token: str) -> User:
        """
        Verify JWT token and return user.

        Args:
            token: JWT token

        Returns:
            User model

        Raises:
            Exception: If token is invalid or expired
        """
        try:
            # Decode JWT
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            user_id = payload.get('user_id')

            if not user_id:
                raise Exception("Invalid token payload")

            # Get user from Firestore
            user = await self.get_user(user_id)

            if not user:
                raise Exception("User not found")

            return user

        except jwt.ExpiredSignatureError:
            raise Exception("Token expired")
        except jwt.InvalidTokenError as e:
            raise Exception(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Token verification failed: {e}", exc_info=True)
            raise Exception(f"Authentication failed: {str(e)}")

    async def get_user(self, user_id: str) -> Optional[User]:
        """
        Get user by ID from Firestore.

        Args:
            user_id: User ID

        Returns:
            User model or None if not found
        """
        user_ref = self.firestore.client.collection('users').document(user_id)
        doc = await user_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        # Remove password hash
        data.pop('password_hash', None)

        # Convert ISO strings back to datetime
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('last_login'):
            data['last_login'] = datetime.fromisoformat(data['last_login'])

        return User(**data)

    async def _get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        query = self.firestore.client.collection('users').where('email', '==', email).limit(1)

        async for doc in query.stream():
            data = doc.to_dict()
            data.pop('password_hash', None)
            data['created_at'] = datetime.fromisoformat(data['created_at'])
            if data.get('last_login'):
                data['last_login'] = datetime.fromisoformat(data['last_login'])
            return User(**data)

        return None

    async def update_last_login(self, user_id: str) -> None:
        """
        Update user's last login timestamp.

        Args:
            user_id: User ID
        """
        user_ref = self.firestore.client.collection('users').document(user_id)
        await user_ref.update({
            'last_login': datetime.utcnow().isoformat()
        })

    async def increment_project_count(self, user_id: str) -> None:
        """
        Increment user's project count.

        Args:
            user_id: User ID
        """
        user_ref = self.firestore.client.collection('users').document(user_id)
        await user_ref.update({
            'project_count': Increment(1)
        })


# Global service instance
auth_service = AuthService()
