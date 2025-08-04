import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Supabase credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") # Use service_role key for write operations in production

if not SUPABASE_URL or not SUPABASE_KEY:
  raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set as environment variables in the .env file.")

# Initialize Supabase client globally for reuse
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_supabase_client(url: str = SUPABASE_URL, key: str = SUPABASE_KEY) -> Client:
  """
  Dependency to get a Supabase client instance.
  Can be used in FastAPI path operations.
  """
  return create_client(url, key)
