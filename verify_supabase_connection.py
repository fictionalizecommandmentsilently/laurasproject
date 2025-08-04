import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables from .env file
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") # Use the service_role key for backend operations

print(f"Verifying Supabase connection to: {SUPABASE_URL}")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set as environment variables in the .env file.")
    exit(1)

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Supabase client initialized successfully.")

    # Attempt to fetch data from the 'students' table
    print("Attempting to fetch data from 'students' table...")
    response = supabase.table("students").select("*").limit(5).execute()

    if response.data:
        print("\nSuccessfully connected to Supabase and retrieved data from 'students' table!")
        print(f"Number of rows retrieved: {len(response.data)}")
        print("Sample data:")
        for row in response.data:
            print(row)
    elif response.error:
        print(f"\nError fetching data from 'students' table: {response.error.message}")
        print("Please ensure the 'students' table exists and has data, and RLS policies allow access.")
    else:
        print("\nSuccessfully connected to Supabase, but no data found in 'students' table.")
        print("Please ensure you have inserted test data (e.g., by running insert_test_data.py).")

except Exception as e:
    print(f"\nAn unexpected error occurred during Supabase connection or data retrieval: {e}")
    print("Please check your SUPABASE_URL, SUPABASE_KEY, and network connectivity.")
