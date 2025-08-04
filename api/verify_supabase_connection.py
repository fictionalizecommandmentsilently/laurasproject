import os
from supabase import create_client, Client

# Load environment variables from .env file if running locally
from dotenv import load_dotenv
load_dotenv()

def verify_supabase_connection():
    """
    Verifies the connection to Supabase using environment variables.
    """
    supabase_url: str = os.environ.get("SUPABASE_URL")
    supabase_service_role_key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not supabase_url:
        print("Error: SUPABASE_URL environment variable is not set.")
        return False
    if not supabase_service_role_key:
        print("Error: SUPABASE_SERVICE_ROLE_KEY environment variable is not set.")
        print("Please ensure you are using the Service Role Key, not the Anon Public Key, for backend operations.")
        return False

    try:
        # Attempt to create a client
        supabase: Client = create_client(supabase_url, supabase_service_role_key)
        print("Supabase client created successfully.")

        # Attempt a simple query to verify connection (e.g., fetch roles)
        # This requires RLS to be configured to allow service role key to bypass policies
        # or for the 'roles' table to have a policy allowing select for service_role.
        response = supabase.table('roles').select('*').limit(1).execute()
        
        if response.data is not None:
            print("Successfully fetched data from 'roles' table. Connection verified!")
            print(f"Example data: {response.data}")
            return True
        else:
            print(f"Failed to fetch data from 'roles' table. Response: {response.data}, Error: {response.error}")
            return False

    except Exception as e:
        print(f"An error occurred during Supabase connection verification: {e}")
        return False

if __name__ == "__main__":
    print("Attempting to verify Supabase connection...")
    if verify_supabase_connection():
        print("\nSupabase connection is working correctly!")
    else:
        print("\nSupabase connection failed. Please check your environment variables and Supabase project settings.")
