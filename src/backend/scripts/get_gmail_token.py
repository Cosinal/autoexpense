"""
Gmail OAuth Token Generator
Run this script once to authenticate and get a refresh token.

Usage:
    python get_gmail_token.py
"""

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Gmail API scopes - only need readonly access
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_credentials():
    """
    Authenticate with Gmail and get credentials.
    This will open a browser window for OAuth consent.
    """
    creds = None
    token_file = 'token.pickle'

    # Check if we already have saved credentials
    if os.path.exists(token_file):
        print("Found existing token file...")
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)

    # If credentials are invalid or don't exist, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired token...")
            creds.refresh(Request())
        else:
            print("\n" + "="*60)
            print("Gmail OAuth Authentication")
            print("="*60)
            print("\nThis will open a browser window for authentication.")
            print("Steps:")
            print("1. Sign in with your Gmail account")
            print("2. Click 'Allow' to grant AutoExpense access")
            print("3. You may see an 'unsafe' warning - this is normal")
            print("   Click 'Advanced' → 'Go to AutoExpense (unsafe)'")
            print("\n" + "="*60 + "\n")

            input("Press Enter to continue...")

            # Check for credentials.json
            if not os.path.exists('credentials.json'):
                print("\n❌ Error: credentials.json not found!")
                print("\nPlease download your OAuth credentials from Google Cloud Console:")
                print("1. Go to APIs & Services → Credentials")
                print("2. Download the OAuth 2.0 Client ID JSON")
                print("3. Save it as 'credentials.json' in the backend/ folder")
                return None

            # Run OAuth flow
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json',
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save credentials for future use
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)

    return creds

def main():
    """Main function to get and display credentials."""

    print("\nGmail API Token Generator for AutoExpense")
    print("=" * 60)

    creds = get_gmail_credentials()

    if creds:
        print("\n✓ Authentication successful!")
        print("=" * 60)
        print("\nYour refresh token:")
        print("-" * 60)
        print(creds.refresh_token)
        print("-" * 60)

        print("\nAdd this to your backend/.env file:")
        print("-" * 60)
        print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
        print("-" * 60)

        print("\n✓ Token saved to token.pickle")
        print("✓ You can now use the Gmail API")
        print("\nNext steps:")
        print("1. Copy the refresh token above")
        print("2. Add it to backend/.env")
        print("3. Test the email connection")

    else:
        print("\n✗ Authentication failed")
        print("Please check the error messages above")

if __name__ == "__main__":
    main()
