from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import date
from supabase import Client
from supabase_client import get_supabase_client, supabase_client
from auth_utils import get_current_teacher_or_admin_user, get_current_admin_user
import pandas as pd
import io
from flask import request, jsonify
from supabase_client import supabase
from auth_utils import admin_required

router = APIRouter()

# Pydantic Models for Student Data
class StudentProfile(BaseModel):
    student_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    email: EmailStr
    phone_number: str
    address: str
    enrollment_date: date
    major: str
    gpa: float
    academic_standing: str
    advisor: str
    enrollment_status: str
    financial_aid_status: str
    scholarship_amount: float

class Course(BaseModel):
    course_id: str
    student_id: str
    course_name: str
    credits: float = Field(..., ge=0.5)
    grade: str
    semester: str
    year: int = Field(..., ge=1900)

class Attendance(BaseModel):
    attendance_id: str
    student_id: str
    date: date
    status: str # e.g., 'Present', 'Absent', 'Excused'
    course_id: Optional[str] = None

class FinancialAid(BaseModel):
    financial_aid_id: str
    student_id: str
    aid_type: str
    amount: float
    date_awarded: date

class StudentData(BaseModel):
    profile: StudentProfile
    courses: List[Course] = []
    attendance: List[Attendance] = []
    financial_aid: List[FinancialAid] = []

class StudentInfoCore(BaseModel):
    student_id: Optional[str] = None
    first_name: str
    last_name: str
    date_of_birth: Optional[str] = None
    gender: str
    email: str
    phone_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    enrollment_date: str
    major: Optional[str] = None
    gpa: Optional[float] = Field(None, ge=0.0, le=4.0)
    academic_standing: Optional[str] = None
    advisor_id: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    medical_conditions: Optional[str] = None
    notes: Optional[str] = None
    full_name: str
    grade_level: int = Field(..., ge=0)
    academic_year: str
    status: Optional[str] = "None"
    assessment_breakdown_by_type: List[Dict[str, Any]] = []
    advisor: Optional[str] = None
    enrollment_status: Optional[str] = None
    financial_aid_status: Optional[str] = None
    scholarship_amount: Optional[float] = Field(None, ge=0.0)

class AssessmentBreakdown(BaseModel):
    type: str
    performance_metric: float = Field(..., ge=0)
    description: Optional[str] = None

class GPAHistoryEntry(BaseModel):
    academic_year: str
    term: str
    gpa_value: float = Field(..., ge=0.0, le=4.0)

class Absences(BaseModel):
    excused: int = Field(..., ge=0)
    unexcused: int = Field(..., ge=0)

class Tardies(BaseModel):
    count: int = Field(..., ge=0)
    dates: List[str] = []

class AttendanceData(BaseModel):
    attendance_id: str
    student_id: str
    date: str
    status: str # "Present", "Absent", "Tardy"
    course_id: Optional[str] = None

class ExtracurricularActivity(BaseModel):
    activity_name: str
    role_title: Optional[str] = None
    start_date: str
    end_date: Optional[str] = None
    is_ongoing: bool = False
    is_leadership: bool = False

class IEP504Plan(BaseModel):
    has_plan: bool
    plan_type: Optional[str] = None
    accommodations: List[str] = []
    last_updated_date: Optional[str] = None

class CollegeMilestone(BaseModel):
    milestone_name: str
    status: str
    date: str

class NarrativeComment(BaseModel):
    subject: str
    teacher: str
    term: str
    comment_text: str

class StaffNote(BaseModel):
    staff_name: str
    role: Optional[str] = None
    date: str
    note_text: str

class SoftSkillInference(BaseModel):
    skill_name: str
    source_phrase: str
    explanation: str
    confidence_level: str

