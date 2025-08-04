from fastapi import APIRouter, HTTPException, Depends, status, Query, UploadFile, File
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import date
from supabase import Client
from supabase_client import get_supabase_client
from auth_utils import get_current_admin_user, get_current_user_role, decode_access_token
import pandas as pd

router = APIRouter()

# --- Pydantic Models for Request Body Validation (kept consistent with logical structure) ---

class StudentInfoCore(BaseModel):
    full_name: str
    grade_level: int
    academic_year: str
    status: str = "None"

class Course(BaseModel):
    course_id: str
    student_id: str
    course_name: str
    credits: float
    grade: str
    semester: str
    year: int

class AssessmentBreakdown(BaseModel):
    type: str
    performance_metric: float
    description: Optional[str] = None

class GPAHistoryEntry(BaseModel):
    academic_year: str
    term: str
    gpa_value: float

class Absences(BaseModel):
    excused: int
    unexcused: int

class Tardies(BaseModel):
    count: int
    dates: List[str]

class AttendanceData(BaseModel):
    absences: Optional[Absences] = None
    tardies: Optional[Tardies] = None

class ExtracurricularActivity(BaseModel):
    activity_name: str
    role_title: Optional[str] = None
    start_date: str # Use string for date for simplicity with Pydantic and DB
    end_date: Optional[str] = None
    is_ongoing: bool = False
    is_leadership: bool = False

class IEP504Plan(BaseModel):
    has_plan: bool
    plan_type: Optional[str] = None
    accommodations: Optional[List[str]] = None
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

class Attendance(BaseModel):
    attendance_id: str
    student_id: str
    date: str
    status: str # e.g., 'Present', 'Absent', 'Tardy'

class FinancialAid(BaseModel):
    financial_aid_id: str
    student_id: str
    aid_type: str
    amount: float
    date_awarded: str

# Main Structured Data Section of the Student Profile
class StudentProfileData(BaseModel):
    student_info: StudentInfoCore
    courses: List[Course] = Field(default_factory=list)
    assessment_breakdown_by_type: List[AssessmentBreakdown] = Field(default_factory=list)
    gpa_history: List[GPAHistoryEntry] = Field(default_factory=list)
    attendance: Optional[AttendanceData] = None
    extracurricular_activities: List[ExtracurricularActivity] = Field(default_factory=list)
    iep_504_plan_information: Optional[IEP504Plan] = None
    college_counseling_milestones: List[CollegeMilestone] = Field(default_factory=list)

# Unstructured Data Section of the Student Profile
class UnstructuredData(BaseModel):
    narrative_teacher_comments: List[NarrativeComment] = Field(default_factory=list)
    advisory_counselor_notes: List[StaffNote] = Field(default_factory=list)
    behavior_social_emotional_notes: List[StaffNote] = Field(default_factory=list)

# Overall Student Profile Input Payload
class StudentIngestionPayload(BaseModel):
    student_profile: StudentProfileData
    unstructured_data: UnstructuredData = Field(default_factory=lambda: UnstructuredData())
    soft_skill_inferences: List[SoftSkillInference] = Field(default_factory=list)

# Student Summary Model (for /students GET)
class StudentSummary(BaseModel):
    id: str
    full_name: str
    grade_level: int
    academic_year: str
    status: str
    has_504_plan: bool = False # Derived from iep_504_plan_information

# Student Profile Response Model (for /students/{id} GET)
class StudentProfileResponse(BaseModel):
    student_profile: StudentProfileData
    unstructured_data: UnstructuredData
    soft_skill_inferences: List[SoftSkillInference]

# Student Update Payload (for /students/{id} PATCH)
class StudentUpdatePayload(BaseModel):
    full_name: Optional[str] = None
    grade_level: Optional[int] = None
    academic_year: Optional[str] = None
    status: Optional[str] = None
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

# Comment Create Model (for /students/{id}/comments POST)
class CommentCreate(BaseModel):
    subject: str
    teacher: str
    term: str
    comment_text: str

# New Student Profile Model
class StudentProfile(BaseModel):
    student_id: str = Field(..., description="Unique identifier for the student")
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    email: str
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
    # Add other fields as per your schema.sql

