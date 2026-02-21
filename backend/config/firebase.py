"""
Firebase Admin SDK initialization.
Provides AsyncClient for Firestore and Cloud Storage bucket access.
"""
import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.firestore_v1 import AsyncClient
from .settings import settings
import os


# Initialize Firebase Admin SDK
def initialize_firebase():
    """Initialize Firebase Admin SDK with service account credentials."""
    # Check if already initialized
    if not firebase_admin._apps:
        # Get credentials path from settings
        cred_path = settings.google_application_credentials

        # Handle relative paths
        if not os.path.isabs(cred_path):
            # Assume relative to backend directory
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cred_path = os.path.join(backend_dir, cred_path)

        # Initialize with service account
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {
            'storageBucket': settings.storage_bucket
        })


# Initialize Firebase
initialize_firebase()

# Create AsyncClient for Firestore (critical for FastAPI async)
firestore_client = AsyncClient(project=settings.google_cloud_project)

# Create Cloud Storage bucket client
storage_bucket = storage.bucket()
