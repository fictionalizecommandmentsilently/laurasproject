from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from supabase import Client
from supabase_client import get_supabase_client, supabase_client
import pandas as pd
import io
from datetime import date
from pydantic import BaseModel, EmailStr
from student_ingestion_route import StudentIngestionPayload, StudentProfileData, StudentInfoCore, Course, GPAHistoryEntry, ExtracurricularActivity, CollegeMilestone, NarrativeComment, StaffNote, SoftSkillInference, UnstructuredData, AssessmentBreakdown, AttendanceData, IEP504Plan
from typing import List, Dict, Any, Optional
from auth_utils import get_current_admin_user
import os
from dotenv import load_dotenv

# Load environment variables from .env file if running locally
load_dotenv()

def get_supabase_client() -> Client:
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Use service role key for backend
    if not url or not key:
        raise ValueError("Supabase URL and Service Role Key must be set in environment variables.")
    return create_client(url, key)

supabase: Client = get_supabase_client()

router = APIRouter()

class StudentProfileUpload(BaseModel):
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

def parse_csv_to_student_payloads(contents: bytes) -> List[StudentIngestionPayload]:
    df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
    payloads: List[StudentIngestionPayload] = []

    for index, row in df.iterrows():
        # Basic Student Info
        student_info = StudentInfoCore(
            first_name=row['first_name'],
            last_name=row['last_name'],
            full_name=f"{row['first_name']} {row['last_name']}",
            email=row['email'],
            enrollment_date=row['enrollment_date'],
            grade_level=int(row['grade_level']),
            academic_year=row['academic_year'],
            gender=row.get('gender', 'Unknown'),
            phone_number=row.get('phone_number'),
            address=row.get('address'),
            city=row.get('city'),
            state=row.get('state'),
            zip_code=row.get('zip_code'),
            date_of_birth=row.get('date_of_birth'),
            major=row.get('major'),
            gpa=float(row['gpa']) if pd.notna(row.get('gpa')) else None,
            academic_standing=row.get('academic_standing'),
            advisor_id=row.get('advisor_id'),
            emergency_contact_name=row.get('emergency_contact_name'),
            emergency_contact_phone=row.get('emergency_contact_phone'),
            medical_conditions=row.get('medical_conditions'),
            notes=row.get('notes'),
            status=row.get('status', 'None'),
            advisor=row.get('advisor'),
            enrollment_status=row.get('enrollment_status'),
            financial_aid_status=row.get('financial_aid_status'),
            scholarship_amount=float(row['scholarship_amount']) if pd.notna(row.get('scholarship_amount')) else None,
            assessment_breakdown_by_type=[] # Will be populated below if available
        )

        # Nested data (assuming JSON strings in CSV or separate columns)
        courses = []
        if 'courses' in row and pd.notna(row['courses']):
            try:
                courses_data = eval(row['courses']) # Use ast.literal_eval in production for safety
                for c in courses_data:
                    courses.append(Course(**c))
            except:
                pass # Handle parsing errors

        gpa_history = []
        if 'gpa_history' in row and pd.notna(row['gpa_history']):
            try:
                gpa_history_data = eval(row['gpa_history'])
                for gpa_entry in gpa_history_data:
                    gpa_history.append(GPAHistoryEntry(**gpa_entry))
            except:
                pass

        extracurricular_activities = []
        if 'extracurricular_activities' in row and pd.notna(row['extracurricular_activities']):
            try:
                activities_data = eval(row['extracurricular_activities'])
                for activity in activities_data:
                    extracurricular_activities.append(ExtracurricularActivity(**activity))
            except:
                pass

        college_counseling_milestones = []
        if 'college_counseling_milestones' in row and pd.notna(row['college_counseling_milestones']):
            try:
                milestones_data = eval(row['college_counseling_milestones'])
                for milestone in milestones_data:
                    college_counseling_milestones.append(CollegeMilestone(**milestone))
            except:
                pass

        narrative_teacher_comments = []
        if 'narrative_teacher_comments' in row and pd.notna(row['narrative_teacher_comments']):
            try:
                comments_data = eval(row['narrative_teacher_comments'])
                for comment in comments_data:
                    narrative_teacher_comments.append(NarrativeComment(**comment))
            except:
                pass

        advisory_counselor_notes = []
        if 'advisory_counselor_notes' in row and pd.notna(row['advisory_counselor_notes']):
            try:
                notes_data = eval(row['advisory_counselor_notes'])
                for note in notes_data:
                    advisory_counselor_notes.append(StaffNote(**note))
            except:
                pass

        behavior_social_emotional_notes = []
        if 'behavior_social_emotional_notes' in row and pd.notna(row['behavior_social_emotional_notes']):
            try:
                notes_data = eval(row['behavior_social_emotional_notes'])
                for note in notes_data:
                    behavior_social_emotional_notes.append(StaffNote(**note))
            except:
                pass

        soft_skill_inferences = []
        if 'soft_skill_inferences' in row and pd.notna(row['soft_skill_inferences']):
            try:
                inferences_data = eval(row['soft_skill_inferences'])
                for inference in inferences_data:
                    soft_skill_inferences.append(SoftSkillInference(**inference))
            except:
                pass

        assessment_breakdown_by_type = []
        if 'assessment_breakdown_by_type' in row and pd.notna(row['assessment_breakdown_by_type']):
            try:
                breakdown_data = eval(row['assessment_breakdown_by_type'])
                for breakdown in breakdown_data:
                    assessment_breakdown_by_type.append(AssessmentBreakdown(**breakdown))
            except:
                pass

        attendance = None
        if 'attendance' in row and pd.notna(row['attendance']):
            try:
                attendance_data = eval(row['attendance'])
                attendance = AttendanceData(**attendance_data)
            except:
                pass

        iep_504_plan_information = None
        if 'iep_504_plan_information' in row and pd.notna(row['iep_504_plan_information']):
            try:
                iep_data = eval(row['iep_504_plan_information'])
                iep_504_plan_information = IEP504Plan(**iep_data)
            except:
                pass

        student_profile_data = StudentProfileData(
            student_info=student_info,
            courses=courses,
            assessment_breakdown_by_type=assessment_breakdown_by_type,
            gpa_history=gpa_history,
            attendance=attendance,
            extracurricular_activities=extracurricular_activities,
            iep_504_plan_information=iep_504_plan_information,
            college_counseling_milestones=college_counseling_milestones,
        )

        unstructured_data = UnstructuredData(
            narrative_teacher_comments=narrative_teacher_comments,
            advisory_counselor_notes=advisory_counselor_notes,
            behavior_social_emotional_notes=behavior_social_emotional_notes,
        )

        payloads.append(StudentIngestionPayload(
            student_profile=student_profile_data,
            unstructured_data=unstructured_data,
            soft_skill_inferences=soft_skill_inferences,
        ))
    return payloads

