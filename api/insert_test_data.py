import os
from supabase import create_client, Client
from datetime import date, timedelta
import random

# Load environment variables from .env file if running locally
from dotenv import load_dotenv
load_dotenv()

def get_supabase_client() -> Client:
    """Initializes and returns a Supabase client."""
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Use service role key for backend
    if not url or not key:
        raise ValueError("Supabase URL and Service Role Key must be set in environment variables.")
    return create_client(url, key)

supabase: Client = get_supabase_client()

def insert_test_data():
    print("Inserting test data...")

    # --- Insert Roles (if not already present) ---
    roles_to_insert = [
        {"name": "admin"},
        {"name": "student"}
    ]
    try:
        response = supabase.table('roles').upsert(roles_to_insert, on_conflict='name').execute()
        print(f"Upserted roles: {response.data}")
        admin_role_id = next(r['id'] for r in response.data if r['name'] == 'admin')
        student_role_id = next(r['id'] for r in response.data if r['name'] == 'student')
    except Exception as e:
        print(f"Error upserting roles: {e}")
        return

    # --- Create Test Users (via Supabase Auth) and assign roles ---
    test_users_data = [
        {"email": "admin@example.com", "password": "password123", "roles": ["admin"]},
        {"email": "student1@example.com", "password": "password123", "roles": ["student"]},
        {"email": "student2@example.com", "password": "password123", "roles": ["student"]},
    ]

    for user_data in test_users_data:
        try:
            # Create user in Supabase Auth
            user_response = supabase.auth.admin.create_user(
                {
                    "email": user_data["email"],
                    "password": user_data["password"],
                    "email_confirm": True # Auto-confirm email for test data
                }
            )
            user_id = user_response.user.id
            print(f"Created user: {user_data['email']} with ID: {user_id}")

            # Assign roles
            roles_to_assign = []
            for role_name in user_data["roles"]:
                if role_name == "admin":
                    roles_to_assign.append({"user_id": user_id, "role_id": admin_role_id})
                elif role_name == "student":
                    roles_to_assign.append({"user_id": user_id, "role_id": student_role_id})
            
            if roles_to_assign:
                # Delete existing roles first to handle re-runs
                supabase.table('user_roles').delete().eq('user_id', user_id).execute()
                role_assign_response = supabase.table('user_roles').insert(roles_to_assign).execute()
                print(f"Assigned roles for {user_data['email']}: {role_assign_response.data}")

        except Exception as e:
            print(f"Error creating user {user_data['email']} or assigning roles: {e}")
            # If user already exists, try to get their ID and update roles
            try:
                existing_user = supabase.auth.admin.list_users(email=user_data["email"])
                if existing_user.users:
                    user_id = existing_user.users[0].id
                    print(f"User {user_data['email']} already exists with ID: {user_id}. Updating roles.")
                    roles_to_assign = []
                    for role_name in user_data["roles"]:
                        if role_name == "admin":
                            roles_to_assign.append({"user_id": user_id, "role_id": admin_role_id})
                        elif role_name == "student":
                            roles_to_assign.append({"user_id": user_id, "role_id": student_role_id})
                    
                    if roles_to_assign:
                        supabase.table('user_roles').delete().eq('user_id', user_id).execute()
                        role_assign_response = supabase.table('user_roles').insert(roles_to_assign).execute()
                        print(f"Updated roles for {user_data['email']}: {role_assign_response.data}")
            except Exception as inner_e:
                print(f"Could not update roles for existing user {user_data['email']}: {inner_e}")


    # --- Insert Test Students ---
    students_to_insert = [
        {
            "user_id": None, # Will be linked later
            "first_name": "Alice", "last_name": "Smith", "date_of_birth": date(2002, 5, 15),
            "gender": "Female", "email": "alice.smith@example.com", "phone_number": "555-111-2222",
            "address": "123 Main St", "city": "Anytown", "state": "CA", "zip_code": "90210",
            "enrollment_date": date(2020, 9, 1), "major": "Computer Science", "current_gpa": 3.85,
            "academic_standing": "Good", "advisor": "Dr. Brown", "expected_graduation_date": date(2024, 5, 20),
            "profile_picture_url": "/placeholder.svg?height=96&width=96"
        },
        {
            "user_id": None, # Will be linked later
            "first_name": "Bob", "last_name": "Johnson", "date_of_birth": date(2001, 11, 22),
            "gender": "Male", "email": "bob.johnson@example.com", "phone_number": "555-333-4444",
            "address": "456 Oak Ave", "city": "Anytown", "state": "CA", "zip_code": "90210",
            "enrollment_date": date(2019, 9, 1), "major": "Electrical Engineering", "current_gpa": 3.20,
            "academic_standing": "Probation", "advisor": "Prof. Green", "expected_graduation_date": date(2023, 12, 15),
            "profile_picture_url": "/placeholder.svg?height=96&width=96"
        },
        {
            "user_id": None, # Will be linked later
            "first_name": "Charlie", "last_name": "Brown", "date_of_birth": date(2003, 1, 1),
            "gender": "Male", "email": "charlie.brown@example.com", "phone_number": "555-555-6666",
            "address": "789 Pine Ln", "city": "Anytown", "state": "CA", "zip_code": "90210",
            "enrollment_date": date(2021, 9, 1), "major": "Physics", "current_gpa": 3.95,
            "academic_standing": "Good", "advisor": "Dr. White", "expected_graduation_date": date(2025, 5, 20),
            "profile_picture_url": "/placeholder.svg?height=96&width=96"
        },
    ]

    # Link students to auth.users if they exist
    try:
        student1_auth_user = supabase.auth.admin.list_users(email="student1@example.com")
        if student1_auth_user.users:
            students_to_insert[0]["user_id"] = student1_auth_user.users[0].id
        
        student2_auth_user = supabase.auth.admin.list_users(email="student2@example.com")
        if student2_auth_user.users:
            students_to_insert[1]["user_id"] = student2_auth_user.users[0].id

    except Exception as e:
        print(f"Could not link students to auth users: {e}")


    try:
        # Delete existing students to prevent duplicates on re-run
        supabase.table('students').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
        
        student_response = supabase.table('students').insert(students_to_insert).execute()
        print(f"Inserted {len(student_response.data)} students.")

        # --- Insert GPA History ---
        gpa_history_to_insert = []
        for student in student_response.data:
            student_id = student['id']
            current_gpa = student['current_gpa']
            
            # Generate 5 historical GPA entries
            for i in range(5):
                gpa = round(current_gpa - (random.random() * 0.5) + (i * 0.1), 2)
                gpa = max(0.0, min(4.0, gpa)) # Ensure GPA is within 0-4 range
                date_recorded = student['enrollment_date'] + timedelta(days=i * 90) # Quarterly updates
                gpa_history_to_insert.append({
                    "student_id": student_id,
                    "gpa": gpa,
                    "date_recorded": date_recorded
                })
        
        if gpa_history_to_insert:
            gpa_response = supabase.table('gpa_history').insert(gpa_history_to_insert).execute()
            print(f"Inserted {len(gpa_response.data)} GPA history records.")

    except Exception as e:
        print(f"Error inserting students or GPA history: {e}")

if __name__ == "__main__":
    insert_test_data()
    print("Test data insertion complete.")
