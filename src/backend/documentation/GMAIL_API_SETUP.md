# Gmail API Setup Guide

Follow these steps to enable Gmail API and get OAuth credentials for AutoExpense.

---

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a project** → **New Project**
3. Project name: `AutoExpense` (or your preference)
4. Click **Create**
5. Wait for the project to be created, then select it

---

## Step 2: Enable Gmail API

1. In your Google Cloud Console, go to **APIs & Services** → **Library**
2. Search for "Gmail API"
3. Click on **Gmail API**
4. Click **Enable**
5. Wait for it to enable (~30 seconds)

---

## Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Choose **External** (unless you have a Google Workspace account)
3. Click **Create**

### App Information:
- **App name**: `AutoExpense`
- **User support email**: Your email
- **Developer contact email**: Your email
- Leave other fields as default
- Click **Save and Continue**

### Scopes:
- Click **Add or Remove Scopes**
- Search for `gmail.readonly`
- Check the box for: `https://www.googleapis.com/auth/gmail.readonly`
- Click **Update**
- Click **Save and Continue**

### Test Users:
- Click **Add Users**
- Add your new Gmail account email address
- Click **Add**
- Click **Save and Continue**

### Summary:
- Review and click **Back to Dashboard**

---

## Step 4: Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Application type: **Desktop app**
4. Name: `AutoExpense Desktop Client`
5. Click **Create**

### Download Credentials:
- A popup will show your Client ID and Client Secret
- Click **Download JSON**
- Save this file as `credentials.json` in your `backend/` folder
- **Or** copy the Client ID and Client Secret - we'll add them to `.env`

---

## Step 5: Get Refresh Token

We need to authenticate once to get a refresh token. Run this Python script:

```bash
cd backend
source venv/bin/activate
python get_gmail_token.py
```

(I'll create this script for you in a moment)

This will:
1. Open a browser window
2. Ask you to sign in with your Gmail account
3. Grant permissions to AutoExpense
4. Save a refresh token

---

## Step 6: Update .env File

Add these values to `backend/.env`:

```bash
# Gmail API
GMAIL_CLIENT_ID=your-client-id-here
GMAIL_CLIENT_SECRET=your-client-secret-here
GMAIL_REFRESH_TOKEN=your-refresh-token-here
INTAKE_EMAIL=your-new-gmail@gmail.com
```

You'll get the refresh token from Step 5.

---

## Security Notes

- **Keep credentials.json private** - it's in .gitignore
- **Never share your client secret or refresh token**
- The refresh token gives access to read emails
- Only grant access to the specific Gmail account for receipts

---

## Troubleshooting

### "App is not verified" warning
- This is normal for development
- Click **Advanced** → **Go to AutoExpense (unsafe)**
- This is safe because it's your own app

### Can't find Gmail API
- Make sure you've selected the correct Google Cloud project
- Wait a few minutes after creating the project

### Token expires
- Refresh tokens don't expire unless you revoke access
- If needed, re-run `get_gmail_token.py`

---

## Next Steps

Once you have the refresh token:
1. ✓ Update .env file
2. → Test email connection
3. → Start building email polling service

Let me know when you're ready to proceed!