class StudentProfileData(BaseModel):
    student_info: StudentInfoCore
    courses: List[Course] = []
    assessment_breakdown_by_type: List[AssessmentBreakdown] = []
    gpa_history: List[GPAHistoryEntry] = []
    attendance: Optional[AttendanceData] = None
    extracurricular_activities: List[ExtracurricularActivity] = []
    iep_504_plan_information: Optional[IEP504Plan] = None
    college_counseling_milestones: List[CollegeMilestone] = []

class UnstructuredData(BaseModel):
    narrative_teacher_comments: List[NarrativeComment] = []
    advisory_counselor_notes: List[StaffNote] = []
    behavior_social_emotional_notes: List[StaffNote] = []

class StudentIngestionPayload(BaseModel):
    student_profile: StudentProfileData
    unstructured_data: UnstructuredData
    soft_skill_inferences: List[SoftSkillInference] = []

class StudentUpdatePayload(BaseModel):
    # Allow partial updates for all fields
    student_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    enrollment_date: Optional[str] = None
    major: Optional[str] = None
    gpa: Optional[float] = Field(None, ge=0.0, le=4.0)
    academic_standing: Optional[str] = None
    advisor_id: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    medical_conditions: Optional[str] = None
    notes: Optional[str] = None
    full_name: Optional[str] = None
    grade_level: Optional[int] = Field(None, ge=0)
    academic_year: Optional[str] = None
    status: Optional[str] = None
    assessment_breakdown_by_type: Optional[List[Dict[str, Any]]] = None
    advisor: Optional[str] = None
    enrollment_status: Optional[str] = None
    financial_aid_status: Optional[str] = None
    scholarship_amount: Optional[float] = Field(None, ge=0.0)
    courses: Optional[List[Course]] = None
    assessment_breakdown_by_type: Optional[List[AssessmentBreakdown]] = None
    gpa_history: Optional[List[GPAHistoryEntry]] = None
    attendance: Optional[AttendanceData] = None
    extracurricular_activities: Optional[List[ExtracurricularActivity]] = None
    iep_504_plan_information: Optional[IEP504Plan] = None
    college_counseling_milestones: Optional[List[CollegeMilestone]] = None
    narrative_teacher_comments: Optional[List[NarrativeComment]] = None
    advisory_counselor_notes: Optional[List[StaffNote]] = None
    behavior_social_emotional_notes: Optional[List[StaffNote]] = None
    soft_skill_inferences: Optional[List[SoftSkillInference]] = None

class StudentSummary(BaseModel):
    id: str
    full_name: str
    grade_level: int
    academic_year: str
    status: str
    has_504_plan: bool = False

