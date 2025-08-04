import csv
import json
import pandas as pd
from io import StringIO
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from typing import List, Dict, Any, Optional
from pydantic import ValidationError
from supabase import Client
from supabase_client import get_supabase_client, supabase
from student_ingestion_route import StudentIngestionPayload, StudentProfileData, StudentInfoCore, Course, AssessmentBreakdown, GPAHistoryEntry, AttendanceData, Absences, Tardies, ExtracurricularActivity, IEP504Plan, CollegeMilestone, NarrativeComment, StaffNote, SoftSkillInference, UnstructuredData, _insert_single_student_profile_normalized, StudentData, StudentProfile, FinancialAid
from auth_utils import get_current_user_role, get_current_admin_user
from datetime import date
import uuid
import requests
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

router = APIRouter()

def generate_uuid():
    return str(uuid.uuid4())

def parse_csv_to_json(file_content: bytes) -> List[Dict[str, Any]]:
    decoded_content = file_content.decode('utf-8').splitlines()
    reader = csv.DictReader(decoded_content)
    return list(reader)

def map_csv_to_student_payload(csv_data: Dict[str, Any]) -> StudentIngestionPayload:
    # This is a simplified mapping. In a real application, you'd need robust
    # logic to parse and validate each field, especially nested JSONB fields.
    # For example, 'courses' might be a JSON string in CSV that needs json.loads()
    # and then validation against CourseSchema.

    # Example of handling nested JSON strings from CSV
    def parse_json_field(field_name: str, default_value: Any = None):
        value = csv_data.get(field_name)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse JSON for field '{field_name}': {value}")
                return default_value
        return default_value

    student_info_core = StudentInfoCore(
        full_name=csv_data.get("full_name", "N/A"),
        grade_level=int(csv_data.get("grade_level", 0)),
        academic_year=csv_data.get("academic_year", "N/A"),
        status=csv_data.get("status", "None"),
        assessment_breakdown_by_type=parse_json_field("assessment_breakdown_by_type", [])
    )

    attendance_data = AttendanceData(
        absences=Absences(
            excused=int(csv_data.get("absences_excused", 0)),
            unexcused=int(csv_data.get("absences_unexcused", 0))
        ),
        tardies=Tardies(
            count=int(csv_data.get("tardies_count", 0)),
            dates=parse_json_field("tardies_dates", [])
        )
    )

    iep_504_plan_info = IEP504Plan(
        has_plan=csv_data.get("iep_has_plan", "false").lower() == "true",
        plan_type=csv_data.get("iep_plan_type"),
        accommodations=parse_json_field("iep_accommodations", []),
        last_updated_date=csv_data.get("iep_last_updated_date")
    )

    return StudentIngestionPayload(
        student_profile=StudentProfileData(
            student_info=student_info_core,
            courses=parse_json_field("courses", []),
            gpa_history=parse_json_field("gpa_history", []),
            attendance=attendance_data,
            extracurricular_activities=parse_json_field("extracurricular_activities", []),
            iep_504_plan_information=iep_504_plan_info,
            college_counseling_milestones=parse_json_field("college_counseling_milestones", [])
        ),
        unstructured_data=UnstructuredData(
            narrative_teacher_comments=parse_json_field("narrative_teacher_comments", []),
            advisory_counselor_notes=parse_json_field("advisory_counselor_notes", []),
            behavior_social_emotional_notes=parse_json_field("behavior_social_emotional_notes", [])
        ),
        soft_skill_inferences=SoftSkillInferences(
            soft_skill_inferences=parse_json_field("soft_skill_inferences", [])
        )
    )

def parse_csv_to_student_data(file_path: str) -> List[StudentData]:
    students_data = []
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            # Basic parsing, adjust field names as per your CSV structure
            student_profile = StudentProfile(
                student_id=row.get('student_id', generate_uuid()),
                first_name=row['first_name'],
                last_name=row['last_name'],
                date_of_birth=row['date_of_birth'],
                gender=row['gender'],
                email=row['email'],
                phone_number=row.get('phone_number'),
                address=row.get('address'),
                city=row.get('city'),
                state=row.get('state'),
                zip_code=row.get('zip_code'),
                enrollment_date=row['enrollment_date'],
                grade_level=int(row['grade_level']),
                major=row.get('major'),
                gpa=float(row['gpa']) if row.get('gpa') else None,
                academic_standing=row.get('academic_standing'),
                advisor_id=row.get('advisor_id'),
                emergency_contact_name=row.get('emergency_contact_name'),
                emergency_contact_phone=row.get('emergency_contact_phone'),
                medical_conditions=row.get('medical_conditions'),
                notes=row.get('notes')
            )

            # Assuming courses, attendance, financial_aid are in separate CSVs or handled differently
            # For a single CSV, you might need to flatten the structure or make assumptions
            # This example assumes only profile data from the main CSV
            students_data.append(StudentData(profile=student_profile))
    return students_data

