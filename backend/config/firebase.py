"""
Firebase Admin SDK initialization.
Provides AsyncClient for Firestore and Cloud Storage bucket access.
Supports both service account key file (local dev) and ADC (Cloud Run).
"""
import firebase_admin
from firebase_admin import credentials, firestore, storage
from google.cloud.firestore_v1 import AsyncClient
from .settings import settings
import os
import logging

logger = logging.getLogger(__name__)


def _get_credentials_path() -> str | None:
    """Get absolute path to service account credentials, or None if not configured."""
    cred_setting = settings.google_application_credentials
    if not cred_setting:
        return None

    cred_path = cred_setting

    # Handle relative paths
    if not os.path.isabs(cred_path):
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_root = os.path.dirname(backend_dir)
        cred_path = os.path.join(project_root, cred_path)

    if os.path.exists(cred_path):
        return cred_path

    logger.warning(f"Credentials file not found at {cred_path}, falling back to ADC")
    return None


def initialize_firebase():
    """Initialize Firebase Admin SDK. Uses key file if available, else ADC."""
    if firebase_admin._apps:
        return

    cred_path = _get_credentials_path()

    if cred_path:
        logger.info("Initializing Firebase with service account key file")
        cred = credentials.Certificate(cred_path)
    else:
        logger.info("Initializing Firebase with Application Default Credentials (ADC)")
        cred = credentials.ApplicationDefault()

    firebase_admin.initialize_app(cred, {
        'storageBucket': settings.storage_bucket
    })


# Initialize Firebase
initialize_firebase()

# Create AsyncClient for Firestore
cred_path = _get_credentials_path()
if cred_path:
    from google.oauth2 import service_account
    gcp_credentials = service_account.Credentials.from_service_account_file(cred_path)
    firestore_client = AsyncClient(
        project=settings.google_cloud_project,
        credentials=gcp_credentials
    )
else:
    # ADC: Cloud Run service account provides credentials automatically
    firestore_client = AsyncClient(project=settings.google_cloud_project)

# Create Cloud Storage bucket client
storage_bucket = storage.bucket()