@router.post("/ingest-student-data")
async def ingest_student_data(
    data: StudentData,
    supabase: Client = Depends(get_supabase_client)
):
    """
    Ingests comprehensive student data including profile, courses, attendance, and financial aid.
    """
    try:
        # Insert student profile
        profile_response = supabase.table("students").insert(data.profile.model_dump()).execute()
        if profile_response.data is None:
            raise HTTPException(status_code=500, detail=f"Failed to insert student profile: {profile_response.error.message}")

        # Insert courses
        if data.courses:
            course_data = [c.model_dump() for c in data.courses]
            course_response = supabase.table("courses").insert(course_data).execute()
            if course_response.data is None:
                raise HTTPException(status_code=500, detail=f"Failed to insert courses: {course_response.error.message}")

        # Insert attendance
        if data.attendance:
            attendance_data = [a.model_dump() for a in data.attendance]
            attendance_response = supabase.table("attendance").insert(attendance_data).execute()
            if attendance_response.data is None:
                raise HTTPException(status_code=500, detail=f"Failed to insert attendance: {attendance_response.error.message}")

        # Insert financial aid
        if data.financial_aid:
            financial_aid_data = [f.model_dump() for f in data.financial_aid]
            financial_aid_response = supabase.table("financial_aid").insert(financial_aid_data).execute()
            if financial_aid_response.data is None:
                raise HTTPException(status_code=500, detail=f"Failed to insert financial aid: {financial_aid_response.error.message}")

        return {"message": "Student data ingested successfully", "student_id": data.profile.student_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload-students/", summary="Upload student data from CSV/Excel", tags=["Admin"])
async def upload_students_data(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_admin_user)
):
    """
    Uploads student data from a CSV or Excel file.
    The file should contain columns: first_name, last_name, date_of_birth, enrollment_date, major, email, gpa, semester, year.
    """
    try:
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(contents))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type. Please upload a CSV or Excel file.")

        # Validate required columns
        required_columns = ["first_name", "last_name", "date_of_birth", "enrollment_date", "major", "email", "gpa", "semester", "year"]
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(status_code=400, detail=f"Missing required columns. Ensure all of {required_columns} are present.")

        students_to_insert = []
        gpa_history_to_insert = []

        for index, row in df.iterrows():
            student_email = str(row["email"]).lower()
            
            # Check if student already exists by email
            existing_student_response = supabase.table('students').select('id').eq('email', student_email).limit(1).execute()
            existing_student_id = None
            if existing_student_response.data:
                existing_student_id = existing_student_response.data[0]['id']

            student_data = {
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "date_of_birth": pd.to_datetime(row["date_of_birth"]).date().isoformat() if pd.notna(row["date_of_birth"]) else None,
                "enrollment_date": pd.to_datetime(row["enrollment_date"]).date().isoformat() if pd.notna(row["enrollment_date"]) else None,
                "major": row["major"],
                "email": student_email
            }

            if existing_student_id:
                # Update existing student
                update_response = supabase.table('students').update(student_data).eq('id', existing_student_id).execute()
                if update_response.data:
                    print(f"Updated existing student: {student_email}")
                    current_student_id = existing_student_id
                else:
                    print(f"Failed to update student {student_email}: {update_response.error}")
                    continue # Skip GPA insertion if student update failed
            else:
                # Insert new student
                insert_response = supabase.table('students').insert(student_data).execute()
                if insert_response.data:
                    current_student_id = insert_response.data[0]['id']
                    print(f"Inserted new student: {student_email}")
                else:
                    print(f"Failed to insert new student {student_email}: {insert_response.error}")
                    continue # Skip GPA insertion if student insertion failed

            # Prepare GPA history data
            if pd.notna(row["gpa"]) and pd.notna(row["semester"]) and pd.notna(row["year"]):
                gpa_data = {
                    "student_id": current_student_id,
                    "gpa": float(row["gpa"]),
                    "semester": str(row["semester"]),
                    "year": int(row["year"])
                }
                gpa_history_to_insert.append(gpa_data)

        # Batch insert GPA history
        if gpa_history_to_insert:
            gpa_insert_response = supabase.table('gpa_history').insert(gpa_history_to_insert).execute()
            if gpa_insert_response.data:
                print(f"Inserted {len(gpa_insert_response.data)} GPA records.")
            else:
                print(f"Failed to insert GPA history: {gpa_insert_response.error}")

        return {"message": "Student data uploaded and processed successfully!"}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred during file processing: {e}")

@router.post("/students", status_code=status.HTTP_201_CREATED)
async def create_student_profile(
    payload: StudentIngestionPayload,
    current_user: dict = Depends(get_current_teacher_or_admin_user)
):
    """
    Ingests a complete student profile, including structured and unstructured data.
    Requires 'admin', 'teacher', or 'counselor' role.
    """
    try:
        # Insert student_info into the 'students' table
        student_info_data = payload.student_profile.student_info.model_dump(exclude_unset=True)
        response = supabase_client.from("students").insert(student_info_data).execute()
        if response.data:
            student_id = response.data[0]['student_id']
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create student info.")

        # Handle nested data (courses, GPA history, etc.)
        # For simplicity, this example assumes direct insertion.
        # In a real app, you'd link these to the student_id and handle updates/deletes.

        # Example for courses (assuming courses table exists and has student_id foreign key)
        if payload.student_profile.courses:
            courses_data = [c.model_dump() for c in payload.student_profile.courses]
            for course in courses_data:
                course['student_id'] = student_id # Link to the newly created student
            supabase_client.from("courses").insert(courses_data).execute()

        # Similarly for other lists: assessment_breakdown_by_type, gpa_history, extracurricular_activities, college_counseling_milestones
        # And for unstructured data: narrative_teacher_comments, advisory_counselor_notes, behavior_social_emotional_notes
        # And soft_skill_inferences

        return {"message": "Student profile created successfully", "student_id": student_id}
    except Exception as e:
        print(f"Error creating student profile: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/students", response_model=List[StudentSummary])
