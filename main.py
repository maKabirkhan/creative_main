from fastapi import FastAPI, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os, requests
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import datetime, timedelta

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "https://stripe.com"],     
    allow_credentials=True,
    allow_methods=["*"],     
    allow_headers=["*"],       
)

# Facebook and Supabase config
FB_APP_ID = os.getenv("FB_APP_ID")
FB_APP_SECRET = os.getenv("FB_APP_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
REQUIRED_PERMISSIONS = {"ads_read", "ads_management", "business_management"}

# ----------------- Utility Functions -----------------
def validate_token(token: str):
    """Check that the token has all required Facebook permissions."""
    url = "https://graph.facebook.com/v19.0/me/permissions"
    resp = requests.get(url, params={"access_token": token}).json()

    if "error" in resp:
        return False, f"Facebook error: {resp['error']['message']}"

    granted = {p['permission'] for p in resp.get('data', []) if p['status'] == 'granted'}
    missing = REQUIRED_PERMISSIONS - granted

    if missing:
        return False, f"Missing permissions: {', '.join(missing)}"
    return True, None

def get_user_access_token(facebook_user_id: str):
    """Fetch token from Supabase and check expiry."""
    user_resp = supabase.table("users").select("*").eq("facebook_user_id", facebook_user_id).execute()

    if not user_resp.data or len(user_resp.data) == 0:
        return None, "User not found"

    user = user_resp.data[0]  # safe access
    token = user["access_token"]
    expires_at = datetime.fromisoformat(user["token_expires_at"])
    
    if datetime.utcnow() >= expires_at:
        return None, "Token expired, please login again"
    
    return token, None


# ----------------- Auth Endpoints -----------------

@app.post("/auth/facebook/token")
def facebook_login_with_token(data: dict = Body(...)):
    """Receive a Facebook access token, validate, and always upsert user into Supabase."""
    access_token = data.get("access_token")
    if not access_token:
        return JSONResponse({"error": "No access token provided"}, status_code=400)

    # Validate Facebook permissions
    is_valid, error = validate_token(access_token)
    if not is_valid:
        return JSONResponse({"error": error}, status_code=400)

    # Get user info from Facebook
    user_info = requests.get(
        "https://graph.facebook.com/v19.0/me",
        params={"access_token": access_token, "fields": "id,name"}
    ).json()

    facebook_user_id = user_info.get("id")
    name = user_info.get("name")
    if not facebook_user_id:
        return JSONResponse({"error": "Invalid access token", "details": user_info}, status_code=400)

    # Always update token and expiry in Supabase
    expires_at = datetime.utcnow() + timedelta(days=60)

    # FIX: specify conflict target for upsert
    supabase.table("users").upsert(
        {
            "facebook_user_id": facebook_user_id,
            "name": name,
            "access_token": access_token,
            "token_expires_at": expires_at.isoformat()
        },
        on_conflict="facebook_user_id"  # <-- key to update if exists
    ).execute()

    # Fetch ad accounts
    ad_accounts_resp = requests.get(
        "https://graph.facebook.com/v19.0/me/adaccounts",
        params={"access_token": access_token}
    ).json()

    return JSONResponse({
        "message": f"User {name} logged in successfully",
        "facebook_user_id": facebook_user_id,
        "token_expires_at": expires_at.isoformat(),
        "ad_accounts": ad_accounts_resp
    })


@app.get("/auth/facebook/callback")
def facebook_callback(request: Request, code: str = None):
    if not code:
        return JSONResponse({"error": "No code provided"})

    # Exchange code for short-lived token
    token_resp = requests.get(
        "https://graph.facebook.com/v19.0/oauth/access_token",
        params={
            "client_id": FB_APP_ID,
            "client_secret": FB_APP_SECRET,
            "redirect_uri": REDIRECT_URI,
            "code": code
        }
    ).json()

    short_token = token_resp.get("access_token")
    if not short_token:
        return JSONResponse({"error": "Failed to get access token", "details": token_resp})

    # Long-lived token
    long_resp = requests.get(
        "https://graph.facebook.com/v19.0/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": FB_APP_ID,
            "client_secret": FB_APP_SECRET,
            "fb_exchange_token": short_token
        }
    ).json()

    long_token = long_resp.get("access_token")
    expires_in = long_resp.get("expires_in")
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    user_info = requests.get(
        "https://graph.facebook.com/v19.0/me",
        params={"access_token": long_token, "fields": "id,name"}
    ).json()

    facebook_user_id = user_info.get("id")
    name = user_info.get("name")

    # Upsert user into Supabase
    supabase.table("users").upsert({
        "facebook_user_id": facebook_user_id,
        "name": name,
        "access_token": long_token,
        "token_expires_at": expires_at.isoformat()
    }).execute()

    return JSONResponse({
        "message": f"User {name} logged in successfully",
        "facebook_user_id": facebook_user_id,
        "token_expires_at": expires_at.isoformat()
    })

# ----------------- Hierarchical Facebook Ads Endpoints -----------------
@app.get("/facebook/adaccounts/{facebook_user_id}")
def get_ad_accounts(facebook_user_id: str):
    """Get all ad accounts for a Facebook user."""
    access_token, error = get_user_access_token(facebook_user_id)
    if not access_token:
        return JSONResponse({"error": error}, status_code=404)

    url = "https://graph.facebook.com/v19.0/me/adaccounts"
    resp = requests.get(url, params={"access_token": access_token}).json()
    return resp


@app.get("/facebook/campaigns/{ad_account_id}")
def get_campaigns(ad_account_id: str, token: str = None):
    """Get campaigns for a given ad account."""
    if not token:
        return JSONResponse({"error": "Access token required"}, status_code=400)
    
    url = f"https://graph.facebook.com/v19.0/act_{ad_account_id}/campaigns"
    resp = requests.get(url, params={"access_token": token}).json()
    return resp

@app.get("/facebook/adsets/{campaign_id}")
def get_adsets(campaign_id: str, token: str = None):
    """Get ad sets for a given campaign."""
    if not token:
        return JSONResponse({"error": "Access token required"}, status_code=400)
    
    url = f"https://graph.facebook.com/v19.0/{campaign_id}/adsets"
    resp = requests.get(url, params={"access_token": token}).json()
    return resp

@app.get("/facebook/ads/{ad_set_id}")
def get_ads(ad_set_id: str, token: str = None):
    """Get ads for a given ad set."""
    if not token:
        return JSONResponse({"error": "Access token required"}, status_code=400)
    
    url = f"https://graph.facebook.com/v19.0/{ad_set_id}/ads"
    resp = requests.get(url, params={"access_token": token}).json()
    return resp