def upload_students_to_supabase(payloads: List[StudentIngestionPayload], supabase: Client):
    for payload in payloads:
        try:
            # Insert student_info into the 'students' table
            student_info_data = payload.student_profile.student_info.model_dump(exclude_unset=True)
            response = supabase.from_("students").insert(student_info_data).execute()
            
            if response.data:
                student_id = response.data[0]['student_id']
                print(f"Successfully created student: {student_info_data['full_name']} with ID: {student_id}")

                # Insert related data, linking to the new student_id
                if payload.student_profile.courses:
                    courses_to_insert = [c.model_dump() for c in payload.student_profile.courses]
                    for course in courses_to_insert:
                        course['student_id'] = student_id
                    supabase.from_("courses").insert(courses_to_insert).execute()

                if payload.student_profile.gpa_history:
                    gpa_history_to_insert = [g.model_dump() for g in payload.student_profile.gpa_history]
                    for gpa_entry in gpa_history_to_insert:
                        gpa_entry['student_id'] = student_id
                    supabase.from_("gpa_history").insert(gpa_history_to_insert).execute()

                if payload.student_profile.extracurricular_activities:
                    activities_to_insert = [a.model_dump() for a in payload.student_profile.extracurricular_activities]
                    for activity in activities_to_insert:
                        activity['student_id'] = student_id
                    supabase.from_("extracurricular_activities").insert(activities_to_insert).execute()

                if payload.student_profile.college_counseling_milestones:
                    milestones_to_insert = [m.model_dump() for m in payload.student_profile.college_counseling_milestones]
                    for milestone in milestones_to_insert:
                        milestone['student_id'] = student_id
                    supabase.from_("college_counseling_milestones").insert(milestones_to_insert).execute()

                if payload.unstructured_data.narrative_teacher_comments:
                    comments_to_insert = [c.model_dump() for c in payload.unstructured_data.narrative_teacher_comments]
                    for comment in comments_to_insert:
                        comment['student_id'] = student_id
                    supabase.from_("narrative_teacher_comments").insert(comments_to_insert).execute()

                if payload.unstructured_data.advisory_counselor_notes:
                    notes_to_insert = [n.model_dump() for n in payload.unstructured_data.advisory_counselor_notes]
                    for note in notes_to_insert:
                        note['student_id'] = student_id
                    supabase.from_("advisory_counselor_notes").insert(notes_to_insert).execute()

                if payload.unstructured_data.behavior_social_emotional_notes:
                    notes_to_insert = [n.model_dump() for n in payload.unstructured_data.behavior_social_emotional_notes]
                    for note in notes_to_insert:
                        note['student_id'] = student_id
                    supabase.from_("behavior_social_emotional_notes").insert(notes_to_insert).execute()

                if payload.soft_skill_inferences:
                    inferences_to_insert = [s.model_dump() for s in payload.soft_skill_inferences]
                    for inference in inferences_to_insert:
                        inference['student_id'] = student_id
                    supabase.from_("soft_skill_inferences").insert(inferences_to_insert).execute()

                if payload.student_profile.attendance:
                    attendance_to_insert = payload.student_profile.attendance.model_dump()
                    attendance_to_insert['student_id'] = student_id
                    supabase.from_("attendance").insert(attendance_to_insert).execute()

                if payload.student_profile.iep_504_plan_information:
                    iep_to_insert = payload.student_profile.iep_504_plan_information.model_dump()
                    iep_to_insert['student_id'] = student_id
                    supabase.from_("iep_504_plan_information").insert(iep_to_insert).execute()

                if payload.student_profile.assessment_breakdown_by_type:
                    assessment_to_insert = [a.model_dump() for a in payload.student_profile.assessment_breakdown_by_type]
                    for assessment in assessment_to_insert:
                        assessment['student_id'] = student_id
                    supabase.from_("assessment_breakdown_by_type").insert(assessment_to_insert).execute()

            else:
                print(f"Failed to create student: {student_info_data.get('full_name', 'N/A')}. Response: {response.data}")
        except Exception as e:
            print(f"Error uploading student {payload.student_profile.student_info.get('full_name', 'N/A')}: {e}")