def parse_json_to_student_data(file_path: str) -> List[StudentData]:
    with open(file_path, mode='r', encoding='utf-8') as file:
        data = json.load(file)
        students_data = []
        for item in data:
            profile_data = item.get('profile', {})
            courses_data = item.get('courses', [])
            attendance_data = item.get('attendance', [])
            financial_aid_data = item.get('financial_aid', [])

            student_profile = StudentProfile(
                student_id=profile_data.get('student_id', generate_uuid()),
                first_name=profile_data['first_name'],
                last_name=profile_data['last_name'],
                date_of_birth=profile_data['date_of_birth'],
                gender=profile_data['gender'],
                email=profile_data['email'],
                phone_number=profile_data.get('phone_number'),
                address=profile_data.get('address'),
                city=profile_data.get('city'),
                state=profile_data.get('state'),
                zip_code=profile_data.get('zip_code'),
                enrollment_date=profile_data['enrollment_date'],
                grade_level=int(profile_data['grade_level']),
                major=profile_data.get('major'),
                gpa=float(profile_data['gpa']) if profile_data.get('gpa') else None,
                academic_standing=profile_data.get('academic_standing'),
                advisor_id=profile_data.get('advisor_id'),
                emergency_contact_name=profile_data.get('emergency_contact_name'),
                emergency_contact_phone=profile_data.get('emergency_contact_phone'),
                medical_conditions=profile_data.get('medical_conditions'),
                notes=profile_data.get('notes')
            )

            courses = [Course(**c) for c in courses_data]
            attendance = [Attendance(**a) for a in attendance_data]
            financial_aid = [FinancialAid(**f) for f in financial_aid_data]

            students_data.append(StudentData(
                profile=student_profile,
                courses=courses,
                attendance=attendance,
                financial_aid=financial_aid
            ))
        return students_data

@router.post("/upload/students-bulk", status_code=status.HTTP_201_CREATED)
async def upload_students_bulk(
    file: UploadFile = File(...),
    supabase: Any = Depends(get_supabase_client),
    user_role: str = Depends(get_current_user_role)
):
    if user_role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only administrators can bulk upload student data.")

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file uploaded.")

    file_content = await file.read()
    processed_count = 0
    failed_count = 0
    errors = []

    try:
        if file.content_type == "text/csv":
            data_list = parse_csv_to_json(file_content)
            payloads = [map_csv_to_student_payload(item) for item in data_list]
        elif file.content_type == "application/json":
            data_list = json.loads(file_content)
            if not isinstance(data_list, list):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON file must contain a list of student objects.")
            payloads = [StudentIngestionPayload(**item) for item in data_list]
        elif file.content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            df = pd.read_excel(file.file)
            students_data = df.to_dict(orient="records")
            response = supabase.from_("students").upsert(students_data, on_conflict="student_id").execute()

            if response.data:
                processed_count += len(response.data)
            elif response.error:
                errors.append(f"Supabase error: {response.error.message}")
            else:
                errors.append("No data processed, check Excel content.")
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type. Only CSV, JSON, and Excel are allowed.")

        for payload in payloads:
            try:
                student_info = payload.student_profile.student_info.model_dump()
                courses = [c.model_dump() for c in payload.student_profile.courses]
                gpa_history = [g.model_dump() for g in payload.student_profile.gpa_history]
                attendance = payload.student_profile.attendance.model_dump() if payload.student_profile.attendance else None
                extracurricular_activities = [e.model_dump() for e in payload.student_profile.extracurricular_activities]
                iep_504_plan_information = payload.student_profile.iep_504_plan_information.model_dump() if payload.student_profile.iep_504_plan_information else None
                college_counseling_milestones = [c.model_dump() for c in payload.student_profile.college_counseling_milestones]

                narrative_teacher_comments = [c.model_dump() for c in payload.unstructured_data.narrative_teacher_comments]
                advisory_counselor_notes = [n.model_dump() for n in payload.unstructured_data.advisory_counselor_notes]
                behavior_social_emotional_notes = [n.model_dump() for n in payload.unstructured_data.behavior_social_emotional_notes]

                soft_skill_inferences = [s.model_dump() for s in payload.soft_skill_inferences.soft_skill_inferences]

                response = supabase.from_("students").insert({
                    "full_name": student_info["full_name"],
                    "grade_level": student_info["grade_level"],
                    "academic_year": student_info["academic_year"],
                    "status": student_info["status"],
                    "assessment_breakdown_by_type": student_info["assessment_breakdown_by_type"],
                    "courses": courses,
                    "gpa_history": gpa_history,
                    "attendance": attendance,
                    "extracurricular_activities": extracurricular_activities,
                    "iep_504_plan_information": iep_504_plan_information,
                    "college_counseling_milestones": college_counseling_milestones,
                    "narrative_teacher_comments": narrative_teacher_comments,
                    "advisory_counselor_notes": advisory_counselor_notes,
                    "behavior_social_emotional_notes": behavior_social_emotional_notes,
                    "soft_skill_inferences": soft_skill_inferences
                }).execute()

                if response.data:
                    processed_count += 1
                else:
                    failed_count += 1
                    errors.append(f"Failed to ingest {payload.student_profile.student_info.full_name}: {response.error.message if response.error else 'Unknown error'}")
            except Exception as e:
                failed_count += 1
                errors.append(f"Error processing a student record: {str(e)}")

    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON format.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred during file processing: {str(e)}")

    return {
        "message": f"Bulk upload complete. Successfully processed {processed_count} records, failed {failed_count} records.",
        "details": errors
    }

