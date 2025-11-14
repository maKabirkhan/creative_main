from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

# Add validation
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

supabase: Client = create_client(supabase_url, supabase_key)

def get_user_by_email(email: str):
    """Fetch a single user by email."""
    response = supabase.table("users").select("*").eq("email", email).execute()
    return response.data[0] if response.data else None