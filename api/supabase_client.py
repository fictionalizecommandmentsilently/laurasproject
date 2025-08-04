import os
from supabase import create_client, Client

def get_supabase_client() -> Client:
    """Initializes and returns a Supabase client."""
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Use service role key for backend
    if not url or not key:
        raise ValueError("Supabase URL and Service Role Key must be set in environment variables.")
    return create_client(url, key)

supabase: Client = get_supabase_client()
