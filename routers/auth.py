from fastapi import Depends, APIRouter, HTTPException
from app.helpers.security import create_persistent_token, verify_password, hash_password
from app.helpers.db import get_user_by_email, supabase
from app.helpers.validators import validate_required_field
from app.schemas.user import UserCreate, UserLogin, Token, GoogleLogin
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()
security = HTTPBearer()

@router.post("/register", response_model=Token)
def register(user: UserCreate):
    validate_required_field(user.first_name, "First name")
    validate_required_field(user.last_name, "Last name")
    validate_required_field(user.email, "Email")
    validate_required_field(user.password, "Password")

    existing_user = get_user_by_email(user.email)
    if existing_user:
        # Check auth provider
        auth_provider = existing_user.get("auth_provider", "local")
        if auth_provider == "google":
            raise HTTPException(
                status_code=400, 
                detail="This email is already registered with Google. Please sign in with Google."
            )
        raise HTTPException(status_code=400, detail="Email already registered with email/password.")

    hashed_pw = hash_password(user.password)
    response = supabase.table("users").insert({
        "email": user.email,
        "password_hash": hashed_pw,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "two_factor": False,
        "auth_provider": "local"
    }).execute()

    if not response.data:
        raise HTTPException(status_code=400, detail="Failed to create user")

    created_user = response.data[0]
    access_token = create_persistent_token(user.email, created_user["id"])
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
def login(user: UserLogin):
    validate_required_field(user.email, "Email")
    validate_required_field(user.password, "Password")

    db_user = get_user_by_email(user.email)
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Check if user registered with Google
    if db_user.get("auth_provider") == "google":
        raise HTTPException(
            status_code=401, 
            detail="This email is registered with Google. Please sign in with Google."
        )
    
    if not verify_password(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_persistent_token(user.email, db_user["id"])
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login/google", response_model=Token)
def google_login(google_data: GoogleLogin):
    """
    Handle Google OAuth login/registration.
    Expected data: google_id, email, first_name, last_name, avatar (optional)
    """
    validate_required_field(google_data.email, "Email")
    validate_required_field(google_data.google_id, "Google ID")
    validate_required_field(google_data.first_name, "First name")
    validate_required_field(google_data.last_name, "Last name")

    existing_user = get_user_by_email(google_data.email)
    
    if existing_user:
        # Check if user registered with local auth
        if existing_user.get("auth_provider") == "local":
            raise HTTPException(
                status_code=400,
                detail="This email is already registered with email/password. Please sign in with your password."
            )
        
        # User already exists with Google, just login
        access_token = create_persistent_token(existing_user["email"], existing_user["id"])
        return {"access_token": access_token, "token_type": "bearer"}
    
    # Create new user with Google auth
    user_data = {
        "email": google_data.email,
        "first_name": google_data.first_name,
        "last_name": google_data.last_name,
        "auth_provider": "google",
        "google_id": google_data.google_id,
        "two_factor": False
    }
    
    if google_data.avatar:
        user_data["avatar"] = google_data.avatar
    
    response = supabase.table("users").insert(user_data).execute()
    
    if not response.data:
        raise HTTPException(status_code=400, detail="Failed to create user")
    
    created_user = response.data[0]
    access_token = create_persistent_token(created_user["email"], created_user["id"])
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
def logout(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Logout endpoint - expires the current token immediately.
    Token becomes invalid after this call.
    """
    from app.helpers.security import expire_token
    
    if expire_token(credentials.credentials):
        return {"message": "Successfully logged out"}
    else:
        raise HTTPException(status_code=400, detail="Failed to logout")