import os
from dotenv import load_dotenv
from supabase import create_client, Client
from datetime import date

# Load environment variables from .env file
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") # Use the service_role key for backend operations

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set as environment variables in the .env file.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def insert_test_students():
    students_data = [
        {
            "student_id": "S001",
            "first_name": "Alice",
            "last_name": "Smith",
            "date_of_birth": date(2000, 1, 15).isoformat(),
            "gender": "Female",
            "email": "alice.smith@example.com",
            "phone_number": "111-222-3333",
            "address": "123 Main St, Anytown, USA",
            "enrollment_date": date(2018, 9, 1).isoformat(),
            "major": "Computer Science",
            "gpa": 3.85,
            "academic_standing": "Good Standing",
            "advisor": "Dr. Emily White",
            "enrollment_status": "Enrolled",
            "financial_aid_status": "Eligible",
            "scholarship_amount": 5000.00
        },
        {
            "student_id": "S002",
            "first_name": "Bob",
            "last_name": "Johnson",
            "date_of_birth": date(1999, 5, 20).isoformat(),
            "gender": "Male",
            "email": "bob.j@example.com",
            "phone_number": "444-555-6666",
            "address": "456 Oak Ave, Otherville, USA",
            "enrollment_date": date(2017, 9, 1).isoformat(),
            "major": "Mathematics",
            "gpa": 3.20,
            "academic_standing": "Probation",
            "advisor": "Prof. David Green",
            "enrollment_status": "Enrolled",
            "financial_aid_status": "Not Eligible",
            "scholarship_amount": 0.00
        },
        {
            "student_id": "S003",
            "first_name": "Charlie",
            "last_name": "Brown",
            "date_of_birth": date(2001, 11, 10).isoformat(),
            "gender": "Non-binary",
            "email": "charlie.b@example.com",
            "phone_number": "777-888-9999",
            "address": "789 Pine Ln, Somewhere, USA",
            "enrollment_date": date(2019, 9, 1).isoformat(),
            "major": "Physics",
            "gpa": 3.95,
            "academic_standing": "Good Standing",
            "advisor": "Dr. Sarah Lee",
            "enrollment_status": "Enrolled",
            "financial_aid_status": "Eligible",
            "scholarship_amount": 7500.00
        }
    ]

    try:
        # Delete existing test data to prevent duplicates on re-run
        print("Attempting to delete existing test student data...")
        delete_response = supabase.table("students").delete().in_("student_id", ["S001", "S002", "S003"]).execute()
        if delete_response.error:
            print(f"Warning: Could not delete existing data (might not exist): {delete_response.error.message}")
        else:
            print("Existing test student data deleted (if any).")

        print("Inserting new test student data...")
        response = supabase.table("students").insert(students_data).execute()

        if response.data:
            print(f"Successfully inserted {len(response.data)} test student records.")
            for student in response.data:
                print(f"  Inserted: {student['first_name']} {student['last_name']} (ID: {student['student_id']})")
        elif response.error:
            print(f"Error inserting data: {response.error.message}")
            print("Please ensure your Supabase table 'students' exists and RLS policies allow insertion.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    insert_test_students()
