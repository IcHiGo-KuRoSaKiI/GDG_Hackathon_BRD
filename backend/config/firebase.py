"""
Firebase Admin SDK initialization.
Provides AsyncClient for Firestore and Cloud Storage bucket access.
"""
import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.firestore_v1 import AsyncClient
from google.oauth2 import service_account
from .settings import settings
import os


# Get credentials path (resolve relative paths)
def get_credentials_path() -> str:
    """Get absolute path to service account credentials."""
    cred_path = settings.google_application_credentials

    # Handle relative paths
    if not os.path.isabs(cred_path):
        # Assume relative to project root (parent of backend/)
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_root = os.path.dirname(backend_dir)
        cred_path = os.path.join(project_root, cred_path)

    return cred_path


# Initialize Firebase Admin SDK
def initialize_firebase():
    """Initialize Firebase Admin SDK with service account credentials."""
    # Check if already initialized
    if not firebase_admin._apps:
        cred_path = get_credentials_path()

        # Initialize with service account
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {
            'storageBucket': settings.storage_bucket
        })


# Initialize Firebase
initialize_firebase()

# Create AsyncClient for Firestore with explicit credentials
# This is critical for FastAPI async compatibility
cred_path = get_credentials_path()
gcp_credentials = service_account.Credentials.from_service_account_file(cred_path)
firestore_client = AsyncClient(
    project=settings.google_cloud_project,
    credentials=gcp_credentials
)

# Create Cloud Storage bucket client
storage_bucket = storage.bucket()
