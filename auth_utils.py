import os
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends, Request, APIRouter
from pydantic import BaseModel, EmailStr
from supabase import Client
from supabase_client import get_supabase_client, supabase
from fastapi.security import OAuth2PasswordBearer

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = os.getenv("SUPABASE_JWT_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

if not SECRET_KEY:
    raise ValueError("SECRET_KEY must be set as an environment variable.")

router = APIRouter()

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, credentials_exception):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=role)
    except JWTError:
        raise credentials_exception
    return token_data

async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    return verify_token(token, credentials_exception)

async def get_current_active_user(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    if current_user is None:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_admin_user(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user

@router.post("/login")
async def login_for_access_token(user_login: UserLogin):
    response = supabase.auth.sign_in_with_password({
        "email": user_login.email,
        "password": user_login.password,
    })

    if response.user:
        # Fetch user's role from your 'users' table
        user_data_res = supabase.from_("users").select("role").eq("id", response.user.id).single().execute()
        user_role = user_data_res.data["role"] if user_data_res.data else "default"

        # Create a custom JWT that includes the role
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(response.user.id), "email": response.user.email, "role": user_role},
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer", "user_role": user_role}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.get("/me")
async def read_users_me(current_user: TokenData = Depends(get_current_user)):
    # This endpoint now just confirms the user's role based on the token
    return {"role": current_user.role}

@router.post("/admin/users", status_code=status.HTTP_201_CREATED)
async def create_user(user_create: UserLogin, current_admin_user: TokenData = Depends(get_current_admin_user)):
    # Create user in Supabase Auth
    auth_response = supabase.auth.admin.create_user({
        "email": user_create.email,
        "password": user_create.password,
        "email_confirm": True # Automatically confirm email for admin created users
    })

    if auth_response.user:
        # Insert user into your 'users' table with role
        db_response = supabase.from_("users").insert({
            "id": str(auth_response.user.id), # Ensure UUID is converted to string
            "email": user_create.email,
            "role": "default" # Assuming a default role for simplicity
        }).execute()
        if db_response.data:
            return {"message": "User created successfully", "user_id": str(auth_response.user.id)}
        else:
            # If DB insert fails, consider deleting the auth user or logging
            supabase.auth.admin.delete_user(str(auth_response.user.id))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save user role")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=auth_response.error.message)

@router.get("/admin/users", status_code=status.HTTP_200_OK)
async def get_users(current_admin_user: TokenData = Depends(get_current_admin_user)):
    response = supabase.from_("users").select("id, email, role").execute()
    if response.data:
        return response.data
    if response.error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=response.error.message)
    return []

@router.patch("/admin/users/{user_id}", status_code=status.HTTP_200_OK)
async def update_user(user_id: str, user_update: UserUpdate, current_admin_user: TokenData = Depends(get_current_admin_user)):
    update_data = user_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    # Update in 'users' table
    response = supabase.from_("users").update(update_data).eq("id", user_id).execute()
    if response.data:
        return {"message": "User updated successfully", "user_id": user_id}
    if response.error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=response.error.message)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or no changes made")

@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, current_admin_user: TokenData = Depends(get_current_admin_user)):
    # Delete from Supabase Auth
    auth_response = supabase.auth.admin.delete_user(user_id)
    if auth_response.error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=auth_response.error.message)

    # Delete from 'users' table
    db_response = supabase.from_("users").delete().eq("id", user_id).execute()
    if db_response.error:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=db_response.error.message)
    return
