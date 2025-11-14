import os
import time
import secrets
import smtplib
import ssl
import socket
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dateutil.parser import parse as parse_datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body, BackgroundTasks
from fastapi.responses import HTMLResponse
from supabase import create_client

from app.helpers.security import get_current_user, verify_password, hash_password

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

router = APIRouter()


class GmailService:
    """Service for sending emails via Gmail SMTP"""
    
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.ssl_port = 465
        self.email = os.getenv("GMAIL_EMAIL")
        self.password = os.getenv("GMAIL_APP_PASSWORD")
        self.executor = ThreadPoolExecutor(max_workers=3)
    
    def _create_message(self, to_email: str, subject: str, body: str, is_html: bool = False) -> MIMEMultipart:
        """Create email message"""
        msg = MIMEMultipart()
        msg['From'] = self.email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html' if is_html else 'plain'))
        return msg
    
    def _send_email_sync(self, to_email: str, subject: str, body: str, is_html: bool = False) -> tuple[bool, str]:
        """Send email using SSL (port 465)"""
        if not self.email or not self.password:
            return False, "Gmail credentials not configured"
        
        msg = self._create_message(to_email, subject, body, is_html)
        
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            socket.setdefaulttimeout(15)
            
            with smtplib.SMTP_SSL(self.smtp_server, self.ssl_port, context=context, timeout=15) as server:
                server.ehlo()
                server.login(self.email, self.password)
                server.sendmail(self.email, to_email, msg.as_string())
            
            return True, "Email sent via SSL (port 465)"
            
        except socket.timeout:
            return False, "SSL connection timed out"
        except smtplib.SMTPAuthenticationError as e:
            return False, f"SSL authentication failed: {str(e)}"
        except Exception as e:
            return False, f"SSL failed: {str(e)}"
        finally:
            socket.setdefaulttimeout(None)
    
    async def send_email(self, to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
        """Async wrapper for email sending"""
        loop = asyncio.get_event_loop()
        
        try:
            success, message = await loop.run_in_executor(
                self.executor,
                self._send_email_sync,
                to_email, subject, body, is_html
            )
            
            if success:
                print(f"✅ Email sent successfully to {to_email}")
            else:
                print(f"❌ Failed to send email to {to_email}: {message}")
            
            return success
                
        except Exception as e:
            print(f"❌ Async email sending error: {str(e)}")
            return False
    
    def send_email_sync(self, to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
        """Synchronous version for testing"""
        success, message = self._send_email_sync(to_email, subject, body, is_html)
        print(f"{'✅' if success else '❌'} {message}")
        return success

gmail_service = GmailService()

@router.get("/me")
def get_current_user_info(current_user: dict = Depends(get_current_user)) -> dict:
    """Get current user information including avatar URL and 2FA status"""
    return {
        "id": current_user["id"],
        "first_name": current_user["first_name"],
        "last_name": current_user["last_name"],
        "email": current_user["email"],
        "company": current_user.get("company"),
        "avatar": current_user.get("avatar"),
        "created_at": current_user["created_at"],
        "two_factor": current_user.get("two_factor", False) 
    }



@router.put("/update")
async def update_profile(
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    two_factor: Optional[bool] = Form(None), 
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Update user profile with avatar URL handling and two-factor update"""
    start_time = time.time()
    update_data = {}
    avatar_url = None

    if first_name:
        update_data["first_name"] = first_name
    if last_name:
        update_data["last_name"] = last_name
    if email:
        update_data["email"] = email
    if two_factor is not None:
        update_data["two_factor"] = two_factor 
    
    if avatar:
        try:
            file_bytes = await avatar.read()
            file_extension = os.path.splitext(avatar.filename)[1] if avatar.filename else '.jpg'
            filename = f"user_{current_user['id']}_avatar{file_extension}"

            upload_response = supabase.storage.from_(BUCKET_NAME).upload(
                filename,
                file_bytes,
                {
                    "upsert": "true",
                    "content-type": avatar.content_type or "image/jpeg"
                }
            )

            avatar_url = supabase.storage.from_(BUCKET_NAME).get_public_url(filename)
            update_data["avatar"] = avatar_url

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload avatar: {str(e)}")

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    try:
        response = (
            supabase.table("users")
            .update(update_data)
            .eq("id", current_user["id"])
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to update profile")

        updated_user = response.data[0]
        execution_time = round(time.time() - start_time, 2)

        return {
            "message": "Profile updated successfully",
            "id": updated_user["id"],
            "first_name": updated_user.get("first_name"),
            "last_name": updated_user.get("last_name"),
            "email": updated_user.get("email"),
            "avatar": updated_user.get("avatar"),
            "company": updated_user.get("company"),
            "two_factor": updated_user.get("two_factor"), 
            "created_at": updated_user.get("created_at"),
            "avatar_url": avatar_url,
            "execution_time": execution_time
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database update failed: {str(e)}")

@router.put("/password")
async def request_password_update(
    background_tasks: BackgroundTasks,
    current_password: str = Body(...),
    new_password: str = Body(...),
    confirm_password: str = Body(...),
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Request password update using user's 2FA setting to determine email verification"""
    
    if new_password != confirm_password:
        raise HTTPException(status_code=400, detail="New password and confirmation do not match")
    
    if not verify_password(current_password, current_user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    require_email_verification = current_user.get("two_factor", False)
    print(f"Password change requires email verification: {require_email_verification}")

    if not require_email_verification:
        new_password_hash = hash_password(new_password)
        try:
            response = (
                supabase.table("users")
                .update({"password_hash": new_password_hash})
                .eq("id", current_user["id"])
                .execute()
            )
            
            if not response.data:
                raise HTTPException(status_code=400, detail="Failed to update password")
            
            return {"message": "Password updated successfully"}
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error updating password: {str(e)}")
    
    else:
        verification_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        
        try:
            new_password_hash = hash_password(new_password)
            response = (
                supabase.table("users")
                .update({
                    "password_reset_token": verification_token,
                    "password_reset_expires": expires_at.isoformat(),
                    "pending_password_hash": new_password_hash
                })
                .eq("id", current_user["id"])
                .execute()
            )
            
            if not response.data:
                raise HTTPException(status_code=400, detail="Failed to initiate password update")
            
            background_tasks.add_task(
                send_password_verification_email,
                current_user["email"],
                current_user.get("first_name", current_user["email"]),
                verification_token
            )
            
            return {
                "message": "Password verification email sent. Please check your email to confirm the change",
                "expires_in_hours": 24
            }
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error initiating password update: {str(e)}")

@router.get("/password/approve/{token}")
async def approve_password_change(token: str) -> HTMLResponse:
    """Approve password change via email link"""
    
    try:
        response = (
            supabase.table("users")
            .select("id, email, password_reset_expires, pending_password_hash")
            .eq("password_reset_token", token)
            .execute()
        )
        
        if not response.data:
            return HTMLResponse(content=_get_error_html("Invalid Token", "The verification token is invalid or has already been used."), status_code=400)
        
        user = response.data[0]
        
        expires_at = parse_datetime(user["password_reset_expires"])
        if datetime.utcnow().replace(tzinfo=expires_at.tzinfo) > expires_at:
            _clear_password_reset_data(user["id"])
            return HTMLResponse(
                content=_get_error_html("Token Expired", "The verification token has expired. Please request a new password change."),
                status_code=400
            )
        update_response = (
            supabase.table("users")
            .update({
                "password_hash": user["pending_password_hash"],
                "password_reset_token": None,
                "password_reset_expires": None,
                "pending_password_hash": None
            })
            .eq("id", user["id"])
            .execute()
        )
        
        if not update_response.data:
            return HTMLResponse(content=_get_error_html("Update Failed", "Failed to update password. Please try again."), status_code=400)
        
        return HTMLResponse(content=_get_success_html("Password Updated Successfully!", "Your password has been changed successfully. You can now use your new password to log in."))
        
    except Exception as e:
        return HTMLResponse(content=_get_error_html("Error", f"An error occurred while processing your request: {str(e)}"), status_code=500)


@router.get("/password/deny/{token}")
async def deny_password_change(token: str) -> HTMLResponse:
    """Deny password change via email link"""
    
    try:
        response = (
            supabase.table("users")
            .select("id, email")
            .eq("password_reset_token", token)
            .execute()
        )
        
        if not response.data:
            return HTMLResponse(content=_get_error_html("Invalid Token", "The verification token is invalid or has already been used."), status_code=400)
        
        user = response.data[0]
        
        update_response = _clear_password_reset_data(user["id"])
        
        if not update_response.data:
            return HTMLResponse(content=_get_error_html("Error", "Failed to process denial. Please try again."), status_code=400)
        
        return HTMLResponse(content=_get_success_html("Password Change Denied", "The password change request has been cancelled. Your current password remains unchanged.", "🔒"))
        
    except Exception as e:
        return HTMLResponse(content=_get_error_html("Error", f"An error occurred while processing your request: {str(e)}"), status_code=500)


def _clear_password_reset_data(user_id: str):
    """Helper function to clear password reset data"""
    return (
        supabase.table("users")
        .update({
            "password_reset_token": None,
            "password_reset_expires": None,
            "pending_password_hash": None
        })
        .eq("id", user_id)
        .execute()
    )


def _get_error_html(title: str, message: str) -> str:
    """Generate error HTML response"""
    return f"""
    <html><body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
        <h2 style="color: #f44336;">❌ {title}</h2>
        <p>{message}</p>
    </body></html>
    """


def _get_success_html(title: str, message: str, emoji: str = "✅") -> str:
    """Generate success HTML response"""
    return f"""
    <html><body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
        <h2 style="color: #4CAF50;">{emoji} {title}</h2>
        <p>{message}</p>
        <p style="color: #666; margin-top: 30px;">You can close this window.</p>
    </body></html>
    """


async def send_password_verification_email(email: str, user_name: str, token: str) -> None:
    """Send password verification email with approve/deny links"""
    
    base_url = os.getenv("BASE_URL")
    approve_url = f"{base_url}/users/password/approve/{token}"
    deny_url = f"{base_url}/users/password/deny/{token}"
    
    subject = "🔐 Approve Your Password Change"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            .container {{ max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif; }}
            .header {{ background-color: #2196F3; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 30px; background-color: #f9f9f9; }}
            .button-container {{ text-align: center; margin: 30px 0; }}
            .approve-btn {{ 
                background-color: #4CAF50; 
                color: white; 
                padding: 15px 30px; 
                text-decoration: none; 
                border-radius: 5px; 
                display: inline-block; 
                margin: 0 10px;
                font-weight: bold;
            }}
            .deny-btn {{ 
                background-color: #f44336; 
                color: white; 
                padding: 15px 30px; 
                text-decoration: none; 
                border-radius: 5px; 
                display: inline-block; 
                margin: 0 10px;
                font-weight: bold;
            }}
            .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .info {{ background-color: #e3f2fd; border: 1px solid #2196F3; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .footer {{ background-color: #333; color: white; padding: 15px; text-align: center; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 Password Change Request</h1>
            </div>
            
            <div class="content">
                <p>Hello <strong>{user_name}</strong>,</p>
                
                <p>You have requested to change your password. Please choose one of the options below:</p>
                
                <div class="button-container">
                    <a href="{approve_url}" class="approve-btn">✅ APPROVE CHANGE</a>
                    <a href="{deny_url}" class="deny-btn">❌ DENY CHANGE</a>
                </div>
                
                <div class="info">
                    <strong>📋 What happens next:</strong><br>
                    • <strong>Approve:</strong> Your password will be updated immediately<br>
                    • <strong>Deny:</strong> Your current password will remain unchanged<br>
                    • <strong>No action:</strong> Request expires in 24 hours
                </div>
                
                <div class="warning">
                    <strong>⚠️ Security Notice:</strong><br>
                    • If you didn't request this change, click <strong>DENY</strong> immediately<br>
                    • This request expires in <strong>24 hours</strong><br>
                    • Only click APPROVE if you initiated this password change
                </div>
                
                <p>Best regards,<br>Your Security Team</p>
            </div>
            
            <div class="footer">
                This is an automated security email. The links will expire in 24 hours.
            </div>
        </div>
    </body>
    </html>
    """
    
    success = await gmail_service.send_email(email, subject, html_body, is_html=True)
    
    if not success:
        print(f"Failed to send verification email to {email}")
    else:
        print(f"Password verification email sent to {email}")