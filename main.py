from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from auth_utils import get_password_hash, verify_password, create_access_token, get_current_user, TokenData, get_current_admin_user
from supabase_client import get_supabase_client
from supabase import Client
import os
from student_ingestion_route import router as student_ingestion_router
from typing import List
from datetime import date

app = FastAPI(
    title="Student Analytics Backend",
    description="API for managing student data, authentication, and analytics.",
    version="1.0.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json"
)

# CORS configuration
# In production, replace "*" with your actual frontend URL (e.g., "https://your-frontend-domain.com")
# The FRONTEND_URL environment variable should be set in .env and Vercel.
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
origins = [
    FRONTEND_URL,
    "http://localhost:3000", # For local development
    "http://localhost:8000", # For local backend testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include other routers
app.include_router(student_ingestion_router, prefix="/api")

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "student" # Default role

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class StudentProfile(BaseModel):
    student_id: str
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

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Student Analytics Backend API!"}

@app.post("/api/register", response_model=Token)
async def register_user(user: UserCreate, supabase: Client = Depends(get_supabase_client)):
    hashed_password = get_password_hash(user.password)
    
    # Check if username already exists
    response = supabase.table("users").select("username").eq("username", user.username).execute()
    if response.data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Insert new user into Supabase
    response = supabase.table("users").insert({
        "username": user.username,
        "hashed_password": hashed_password,
        "role": user.role
    }).execute()

    if response.data:
        access_token = create_access_token(data={"sub": user.username, "role": user.role})
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=response.error.message if response.error else "Failed to register user"
        )

@app.post("/api/token", response_model=Token)
async def login_for_access_token(user: UserLogin, supabase: Client = Depends(get_supabase_client)):
    response = supabase.table("users").select("hashed_password, role").eq("username", user.username).single().execute()
    
    if not response.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    hashed_password = response.data["hashed_password"]
    role = response.data["role"]

    if not verify_password(user.password, hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username, "role": role})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/users/me", response_model=TokenData)
async def read_users_me(current_user: TokenData = Depends(get_current_user)):
    return current_user

# Example protected route for students
@app.get("/api/students/me")
async def read_student_data(current_user: TokenData = Depends(get_current_user), supabase: Client = Depends(get_supabase_client)):
    if current_user.role != "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized as student")
    
    # In a real app, you'd fetch student data linked to current_user.username
    # For now, return a placeholder
    return {"message": f"Hello student {current_user.username}! Here's your data."}

# Example protected route for admins
@app.get("/api/admin/dashboard")
async def read_admin_dashboard(current_user: TokenData = Depends(get_current_admin_user)):
    return {"message": f"Welcome admin {current_user.username}! This is the admin dashboard."}

# Route to fetch all students (admin only)
@app.get("/api/students", response_model=List[StudentProfile])
async def get_all_students(
    supabase: Client = Depends(get_supabase_client),
    current_user: TokenData = Depends(get_current_admin_user)
):
    response = supabase.table("students").select("*").execute()
    if response.data:
        # Convert date strings from Supabase to date objects for Pydantic validation
        for student in response.data:
            if 'date_of_birth' in student and isinstance(student['date_of_birth'], str):
                student['date_of_birth'] = date.fromisoformat(student['date_of_birth'])
            if 'enrollment_date' in student and isinstance(student['enrollment_date'], str):
                student['enrollment_date'] = date.fromisoformat(student['enrollment_date'])
        return response.data
    elif response.error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=response.error.message)
    return []

# Route to fetch a single student by ID (admin or the student themselves)
@app.get("/api/students/{student_id}", response_model=StudentProfile)
async def get_student_by_id(
    student_id: str,
    supabase: Client = Depends(get_supabase_client),
    current_user: TokenData = Depends(get_current_user)
):
    # If not admin, ensure the student_id matches the current user's student_id
    if current_user.role != "admin":
        # This assumes a mapping between username and student_id exists,
        # or that the username *is* the student_id for student users.
        # For simplicity, let's assume username == student_id for student roles.
        if current_user.username != student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this student's data")

    response = supabase.table("students").select("*").eq("student_id", student_id).single().execute()
    if response.data:
        # Convert date strings from Supabase to date objects for Pydantic validation
        if 'date_of_birth' in response.data and isinstance(response.data['date_of_birth'], str):
            response.data['date_of_birth'] = date.fromisoformat(response.data['date_of_birth'])
        if 'enrollment_date' in response.data and isinstance(response.data['enrollment_date'], str):
            response.data['enrollment_date'] = date.fromisoformat(response.data['enrollment_date'])
        return response.data
    elif response.error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=response.error.message)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

