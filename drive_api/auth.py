"""
Authentication for the Google Drive API.

Service Account (preferred, per Sprint 4 direction) is the default. OAuth
user-credential flow is supported as a fallback for environments where a
service account cannot be shared onto the target Drive (e.g. a personal
My Drive rather than a Shared Drive), since a service account only sees
folders explicitly shared with its email address.
"""

import os
import sys

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def build_drive_service(credentials_path: str = "credentials.json"):
    """Build an authenticated Drive API v3 service using a Service Account key.

    Raises FileNotFoundError with a clear message rather than failing deep
    inside googleapiclient if the key is missing — this is the #1 setup
    mistake (see INSTALL.md / README troubleshooting sections).
    """
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    if not os.path.exists(credentials_path):
        raise FileNotFoundError(
            f"Service Account key not found at '{credentials_path}'. "
            "Download it from Google Cloud Console (IAM & Admin > Service "
            "Accounts > Keys) and place it at the project root, then share "
            "the target Drive folders with the service account's email "
            "address (Viewer access is enough for scanning)."
        )
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def build_drive_service_oauth(client_secrets_path: str = "oauth_client.json",
                               token_path: str = "oauth_token.json"):
    """Fallback OAuth user-credential flow (only needed if a Service Account
    cannot be granted access to the target Drive, e.g. a personal My Drive).
    Not used by default — `inventory.py` uses the Service Account flow above.
    """
    from google.oauth2.credentials import Credentials as UserCredentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(token_path):
        creds = UserCredentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(client_secrets_path):
                print(f"❌ OAuth client secrets not found at: {client_secrets_path}", file=sys.stderr)
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return build("drive", "v3", credentials=creds)