def upload_students_from_excel(file_path):
    try:
        df = pd.read_excel(file_path)

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
                "user_id": row.get("User ID") # Assuming User ID is provided in the Excel for linking
            }
            students_to_insert.append(student_data)

            if pd.notna(row.get("Current GPA")):
                gpa_history_to_insert.append({
                    "student_id": None, # Will be updated after student insertion
                    "gpa": row.get("Current GPA"),
                    "date_recorded": str(pd.Timestamp.now().date())
                })

        # Insert students
        student_response = supabase.table('students').insert(students_to_insert).execute()
        if student_response.data:
            print(f"Inserted {len(student_response.data)} students.")
            # Link GPA history to newly inserted students
            for i, student in enumerate(student_response.data):
                if i < len(gpa_history_to_insert):
                    gpa_history_to_insert[i]["student_id"] = student["id"]
            
            if gpa_history_to_insert:
                gpa_response = supabase.table('gpa_history').insert(gpa_history_to_insert).execute()
                print(f"Inserted {len(gpa_response.data)} GPA history records.")

    except Exception as e:
        print(f"Error uploading students from Excel: {e}")

@router.post("/upload-students-csv-direct")
async def upload_students_csv_direct(
    file: UploadFile = File(...),
    supabase: Client = Depends(get_supabase_client)
):
    """
    Uploads student profiles from a CSV file directly to the 'students' table.
    The CSV must have columns matching the StudentProfileUpload model fields.
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    try:
        contents = await file.read()
        student_payloads = parse_csv_to_student_payloads(contents)
        upload_students_to_supabase(student_payloads, supabase)
        return {"message": f"Successfully uploaded {len(student_payloads)} student profiles."}
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="CSV file is empty.")
    except pd.errors.ParserError:
        raise HTTPException(status_code=400, detail="Could not parse CSV file. Check format.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

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
        raise HTTPException(status_code=500, detail=f"An error occurred during file processing: {e}")

if __name__ == "__main__":
    # Example usage:
    # Make sure you have an 'example_students.xlsx' file in the same directory
    # or provide the full path to your Excel file.
    # excel_file_path = "example_students.xlsx"
    # upload_students_from_excel(excel_file_path)
    print("This script is for local Excel upload. Use the /api/students/upload endpoint for web uploads.")
