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


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "https://stripe.com"],     
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
    fb_url = (
        f"https://www.facebook.com/v19.0/dialog/oauth?"
        f"client_id={FB_APP_ID}&redirect_uri={REDIRECT_URI}"
        f"&scope=ads_read,business_management,ads_management"
        f"&response_type=code"
    )
    return RedirectResponse(fb_url)


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
    expires_in = long_resp.get("expires_in")  # seconds
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

    # User info
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
