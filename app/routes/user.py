from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime
from routes.db import get_db, Users

user_router = APIRouter()

# Request model
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

# Response model
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

# Authentication function
def authenticate_user(db: Session, username: str, password: str) -> Users:
    user = db.query(Users).filter(Users.username == username, Users.password == password).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return user

# Register new user
@user_router.post("/user", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(Users).filter(Users.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(Users).filter(Users.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    try:
        datetime.strptime(user.birth_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid birth_date format. Use YYYY-MM-DD")

    db_user = Users(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Get all users
@user_router.get("/get_users", response_model=list[UserResponse])
def get_users(db: Session = Depends(get_db)):
    return db.query(Users).all()