@router.post("/upload/csv", status_code=status.HTTP_201_CREATED)
async def upload_students_csv(
    file: UploadFile = File(...),
    supabase: Client = Depends(get_supabase_client),
    current_user: dict = Depends(get_current_admin_user) # Only admins can upload
):
    """
    Upload student profiles from a CSV file.
    Requires admin authentication.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV files are allowed.")

    try:
        contents = await file.read()
        df = pd.read_csv(StringIO(contents.decode('utf-8')))

        # Convert DataFrame to a list of dictionaries, ensuring types match Pydantic model
        students_data = df.to_dict(orient="records")
        
        # Validate each record against the StudentProfile Pydantic model
        validated_students = []
        for student_dict in students_data:
            try:
                # Ensure all required fields are present, even if empty in CSV
                # Pydantic will handle type coercion where possible
                validated_students.append(StudentProfileData(**student_dict))
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Validation error in CSV data: {e} for row: {student_dict}"
                )

        # Insert data into Supabase
        # Supabase client's insert method expects a list of dictionaries
        insert_payload = [student.dict() for student in validated_students]
        response = supabase.from_("students").insert(insert_payload).execute()

        if response.data:
            return {"message": f"Successfully uploaded {len(response.data)} student profiles from CSV."}
        elif response.error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=response.error.message)
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unknown error during CSV upload.")

    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV file is empty.")
    except pd.errors.ParserError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not parse CSV file. Check format.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")

@router.post("/upload/json", status_code=status.HTTP_201_CREATED)
async def upload_students_json(
    students: List[StudentProfileData],
    supabase: Client = Depends(get_supabase_client),
    current_user: dict = Depends(get_current_admin_user) # Only admins can upload
):
    """
    Upload student profiles from a JSON array.
    Requires admin authentication.
    """
    try:
        # Pydantic already validates the incoming list of StudentProfile objects
        insert_payload = [student.dict() for student in students]
        response = supabase.from_("students").insert(insert_payload).execute()

        if response.data:
            return {"message": f"Successfully uploaded {len(response.data)} student profiles from JSON."}
        elif response.error:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=response.error.message)
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unknown error during JSON upload.")

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred: {str(e)}")

def upload_students_from_excel(file_path: str):
    """
    Reads student data from an Excel file and uploads it to Supabase.
    Assumes the Excel file has columns matching your Supabase 'students' table.
    """
    try:
        df = pd.read_excel(file_path)
        # Convert DataFrame to a list of dictionaries (JSON records)
        students_data = df.to_dict(orient="records")

        # Perform bulk upsert (insert or update) into Supabase
        # Assuming 'student_id' is the unique identifier for upsert
        response = supabase.from_("students").upsert(students_data, on_conflict="student_id").execute()

        if response.data:
            print(f"Successfully processed {len(response.data)} student records.")
        elif response.error:
            print(f"Supabase error: {response.error.message}")
        else:
            print("No data processed, check Excel content.")

    except Exception as e:
        print(f"Failed to process Excel file: {str(e)}")

def upload_students_from_dataframe(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Uploads student data from a pandas DataFrame to Supabase.
    Assumes DataFrame columns map directly to Supabase table columns,
    with complex types (JSONB) handled as JSON strings.
    """
    uploaded_students = []
    for index, row in df.iterrows():
        student_data = row.to_dict()

        # Convert complex fields to JSON strings if they are dicts/lists
        for key, value in student_data.items():
            if isinstance(value, (dict, list)):
                student_data[key] = json.dumps(value)
            elif pd.isna(value): # Handle NaN values from pandas
                student_data[key] = None

        # Ensure student_id is present and unique (Supabase handles uniqueness if it's primary key)
        if 'student_id' not in student_data or student_data['student_id'] is None:
            print(f"Skipping row {index}: 'student_id' is missing or null.")
            continue

        try:
            # Attempt to insert the student data
            response = supabase.from_("students").insert([student_data]).execute()
            if response.data:
                uploaded_students.append(response.data[0])
            elif response.error:
                print(f"Error uploading student {student_data.get('student_id')}: {response.error.message}")
        except Exception as e:
            print(f"An unexpected error occurred for student {student_data.get('student_id')}: {e}")
    return uploaded_students