async def get_all_students(
    current_user: dict = Depends(get_current_teacher_or_admin_user)
):
    """
    Retrieves a summary list of all students.
    Requires 'admin', 'teacher', or 'counselor' role.
    """
    try:
        response = supabase_client.from("students").select(
            "student_id:id, full_name, grade_level, academic_year, status, iep_504_plan_information"
        ).execute()

        students_data = []
        for student in response.data:
            has_504_plan = student.get('iep_504_plan_information', {}).get('has_plan', False) if student.get('iep_504_plan_information') else False
            students_data.append(StudentSummary(
                id=student['student_id'],
                full_name=student['full_name'],
                grade_level=student['grade_level'],
                academic_year=student['academic_year'],
                status=student['status'],
                has_504_plan=has_504_plan
            ))
        return students_data
    except Exception as e:
        print(f"Error fetching students: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/students/{student_id}", response_model=StudentIngestionPayload)
async def get_student_profile(
    student_id: str,
    current_user: dict = Depends(get_current_teacher_or_admin_user)
):
    """
    Retrieves a complete student profile by ID.
    Requires 'admin', 'teacher', or 'counselor' role.
    """
    try:
        # Fetch student info
        student_response = supabase_client.from("students").select("*").eq("student_id", student_id).single().execute()
        student_info = student_response.data
        if not student_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

        # Fetch related data (example for courses)
        courses_response = supabase_client.from("courses").select("*").eq("student_id", student_id).execute()
        courses = courses_response.data or []

        # Construct the full payload
        student_profile_data = StudentProfileData(
            student_info=StudentInfoCore(**student_info),
            courses=[Course(**c) for c in courses],
            # Add other nested data here
        )
        
        # Assuming unstructured_data and soft_skill_inferences are stored directly or fetched similarly
        unstructured_data = UnstructuredData() # Placeholder
        soft_skill_inferences = [] # Placeholder

        return StudentIngestionPayload(
            student_profile=student_profile_data,
            unstructured_data=unstructured_data,
            soft_skill_inferences=soft_skill_inferences
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error fetching student profile: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.patch("/students/{student_id}", status_code=status.HTTP_200_OK)
async def update_student_profile(
    student_id: str,
    payload: StudentUpdatePayload,
    current_user: dict = Depends(get_current_teacher_or_admin_user)
):
    """
    Updates parts of a student's profile by ID.
    Requires 'admin', 'teacher', or 'counselor' role.
    """
    try:
        # Filter out unset fields to allow partial updates
        update_data = payload.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No data provided for update.")

        # Separate student_info fields from nested list fields
        student_info_updates = {k: v for k, v in update_data.items() if k in StudentInfoCore.model_fields}
        nested_list_updates = {k: v for k, v in update_data.items() if k not in StudentInfoCore.model_fields}

        if student_info_updates:
            response = supabase_client.from("students").update(student_info_updates).eq("student_id", student_id).execute()
            if not response.data:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found or no changes applied.")

        # Handle updates for nested lists (e.g., courses, gpa_history)
        # This is more complex as it might involve adding, updating, or deleting items in the lists.
        # For a PATCH, you might typically replace the entire list or have specific endpoints for list items.
        # For simplicity, this example will just show how you might handle one nested list (e.g., courses)
        # by replacing it entirely if provided. In a real app, you'd need more granular logic.

        if "courses" in nested_list_updates and nested_list_updates["courses"] is not None:
            # Delete existing courses for this student and insert new ones
            supabase_client.from("courses").delete().eq("student_id", student_id).execute()
            new_courses_data = [c.model_dump() for c in nested_list_updates["courses"]]
            for course in new_courses_data:
                course['student_id'] = student_id
            supabase_client.from("courses").insert(new_courses_data).execute()
        
        # Repeat for other nested lists as needed

        return {"message": "Student profile updated successfully", "student_id": student_id}
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error updating student profile: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student_profile(
    student_id: str,
    current_user: dict = Depends(get_current_admin_user) # Only admin can delete
):
    """
    Deletes a student profile by ID.
    Requires 'admin' role.
    """
    try:
        # Delete related data first to avoid foreign key constraints
        # (e.g., courses, attendance, notes, etc.)
        supabase_client.from("courses").delete().eq("student_id", student_id).execute()
        # ... delete from other related tables ...

        response = supabase_client.from("students").delete().eq("student_id", student_id).execute()
        if not response.data: # Supabase delete returns empty data on success
            # Check if the student actually existed before deletion
            check_response = supabase_client.from("students").select("student_id").eq("student_id", student_id).execute()
            if not check_response.data:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
        return
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error deleting student profile: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

def register_student_ingestion_routes(app):
    @app.route('/api/students/upload', methods=['POST'])
    @admin_required
    def upload_students():
        if 'file' not in request.files:
            return jsonify({"error": "No file part"}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        if file and file.filename.endswith(('.xlsx', '.xls')):
            try:
                df = pd.read_excel(file)
                # Process DataFrame and insert into Supabase
                # This is a simplified example. You'd need robust validation and error handling.
                students_to_insert = []
                gpa_history_to_insert = []

                for index, row in df.iterrows():
                    student_data = {
                        "first_name": row.get("First Name"),
                        "last_name": row.get("Last Name"),
                        "date_of_birth": str(row.get("Date of Birth").date()) if pd.notna(row.get("Date of Birth")) else None,
                        "gender": row.get("Gender"),
                        "email": row.get("Email"),
                        "phone_number": row.get("Phone Number"),
                        "address": row.get("Address"),
                        "city": row.get("City"),
                        "state": row.get("State"),
                        "zip_code": row.get("Zip Code"),
                        "enrollment_date": str(row.get("Enrollment Date").date()) if pd.notna(row.get("Enrollment Date")) else None,
                        "major": row.get("Major"),
                        "current_gpa": row.get("Current GPA"),
                        "academic_standing": row.get("Academic Standing"),
                        "advisor": row.get("Advisor"),
                        "expected_graduation_date": str(row.get("Expected Graduation Date").date()) if pd.notna(row.get("Expected Graduation Date")) else None,
                        "profile_picture_url": row.get("Profile Picture URL"),
                        "user_id": row.get("User ID") # Assuming User ID is provided in the CSV for linking
                    }
                    students_to_insert.append(student_data)

                    # Assuming GPA history is also in the same row or needs to be derived
                    if pd.notna(row.get("Current GPA")):
                        gpa_history_to_insert.append({
                            "student_id": None, # Will be updated after student insertion
                            "gpa": row.get("Current GPA"),
                            "date_recorded": str(pd.Timestamp.now().date())
                        })

                # Insert students
                student_response = supabase.table('students').insert(students_to_insert).execute()
                if student_response.data:
                    # Link GPA history to newly inserted students
                    for i, student in enumerate(student_response.data):
                        if i < len(gpa_history_to_insert):
                            gpa_history_to_insert[i]["student_id"] = student["id"]
                    
                    if gpa_history_to_insert:
                        supabase.table('gpa_history').insert(gpa_history_to_insert).execute()

                return jsonify({"message": "Students uploaded successfully", "data": student_response.data}), 200
            except Exception as e:
                print(f"Error processing file: {e}")
                return jsonify({"error": f"Error processing file: {e}"}), 500
        else:
            return jsonify({"error": "Invalid file type. Please upload an Excel file (.xlsx, .xls)."}), 400

    @app.route('/api/students', methods=['GET'])
    def get_students():
        try:
            response = supabase.table('students').select('*').execute()
            return jsonify(response.data), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/students/<string:student_id>', methods=['GET'])
    def get_student_by_id(student_id):
        try:
            response = supabase.table('students').select('*').eq('id', student_id).single().execute()
            if response.data:
                return jsonify(response.data), 200
            return jsonify({"error": "Student not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/students/<string:student_id>', methods=['PATCH'])
    @admin_required # Only admins can update student data for now
    def update_student(student_id):
        try:
            data = request.json
            if not data:
                return jsonify({"error": "No data provided for update"}), 400

            response = supabase.table('students').update(data).eq('id', student_id).execute()
            if response.data:
                return jsonify({"message": "Student updated successfully", "data": response.data[0]}), 200
            return jsonify({"error": "Student not found or no changes made"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/students/<string:student_id>', methods=['DELETE'])
    @admin_required
    def delete_student(student_id):
        try:
            response = supabase.table('students').delete().eq('id', student_id).execute()
            if response.data:
                return jsonify({"message": "Student deleted successfully"}), 200
            return jsonify({"error": "Student not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/gpa_history/<string:student_id>', methods=['GET'])
    def get_gpa_history(student_id):
        try:
            response = supabase.table('gpa_history').select('*').eq('student_id', student_id).order('date_recorded', desc=False).execute()
            return jsonify(response.data), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/api/users', methods=['GET'])
    @admin_required
    def get_users():
        try:
            # Fetch users from Supabase auth.users()
            # Note: This requires the service role key and might have rate limits for large numbers of users
            users_response = supabase.auth.admin.list_users()
            
            # Fetch roles from your 'roles' table
            roles_response = supabase.table('roles').select('*').execute()
            roles_map = {role['id']: role['name'] for role in roles_response.data}

            # Fetch user_roles to link users to their roles
            user_roles_response = supabase.table('user_roles').select('*').execute()
            user_roles_map = {}
            for ur in user_roles_response.data:
                if ur['user_id'] not in user_roles_map:
                    user_roles_map[ur['user_id']] = []
                user_roles_map[ur['user_id']].append(roles_map.get(ur['role_id'], 'unknown'))

            # Combine user data with roles
            users_with_roles = []
            for user in users_response.data.users:
                users_with_roles.append({
                    "id": user.id,
                    "email": user.email,
                    "created_at": user.created_at,
                    "last_sign_in_at": user.last_sign_in_at,
                    "roles": user_roles_map.get(user.id, ['student']) # Default to student if no explicit role
                })
            
            return jsonify(users_with_roles), 200
        except Exception as e:
            print(f"Error fetching users: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/api/users/<string:user_id>/roles', methods=['PATCH'])
    @admin_required
    def update_user_roles(user_id):
        try:
            data = request.json
            new_roles = data.get('roles', [])

            # Fetch existing roles from the 'roles' table
            roles_response = supabase.table('roles').select('*').execute()
            valid_role_ids = {role['name']: role['id'] for role in roles_response.data}

            # Delete existing user roles
            supabase.table('user_roles').delete().eq('user_id', user_id).execute()

            # Insert new roles
            roles_to_insert = []
            for role_name in new_roles:
                role_id = valid_role_ids.get(role_name)
                if role_id:
                    roles_to_insert.append({'user_id': user_id, 'role_id': role_id})
            
            if roles_to_insert:
                supabase.table('user_roles').insert(roles_to_insert).execute()

            return jsonify({"message": f"Roles for user {user_id} updated successfully"}), 200
        except Exception as e:
            print(f"Error updating user roles: {e}")
            return jsonify({"error": str(e)}), 500
