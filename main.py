from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
import os, requests
from dotenv import load_dotenv
from urllib.parse import urlencode
from supabase import create_client, Client
from datetime import datetime, timedelta


load_dotenv()
app = FastAPI()

# Get allowed origins from environment or use defaults
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000,http://127.0.0.1:8080").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,     
    allow_credentials=True,
    allow_methods=["*"],     
    allow_headers=["*"],       
)

FB_APP_ID = os.getenv("FB_APP_ID")
FB_APP_SECRET = os.getenv("FB_APP_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


print("FB_APP_ID:", FB_APP_ID)

@app.get("/auth/facebook")
def facebook_login():
    """
    Initiates Facebook OAuth login flow.
    
    Note: If you see "App not active" error, the Facebook app is likely in Development Mode.
    Solution: Add the user as a Test User or Developer in Facebook App Settings:
    1. Go to https://developers.facebook.com/apps/
    2. Select your app
    3. Go to Roles > Roles
    4. Add the user as a Developer or Tester
    """
    if not FB_APP_ID or not REDIRECT_URI:
        return JSONResponse(
            {"error": "Facebook app configuration missing. Check FB_APP_ID and REDIRECT_URI environment variables."},
            status_code=500
        )
    
    fb_url = (
        f"https://www.facebook.com/v19.0/dialog/oauth?"
        f"client_id={FB_APP_ID}&redirect_uri={REDIRECT_URI}"
        f"&scope=ads_read,business_management,ads_management"
        f"&response_type=code"
    )
    return RedirectResponse(fb_url)


@app.get("/auth/facebook/callback")
def facebook_callback(request: Request, code: str = None, error: str = None, error_reason: str = None):
    """
    Facebook OAuth callback handler.
    
    Handles errors from Facebook OAuth flow, including:
    - "App not active" error (app in development mode, user not added as tester/developer)
    - Access denied by user
    - Invalid redirect URI
    """
    if error:
        error_message = f"Facebook OAuth error: {error}"
        if error_reason:
            error_message += f" (Reason: {error_reason})"
        
        # Provide helpful message for common errors
        if error == "access_denied":
            error_message += " - User denied access to the app"
        elif "app_not_active" in error.lower() or "app_not_accessible" in error.lower():
            error_message += (
                "\n\nSOLUTION: The Facebook app is in Development Mode. "
                "Add the user as a Test User or Developer in Facebook App Settings:\n"
                "1. Go to https://developers.facebook.com/apps/\n"
                "2. Select your app\n"
                "3. Go to Roles > Roles\n"
                "4. Add the user as a Developer or Tester"
            )
        
        return JSONResponse({"error": error_message}, status_code=400)
    
    if not code:
        return JSONResponse({"error": "No authorization code provided"}, status_code=400)

    # Exchange code for short-lived token
    try:
        token_resp = requests.get(
            "https://graph.facebook.com/v19.0/oauth/access_token",
            params={
                "client_id": FB_APP_ID,
                "client_secret": FB_APP_SECRET,
                "redirect_uri": REDIRECT_URI,
                "code": code
            }
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
    except requests.exceptions.RequestException as e:
        return JSONResponse(
            {"error": "Failed to exchange code for access token", "details": str(e)},
            status_code=500
        )

    # Check for Facebook API errors
    if "error" in token_data:
        error_info = token_data.get("error", {})
        error_message = error_info.get("message", "Unknown error")
        error_type = error_info.get("type", "")
        
        if "app_not_active" in error_message.lower() or "app_not_accessible" in error_message.lower():
            error_message += (
                "\n\nSOLUTION: The Facebook app is in Development Mode. "
                "Add the user as a Test User or Developer in Facebook App Settings:\n"
                "1. Go to https://developers.facebook.com/apps/\n"
                "2. Select your app\n"
                "3. Go to Roles > Roles\n"
                "4. Add the user as a Developer or Tester"
            )
        
        return JSONResponse(
            {"error": f"Facebook API error: {error_message}", "error_type": error_type, "details": error_info},
            status_code=400
        )

    short_token = token_data.get("access_token")
    if not short_token:
        return JSONResponse({"error": "Failed to get access token", "details": token_data}, status_code=500)

    # Long-lived token
    try:
        long_resp = requests.get(
            "https://graph.facebook.com/v19.0/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": FB_APP_ID,
                "client_secret": FB_APP_SECRET,
                "fb_exchange_token": short_token
            }
        )
        long_resp.raise_for_status()
        long_data = long_resp.json()
    except requests.exceptions.RequestException as e:
        return JSONResponse(
            {"error": "Failed to exchange for long-lived token", "details": str(e)},
            status_code=500
        )
    
    if "error" in long_data:
        return JSONResponse(
            {"error": "Failed to get long-lived token", "details": long_data.get("error")},
            status_code=500
        )

    long_token = long_data.get("access_token")
    expires_in = long_data.get("expires_in", 5184000)  # Default 60 days if not provided
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    try:
        user_resp = requests.get(
            "https://graph.facebook.com/v19.0/me",
            params={"access_token": long_token, "fields": "id,name"}
        )
        user_resp.raise_for_status()
        user_info = user_resp.json()
    except requests.exceptions.RequestException as e:
        return JSONResponse(
            {"error": "Failed to get user info", "details": str(e)},
            status_code=500
        )
    
    if "error" in user_info:
        return JSONResponse(
            {"error": "Failed to get user info", "details": user_info.get("error")},
            status_code=500
        )

    facebook_user_id = user_info.get("id")
    name = user_info.get("name")
    
    if not facebook_user_id:
        return JSONResponse({"error": "Failed to get user ID from Facebook"}, status_code=500)

    # Upsert user into Supabase
    supabase.table("users").upsert({
        "facebook_user_id": facebook_user_id,
        "name": name,
        "access_token": long_token,
        "token_expires_at": expires_at.isoformat()  # <-- FIX
    }).execute()

    return JSONResponse({
        "message": f"User {name} logged in successfully",
        "facebook_user_id": facebook_user_id,
        "token_expires_at": expires_at.isoformat()
    })

@app.get("/facebook/adaccounts")
def get_ad_accounts(token: str):
    url = "https://graph.facebook.com/v19.0/me/adaccounts"
    params = {"access_token": token}
    resp = requests.get(url, params=params).json()
    return resp

@app.get("/facebook/adaccounts/{facebook_user_id}")
def get_ad_accounts(facebook_user_id: str):
    user = supabase.table("users").select("*").eq("facebook_user_id", facebook_user_id).single().execute()
    if not user.data:
        return {"error": "User not found"}

    access_token = user.data["access_token"]

    url = "https://graph.facebook.com/v19.0/me/adaccounts"
    params = {"access_token": access_token}
    resp = requests.get(url, params=params).json()
    return resp