# New Student Profile Update Model
class StudentProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None
    enrollment_date: Optional[date] = None
    major: Optional[str] = None
    gpa: Optional[float] = None
    academic_standing: Optional[str] = None
    advisor: Optional[str] = None
    enrollment_status: Optional[str] = None
    financial_aid_status: Optional[str] = None
    scholarship_amount: Optional[float] = None

# --- Helper function to insert a single student profile across normalized tables ---
async def _insert_single_student_profile_normalized(profile: StudentIngestionPayload, supabase_client: Client):
    """
    Helper function to insert a single student profile into normalized tables.
    """
    # 1. Insert into 'students' table first to get the student_id
    student_info = profile.student_profile.student_info.model_dump()
    student_insert_data = {
        "full_name": student_info["full_name"],
        "grade_level": student_info["grade_level"],
        "academic_year": student_info["academic_year"],
        "status": student_info["status"],
    }
    response = supabase_client.from('students').insert(student_insert_data).execute()

    if not response.data:
        raise HTTPException(status_code=500, detail="Failed to insert student record into 'students' table.")
    
    student_id = response.data[0]['id']

    # 2. Insert into related tables, linking with student_id
    # Courses
    if profile.student_profile.courses:
        courses_to_insert = [{"student_id": student_id, **c.model_dump()} for c in profile.student_profile.courses]
        supabase_client.from('courses').insert(courses_to_insert).execute()

    # Assessment Breakdowns
    if profile.student_profile.assessment_breakdown_by_type:
        assessments_to_insert = [{"student_id": student_id, **a.model_dump()} for a in profile.student_profile.assessment_breakdown_by_type]
        supabase_client.from('assessment_breakdowns').insert(assessments_to_insert).execute()

    # GPA History
    if profile.student_profile.gpa_history:
        gpa_history_to_insert = [{"student_id": student_id, **g.model_dump()} for g in profile.student_profile.gpa_history]
        supabase_client.from('gpa_history').insert(gpa_history_to_insert).execute()

    # Attendance
    if profile.student_profile.attendance:
        attendance_data = profile.student_profile.attendance.model_dump()
        supabase_client.from('attendance').insert({
            "student_id": student_id,
            "excused": attendance_data.get("absences", {}).get("excused", 0),
            "unexcused": attendance_data.get("absences", {}).get("unexcused", 0),
            "tardy_count": attendance_data.get("tardies", {}).get("count", 0),
            "tardy_dates": attendance_data.get("tardies", {}).get("dates", [])
        }).execute()

    # Extracurricular Activities
    if profile.student_profile.extracurricular_activities:
        activities_to_insert = [{"student_id": student_id, **a.model_dump()} for a in profile.student_profile.extracurricular_activities]
        supabase_client.from('extracurricular_activities').insert(activities_to_insert).execute()

    # IEP/504 Plan Information
    if profile.student_profile.iep_504_plan_information:
        iep_data = profile.student_profile.iep_504_plan_information.model_dump()
        supabase_client.from('iep_504_plans').insert({
            "student_id": student_id,
            "has_plan": iep_data.get("has_plan", False),
            "plan_type": iep_data.get("plan_type"),
            "accommodations": iep_data.get("accommodations", []),
            "last_updated": iep_data.get("last_updated_date")
        }).execute()

    # College Counseling Milestones
    if profile.student_profile.college_counseling_milestones:
        milestones_to_insert = [{"student_id": student_id, **m.model_dump()} for m in profile.student_profile.college_counseling_milestones]
        supabase_client.from('college_milestones').insert(milestones_to_insert).execute()

    # Narrative Teacher Comments
    if profile.unstructured_data.narrative_teacher_comments:
        comments_to_insert = [{"student_id": student_id, **c.model_dump()} for c in profile.unstructured_data.narrative_teacher_comments]
        supabase_client.from('narrative_comments').insert(comments_to_insert).execute()

    # Advisory/Counselor Notes
    if profile.unstructured_data.advisory_counselor_notes:
        counselor_notes_to_insert = [{"student_id": student_id, **n.model_dump()} for n in profile.unstructured_data.advisory_counselor_notes]
        supabase_client.from('counselor_notes').insert(counselor_notes_to_insert).execute()

    # Behavior/Social Emotional Notes
    if profile.unstructured_data.behavior_social_emotional_notes:
        behavior_notes_to_insert = [{"student_id": student_id, **n.model_dump()} for n in profile.unstructured_data.behavior_social_emotional_notes]
        supabase_client.from('behavior_notes').insert(behavior_notes_to_insert).execute()

    # Soft Skill Inferences
    if profile.soft_skill_inferences:
        soft_skills_to_insert = [{"student_id": student_id, **s.model_dump()} for s in profile.soft_skill_inferences]
        supabase_client.from('soft_skills').insert(soft_skills_to_insert).execute()

    return {"status": "success", "message": "Student profile created successfully", "student_id": str(student_id)}