# Route to update student data (admin only, or student for their own profile with limited fields)
@app.patch("/api/students/{student_id}", response_model=StudentProfile)
async def update_student_data(
    student_id: str,
    student_update: dict, # Use dict for partial updates
    supabase: Client = Depends(get_supabase_client),
    current_user: TokenData = Depends(get_current_user)
):
    # Implement server-side role validation for PATCH /students
    if current_user.role != "admin":
        # If not admin, only allow student to update their own profile and only specific fields
        if current_user.username != student_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this student's data")
        
        # Define fields a student can update (e.g., phone_number, address, email)
        allowed_student_fields = ["phone_number", "address", "email"]
        for field in student_update.keys():
            if field not in allowed_student_fields:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Students are not allowed to update '{field}'")

    # Convert date strings to date objects if present in update data
    if 'date_of_birth' in student_update and isinstance(student_update['date_of_birth'], str):
        student_update['date_of_birth'] = date.fromisoformat(student_update['date_of_birth'])
    if 'enrollment_date' in student_update and isinstance(student_update['enrollment_date'], str):
        student_update['enrollment_date'] = date.fromisoformat(student_update['enrollment_date'])

    response = supabase.table("students").update(student_update).eq("student_id", student_id).execute()
    
    if response.data:
        # Supabase update returns the updated rows. Take the first one.
        updated_student = response.data[0]
        # Convert date strings back to date objects for Pydantic validation
        if 'date_of_birth' in updated_student and isinstance(updated_student['date_of_birth'], str):
            updated_student['date_of_birth'] = date.fromisoformat(updated_student['date_of_birth'])
        if 'enrollment_date' in updated_student and isinstance(updated_student['enrollment_date'], str):
            updated_student['enrollment_date'] = date.fromisoformat(updated_student['enrollment_date'])
        return updated_student
    elif response.error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=response.error.message)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found or no changes applied")

# Route to delete student data (admin only)
@app.delete("/api/students/{student_id}")
async def delete_student_data(
    student_id: str,
    supabase: Client = Depends(get_supabase_client),
    current_user: TokenData = Depends(get_current_admin_user)
):
    response = supabase.table("students").delete().eq("student_id", student_id).execute()
    if response.data:
        return {"message": f"Student {student_id} deleted successfully."}
    elif response.error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=response.error.message)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "message": "Backend is running"}

@app.get("/api/admin/users")
async def get_all_users(
    supabase_client: Client = Depends(get_supabase_client),
    current_admin: TokenData = Depends(get_current_admin_user)
):
    response = supabase_client.table("users").select("id, username, role").execute()
    if response.data:
        return response.data
    elif response.error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error fetching users: {response.error.message}")
    return []

@app.post("/api/admin/users")
async def create_user(
    username: str,
    password: str,
    role: str,
    supabase_client: Client = Depends(get_supabase_client),
    current_admin: TokenData = Depends(get_current_admin_user)
):
    # Basic validation for role
    if role not in ["admin", "advisor", "student"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role specified.")

    # Check if user already exists
    response = supabase_client.table("users").select("id").eq("username", username).execute()
    if response.data:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists.")

    hashed_password = get_password_hash(password)
    user_data = {"username": username, "hashed_password": hashed_password, "role": role}
    response = supabase_client.table("users").insert(user_data).execute()
    if response.data:
        return {"message": "User created successfully", "user_id": response.data[0]["id"]}
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create user: {response.error.message}")

@app.patch("/api/admin/users/{user_id}")
async def update_user_role(
    user_id: str,
    new_role: str,
    supabase_client: Client = Depends(get_supabase_client),
    current_admin: TokenData = Depends(get_current_admin_user)
):
    if new_role not in ["admin", "advisor", "student"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role specified.")

    response = supabase_client.table("users").update({"role": new_role}).eq("id", user_id).execute()
    if response.data:
        return {"message": f"User {user_id} role updated to {new_role}", "data": response.data[0]}
    elif response.error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to update user role: {response.error.message}")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")

@app.delete("/api/admin/users/{user_id}")
async def delete_user(
    user_id: str,
    supabase_client: Client = Depends(get_supabase_client),
    current_admin: TokenData = Depends(get_current_admin_user)
):
    response = supabase_client.table("users").delete().eq("id", user_id).execute()
    if response.data:
        return {"message": f"User {user_id} deleted successfully."}
    elif response.error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete user: {response.error.message}")
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found.")
