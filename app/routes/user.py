from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from routes.db import get_db, Users
import jwt
import bcrypt
from typing import Optional

user_router = APIRouter()
security = HTTPBearer()

# JWT Configuration
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Models
class UserCreate(BaseModel):
    username: str
    password: str
    email: str
    gender: str
    birth_date: str  # Format: YYYY-MM-DD
    age: int
    height: str
    weight: str
    target_weight: str
    activity_level: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    gender: str
    birth_date: str
    age: int
    height: str
    weight: str
    target_weight: str
    activity_level: str

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str

# Password hashing functions
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# JWT functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Authentication dependency
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    payload = verify_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(Users).filter(Users.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# Authentication
def authenticate_user(db: Session, username: str, password: str) -> Users:
    user = db.query(Users).filter(Users.username == username).first()
    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return user

# Login route
@user_router.post("/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    user_in_db = authenticate_user(db, user.username, user.password)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user_in_db.id)}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_in_db.id,
        "username": user_in_db.username
    }

# Register route
@user_router.post("/signup", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(Users).filter(Users.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(Users).filter(Users.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    try:
        datetime.strptime(user.birth_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid birth_date format. Use YYYY-MM-DD")

    # Hash the password
    hashed_password = hash_password(user.password)
    
    db_user = Users(
        username=user.username,
        password=hashed_password,
        email=user.email,
        gender=user.gender,
        birth_date=user.birth_date,
        age=user.age,
        height=user.height,
        weight=user.weight,
        target_weight=user.target_weight,
        activity_level=user.activity_level
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Get current user info
@user_router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: Users = Depends(get_current_user)):
    return current_user

# Logout route (client-side token removal)
@user_router.post("/logout")
def logout():
    return {"message": "Successfully logged out"}

# Get all users (for admin purposes)
@user_router.get("/get_users", response_model=list[UserResponse])
def get_users(db: Session = Depends(get_db)):
    return db.query(Users).all()