# --- API Endpoints ---

@router.post("/ingest", status_code=status.HTTP_201_CREATED)
async def ingest_student_data(
    payload: StudentIngestionPayload,
    supabase_client: Client = Depends(get_supabase_client),
    user_role: str = Depends(get_current_admin_user) # Only admins can ingest full profiles
):
    try:
        result = await _insert_single_student_profile_normalized(payload, supabase_client)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/students", status_code=status.HTTP_201_CREATED)
async def create_student_profile(
    student: StudentProfile,
    supabase: Client = Depends(get_supabase_client),
    current_user: dict = Depends(get_current_admin_user) # Only admins can create
):
    """
    Create a new student profile.
    Requires admin authentication.
    """
    try:
        response = supabase.table("students").insert(student.dict()).execute()
        if response.data:
            return {"message": "Student profile created successfully", "data": response.data[0]}
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=response.error.message)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/students/{student_id}")
async def get_student_profile(
    student_id: str,
    supabase: Client = Depends(get_supabase_client),
    current_user: dict = Depends(get_current_admin_user) # Or a student can view their own profile
):
    """
    Retrieve a student profile by ID.
    Requires admin authentication or the student viewing their own profile.
    """
    try:
        # Implement logic for students to view their own profile if not admin
        if current_user.get("role") != "admin" and current_user.get("id") != student_id:
             raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this profile")

        response = supabase.table("students").select("*").eq("student_id", student_id).limit(1).execute()
        if response.data:
            return response.data[0]
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.patch("/students/{student_id}")
async def update_student_profile(
    student_id: str,
    student_update: StudentProfileUpdate,
    supabase: Client = Depends(get_supabase_client),
    current_user: dict = Depends(get_current_admin_user) # Only admins can update
):
    """
    Update an existing student profile.
    Requires admin authentication.
    """
    try:
        # Filter out None values from the update payload
        update_data = student_update.dict(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update provided.")

        response = supabase.table("students").update(update_data).eq("student_id", student_id).execute()
        if response.data:
            return {"message": "Student profile updated successfully", "data": response.data[0]}
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found or no changes made")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/students/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student_profile(
    student_id: str,
    supabase: Client = Depends(get_supabase_client),
    current_user: dict = Depends(get_current_admin_user) # Only admins can delete
):
    """
    Delete a student profile.
    Requires admin authentication.
    """
    try:
        response = supabase.table("students").delete().eq("student_id", student_id).execute()
        if response.data:
            return {"message": "Student profile deleted successfully"}
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/students")
async def get_all_students(
    supabase: Client = Depends(get_supabase_client),
    current_user: dict = Depends(get_current_admin_user) # Only admins can view all students
):
    """
    Retrieve all student profiles.
    Requires admin authentication.
    """
    try:
        response = supabase.table("students").select("*").execute()
        if response.data:
            return response.data
        return []
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/", response_model=List[StudentSummary])
async def get_all_students_summary(
    supabase_client: Client = Depends(get_supabase_client),
    user_role: str = Depends(get_current_user_role)
):
    if user_role not in ["admin", "teacher", "counselor"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to view student list.")

    try:
        response = supabase_client.from("students").select(
            "id, full_name, grade_level, academic_year, status"
        ).execute()

        if response.data:
            students_summary = []
            for student in response.data:
                # To get has_504_plan, we need to query the iep_504_plans table
                iep_response = supabase_client.from("iep_504_plans").select("has_plan").eq("student_id", student["id"]).single().execute()
                has_504_plan = iep_response.data.get("has_plan", False) if iep_response.data else False

                students_summary.append(StudentSummary(
                    id=student["id"],
                    full_name=student["full_name"],
                    grade_level=student["grade_level"],
                    academic_year=student["academic_year"],
                    status=student["status"],
                    has_504_plan=has_504_plan
                ))
            return students_summary
        else:
            return []
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/{student_id}", response_model=StudentProfileResponse)
async def get_student_profile_full(
    student_id: str,
    supabase_client: Client = Depends(get_supabase_client),
    user_role: str = Depends(get_current_user_role)
):
    if user_role not in ["admin", "teacher", "counselor"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to view student profiles.")

    try:
        # Fetch main student info
        student_response = supabase_client.from("students").select("*").eq("id", student_id).single().execute()
        if not student_response.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
        student_data = student_response.data

        # Fetch all related data
        courses_res = supabase_client.from("courses").select("*").eq("student_id", student_id).execute()
        assessments_res = supabase_client.from("assessment_breakdowns").select("*").eq("student_id", student_id).execute()
        gpa_history_res = supabase_client.from("gpa_history").select("*").eq("student_id", student_id).execute()
        attendance_res = supabase_client.from("attendance").select("*").eq("student_id", student_id).execute()
        extracurricular_res = supabase_client.from("extracurricular_activities").select("*").eq("student_id", student_id).execute()
        iep_res = supabase_client.from("iep_504_plans").select("*").eq("student_id", student_id).single().execute()
        college_milestones_res = supabase_client.from("college_milestones").select("*").eq("student_id", student_id).execute()
        narrative_comments_res = supabase_client.from("narrative_comments").select("*").eq("student_id", student_id).execute()
        counselor_notes_res = supabase_client.from("counselor_notes").select("*").eq("student_id", student_id).execute()
        behavior_notes_res = supabase_client.from("behavior_notes").select("*").eq("student_id", student_id).execute()
        soft_skills_res = supabase_client.from("soft_skills").select("*").eq("student_id", student_id).execute()

        # Reconstruct StudentProfileData
        student_profile_data = StudentProfileData(
            student_info=StudentInfoCore(
                full_name=student_data["full_name"],
                grade_level=student_data["grade_level"],
                academic_year=student_data["academic_year"],
                status=student_data.get("status", "None")
            ),
            courses=[Course(**c) for c in courses_res.data] if courses_res.data else [],
            assessment_breakdown_by_type=[AssessmentBreakdown(**a) for a in assessments_res.data] if assessments_res.data else [],
            gpa_history=[GPAHistoryEntry(**g) for g in gpa_history_res.data] if gpa_history_res.data else [],
            attendance=AttendanceData(
                absences=Absences(excused=attendance_res.data.get("excused", 0), unexcused=attendance_res.data.get("unexcused", 0)) if attendance_res.data else Absences(excused=0, unexcused=0),
                tardies=Tardies(count=attendance_res.data.get("tardy_count", 0), dates=attendance_res.data.get("tardy_dates", [])) if attendance_res.data else Tardies(count=0, dates=[])
            ) if attendance_res.data else None,
            extracurricular_activities=[ExtracurricularActivity(**e) for e in extracurricular_res.data] if extracurricular_res.data else [],
            iep_504_plan_information=IEP504Plan(**iep_res.data) if iep_res.data else None,
            college_counseling_milestones=[CollegeMilestone(**c) for c in college_milestones_res.data] if college_milestones_res.data else []
        )

        # Reconstruct UnstructuredData
        unstructured_data = UnstructuredData(
            narrative_teacher_comments=[NarrativeComment(**n) for n in narrative_comments_res.data] if narrative_comments_res.data else [],
            advisory_counselor_notes=[StaffNote(**s) for s in counselor_notes_res.data] if counselor_notes_res.data else [],
            behavior_social_emotional_notes=[StaffNote(**b) for b in behavior_notes_res.data] if behavior_notes_res.data else []
        )

        # Soft Skill Inferences
        soft_skill_inferences = [SoftSkillInference(**s) for s in soft_skills_res.data] if soft_skills_res.data else []

        return StudentProfileResponse(
            student_profile=student_profile_data,
            unstructured_data=unstructured_data,
            soft_skill_inferences=soft_skill_inferences
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.patch("/{student_id}", status_code=status.HTTP_200_OK)
async def update_student_profile_full(
    student_id: str,
    update_data: StudentUpdatePayload,
    supabase_client: Client = Depends(get_supabase_client),
    user_role: str = Depends(get_current_user_role)
):
    allowed_roles = ["admin", "teacher", "counselor"]
    if user_role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to update student profile.")

    try:
        # Update main student info fields in 'students' table
        student_update_payload = update_data.model_dump(include={"full_name", "grade_level", "academic_year", "status"}, exclude_unset=True)
        if student_update_payload:
            supabase_client.from("students").update(student_update_payload).eq("id", student_id).execute()

        # Handle updates for related tables (replace existing lists for simplicity)
        if update_data.courses is not None:
            supabase_client.from("courses").delete().eq("student_id", student_id).execute()
            if update_data.courses:
                courses_to_insert = [{"student_id": student_id, **c.model_dump()} for c in update_data.courses]
                supabase_client.from("courses").insert(courses_to_insert).execute()

        if update_data.assessment_breakdown_by_type is not None:
            supabase_client.from("assessment_breakdowns").delete().eq("student_id", student_id).execute()
            if update_data.assessment_breakdown_by_type:
                assessments_to_insert = [{"student_id": student_id, **a.model_dump()} for a in update_data.assessment_breakdown_by_type]
                supabase_client.from("assessment_breakdowns").insert(assessments_to_insert).execute()

        if update_data.gpa_history is not None:
            supabase_client.from("gpa_history").delete().eq("student_id", student_id).execute()
            if update_data.gpa_history:
                gpa_history_to_insert = [{"student_id": student_id, **g.model_dump()} for g in update_data.gpa_history]
                supabase_client.from("gpa_history").insert(gpa_history_to_insert).execute()

        if update_data.attendance is not None:
            # For single object, upsert or update
            attendance_data = update_data.attendance.model_dump()
            supabase_client.from("attendance").upsert({
                "student_id": student_id,
                "excused": attendance_data.get("absences", {}).get("excused", 0),
                "unexcused": attendance_data.get("absences", {}).get("unexcused", 0),
                "tardy_count": attendance_data.get("tardies", {}).get("count", 0),
                "tardy_dates": attendance_data.get("tardies", {}).get("dates", [])
            }, on_conflict="student_id").execute()

        if update_data.extracurricular_activities is not None:
            supabase_client.from("extracurricular_activities").delete().eq("student_id", student_id).execute()
            if update_data.extracurricular_activities:
                activities_to_insert = [{"student_id": student_id, **a.model_dump()} for a in update_data.extracurricular_activities]
                supabase_client.from("extracurricular_activities").insert(activities_to_insert).execute()

        if update_data.iep_504_plan_information is not None:
            iep_data = update_data.iep_504_plan_information.model_dump()
            supabase_client.from("iep_504_plans").upsert({
                "student_id": student_id,
                "has_plan": iep_data.get("has_plan", False),
                "plan_type": iep_data.get("plan_type"),
                "accommodations": iep_data.get("accommodations", []),
                "last_updated": iep_data.get("last_updated_date")
            }, on_conflict="student_id").execute()

        if update_data.college_counseling_milestones is not None:
            supabase_client.from("college_milestones").delete().eq("student_id", student_id).execute()
            if update_data.college_counseling_milestones:
                milestones_to_insert = [{"student_id": student_id, **m.model_dump()} for m in update_data.college_counseling_milestones]
                supabase_client.from("college_milestones").insert(milestones_to_insert).execute()

        if update_data.narrative_teacher_comments is not None:
            supabase_client.from("narrative_comments").delete().eq("student_id", student_id).execute()
            if update_data.narrative_teacher_comments:
                comments_to_insert = [{"student_id": student_id, **c.model_dump()} for c in update_data.narrative_teacher_comments]
                supabase_client.from("narrative_comments").insert(comments_to_insert).execute()

        if update_data.advisory_counselor_notes is not None:
            supabase_client.from("counselor_notes").delete().eq("student_id", student_id).execute()
            if update_data.advisory_counselor_notes:
                counselor_notes_to_insert = [{"student_id": student_id, **n.model_dump()} for n in update_data.advisory_counselor_notes]
                supabase_client.from("counselor_notes").insert(counselor_notes_to_insert).execute()

        if update_data.behavior_social_emotional_notes is not None:
            supabase_client.from("behavior_notes").delete().eq("student_id", student_id).execute()
            if update_data.behavior_social_emotional_notes:
                behavior_notes_to_insert = [{"student_id": student_id, **n.model_dump()} for n in update_data.behavior_social_emotional_notes]
                supabase_client.from("behavior_notes").insert(behavior_notes_to_insert).execute()

        if update_data.soft_skill_inferences is not None:
            supabase_client.from("soft_skills").delete().eq("student_id", student_id).execute()
            if update_data.soft_skill_inferences:
                soft_skills_to_insert = [{"student_id": student_id, **s.model_dump()} for s in update_data.soft_skill_inferences]
                supabase_client.from("soft_skills").insert(soft_skills_to_insert).execute()

        # Return the updated profile
        return await get_student_profile_full(student_id, supabase_client, user_role)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/{student_id}/comments", status_code=status.HTTP_201_CREATED)
async def add_narrative_comment(
    student_id: str,
    comment: CommentCreate,
    supabase_client: Client = Depends(get_supabase_client),
    user_role: str = Depends(get_current_admin_user) # Only admins can add comments
):
    if user_role not in ["admin", "teacher", "counselor"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to add comments.")

    try:
        # Verify student exists
        student_check = supabase_client.from("students").select("id").eq("id", student_id).single().execute()
        if not student_check.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")

        new_comment_data = comment.model_dump()
        insert_response = supabase_client.from("narrative_comments").insert({
            "student_id": student_id,
            **new_comment_data
        }).execute()

        if insert_response.data:
            return {"message": "Comment added successfully."}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=insert_response.error.message if insert_response.error else "Failed to add comment.")

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/reports/trends")
async def get_reports_trends(
    grade_level: Optional[int] = Query(None, description="Filter by student grade level"),
    min_gpa: Optional[float] = Query(None, description="Minimum GPA value for filtering"),
    max_gpa: Optional[float] = Query(None, description="Maximum GPA value for filtering"),
    supabase_client: Client = Depends(get_supabase_client),
    user_role: str = Depends(get_current_user_role)
):
    if user_role not in ["admin", "teacher", "counselor"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to view reports.")

    try:
        # Fetch students and their GPA history and soft skills
        query = supabase_client.from("students").select("id, full_name, grade_level, academic_year, status")
        if grade_level:
            query = query.eq("grade_level", grade_level)
        students_response = query.execute()

        if not students_response.data:
            return {
                "gpa_histogram": [],
                "soft_skill_coverage": [],
                "gpa_drops_students": []
            }

        students_data = students_response.data
        
        # Fetch GPA history and soft skills for all fetched students
        student_ids = [s["id"] for s in students_data]
        gpa_history_all_students_res = supabase_client.from("gpa_history").select("*").in_("student_id", student_ids).execute()
        soft_skills_all_students_res = supabase_client.from("soft_skills").select("*").in_("student_id", student_ids).execute()

        gpa_map = {}
        for gpa_entry in gpa_history_all_students_res.data:
            student_id = gpa_entry["student_id"]
            if student_id not in gpa_map:
                gpa_map[student_id] = []
            gpa_map[student_id].append(gpa_entry)

        soft_skill_map = {}
        for skill_entry in soft_skills_all_students_res.data:
            student_id = skill_entry["student_id"]
            if student_id not in soft_skill_map:
                soft_skill_map[student_id] = []
            soft_skill_map[student_id].append(skill_entry)

        # Combine data for processing
        processed_students = []
        for student in students_data:
            student["gpa_history"] = gpa_map.get(student["id"], [])
            student["soft_skill_inferences"] = soft_skill_map.get(student["id"], [])
            processed_students.append(student)

        # Filter by GPA range if provided
        if min_gpa is not None or max_gpa is not None:
            filtered_students_by_gpa = []
            for student in processed_students:
                latest_gpa = None
                if student.get("gpa_history"):
                    sorted_gpas = sorted(student["gpa_history"], key=lambda x: (x.get("academic_year", ""), x.get("term", "")), reverse=True)
                    if sorted_gpas:
                        latest_gpa = sorted_gpas[0].get("gpa_value")

                if latest_gpa is not None:
                    if (min_gpa is None or latest_gpa >= min_gpa) and \
                       (max_gpa is None or latest_gpa <= max_gpa):
                        filtered_students_by_gpa.append(student)
            processed_students = filtered_students_by_gpa

        # GPA Histogram Calculation
        gpa_ranges = {
            "0.0-1.0": 0, "1.1-2.0": 0, "2.1-3.0": 0, "3.1-4.0": 0
        }
        for student in processed_students:
            if student.get("gpa_history"):
                sorted_gpas = sorted(student["gpa_history"], key=lambda x: (x.get("academic_year", ""), x.get("term", "")), reverse=True)
                if sorted_gpas:
                    latest_gpa = sorted_gpas[0].get("gpa_value")
                    if latest_gpa is not None:
                        if 0.0 <= latest_gpa <= 1.0:
                            gpa_ranges["0.0-1.0"] += 1
                        elif 1.1 <= latest_gpa <= 2.0:
                            gpa_ranges["1.1-2.0"] += 1
                        elif 2.1 <= latest_gpa <= 3.0:
                            gpa_ranges["2.1-3.0"] += 1
                        elif 3.1 <= latest_gpa <= 4.0:
                            gpa_ranges["3.1-4.0"] += 1
        gpa_histogram = [{"range": r, "count": c} for r, c in gpa_ranges.items()]

        # Soft Skill Coverage Calculation
        soft_skill_counts = {}
        for student in processed_students:
            for skill in student.get("soft_skill_inferences", []):
                skill_name = skill.get("skill_name")
                if skill_name:
                    soft_skill_counts[skill_name] = soft_skill_counts.get(skill_name, 0) + 1
        soft_skill_coverage = [{"skill_name": s, "count": c} for s, c in soft_skill_counts.items()]

        # GPA Drops Calculation
        gpa_drops_students = []
        for student in processed_students:
            gpa_history = sorted(student.get("gpa_history", []), key=lambda x: (x.get("academic_year", ""), x.get("term", "")))
            if len(gpa_history) >= 2:
                term2_gpa_entry = gpa_history[-1]
                term1_gpa_entry = gpa_history[-2]

                gpa1 = term1_gpa_entry.get("gpa_value")
                gpa2 = term2_gpa_entry.get("gpa_value")

                if gpa1 is not None and gpa2 is not None:
                    drop_amount = round(gpa1 - gpa2, 2)
                    if drop_amount > 0.3: # Significant drop threshold
                        gpa_drops_students.append({
                            "student_id": student["id"],
                            "full_name": student["full_name"],
                            "grade_level": student["grade_level"],
                            "academic_year": student["academic_year"],
                            "status": student["status"],
                            "term1": f"{term1_gpa_entry.get('academic_year', 'N/A')} {term1_gpa_entry.get('term', 'N/A')}",
                            "gpa1": gpa1,
                            "term2": f"{term2_gpa_entry.get('academic_year', 'N/A')} {term2_gpa_entry.get('term', 'N/A')}",
                            "gpa2": gpa2,
                            "drop_amount": drop_amount
                        })

        return {
            "gpa_histogram": gpa_histogram,
            "soft_skill_coverage": soft_skill_coverage,
            "gpa_drops_students": gpa_drops_students
        }

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_student(student_id: str, user_role: str = Depends(get_current_admin_user)):
    try:
        # Deleting from 'students' table with ON DELETE CASCADE will delete from related tables
        response = supabase_client.from("students").delete().eq("id", student_id).execute()
        if response.data:
            return {"message": f"Student {student_id} deleted successfully."}
        else:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found or deletion failed.")
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/upload-students-csv")
async def upload_students_csv(
    file: UploadFile = File(...),
    supabase: Client = Depends(get_supabase_client),
    current_user: dict = Depends(get_current_admin_user) # Only admin can upload
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    try:
        df = pd.read_csv(file.file)
        
        # Convert DataFrame to a list of dictionaries for Supabase insertion
        # Ensure column names match your Supabase table exactly
        students_data = df.to_dict(orient="records")

        # Basic validation (can be expanded)
        for student in students_data:
            # Convert date strings to date objects if necessary, or ensure format matches DB
            if 'date_of_birth' in student and isinstance(student['date_of_birth'], str):
                student['date_of_birth'] = date.fromisoformat(student['date_of_birth'])
            if 'enrollment_date' in student and isinstance(student['enrollment_date'], str):
                student['enrollment_date'] = date.fromisoformat(student['enrollment_date'])
            # Ensure GPA is float
            if 'gpa' in student:
                student['gpa'] = float(student['gpa'])
            if 'scholarship_amount' in student:
                student['scholarship_amount'] = float(student['scholarship_amount'])

        # Insert data into Supabase
        response = supabase.table("students").insert(students_data).execute()

        if response.data:
            return {"message": f"Successfully uploaded {len(response.data)} student records."}
        elif response.error:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=response.error.message)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process CSV: {e}")