def process_csv_upload(file_path: str) -> List[Dict[str, Any]]:
    """Reads a CSV file and uploads student data."""
    df = pd.read_csv(file_path)
    return upload_students_from_dataframe(df)

def process_json_upload(file_path: str) -> List[Dict[str, Any]]:
    """Reads a JSON file and uploads student data."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    return upload_students_from_dataframe(df)

# Path to your dummy CSV file
CSV_FILE_PATH = "dummy_students.csv" # Create a dummy_students.csv in the same directory

# FastAPI backend URL
BACKEND_URL = os.getenv("NEXT_PUBLIC_BACKEND_URL", "http://localhost:8000") # Use the env var or default

# You would typically get a token after a successful login
# For testing, you might manually generate one or use a test user's token
# IMPORTANT: In a real application, do not hardcode tokens.
# This is a placeholder for demonstration.
# You need to replace 'YOUR_ADMIN_JWT_TOKEN' with an actual JWT token for an admin user.
# You can get this by logging in as an admin via the frontend or generating one manually for testing.
ADMIN_JWT_TOKEN = "YOUR_ADMIN_JWT_TOKEN" 

def create_dummy_csv(file_path):
    """Creates a dummy CSV file for testing."""
    content = """student_id,first_name,last_name,date_of_birth,gender,email,phone_number,address,enrollment_date,major,gpa,academic_standing,advisor_id,enrollment_status,financial_aid_status,scholarship_amount
S001,Alice,Smith,2000-01-15,Female,alice.s@example.com,111-222-3333,123 Main St,2018-09-01,Computer Science,3.8,Good Standing,Dr. Lee,Enrolled,Eligible,5000.00
S002,Bob,Johnson,1999-05-20,Male,bob.j@example.com,444-555-6666,456 Oak Ave,2017-09-01,Mathematics,3.5,Probation,Prof. Green,Enrolled,Not Eligible,0.00
S003,Charlie,Brown,2001-11-10,Non-binary,charlie.b@example.com,777-888-9999,789 Pine Ln,2019-09-01,Physics,3.9,Good Standing,Dr. White,Enrolled,Eligible,7500.00
"""
    with open(file_path, "w") as f:
        f.write(content)
    print(f"Dummy CSV created at {file_path}")

def upload_csv(file_path: str, token: str):
    """Uploads a CSV file to the FastAPI backend."""
    url = f"{BACKEND_URL}/api/upload-students-csv"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "text/csv")}
            response = requests.post(url, headers=headers, files=files)
        
        response.raise_for_status() # Raise an exception for HTTP errors
        print(f"Upload successful: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Upload failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response content: {e.response.text}")

if __name__ == "__main__":
    if not os.path.exists(CSV_FILE_PATH):
        create_dummy_csv(CSV_FILE_PATH)
    
    if ADMIN_JWT_TOKEN == "YOUR_ADMIN_JWT_TOKEN":
        print("WARNING: Please replace 'YOUR_ADMIN_JWT_TOKEN' in upload_students.py with an actual admin JWT token.")
        print("You can obtain this by logging in as an admin user through the frontend and inspecting network requests,")
        print("or by manually generating a token for testing purposes.")
    else:
        print(f"Attempting to upload {CSV_FILE_PATH} to {BACKEND_URL}...")
        upload_csv(CSV_FILE_PATH, ADMIN_JWT_TOKEN)
