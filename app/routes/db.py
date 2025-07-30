from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime, timezone

Base = declarative_base()

class Users(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String)
    email = Column(String, unique=True, index=True)
    gender = Column(String)
    birth_date = Column(String)
    age = Column(Integer)
    height = Column(String)
    weight = Column(String)
    target_weight = Column(String)
    activity_level = Column(String)

    workouts = relationship("Workout", back_populates="user", cascade="all, delete-orphan")
    diets = relationship("Diet", back_populates="user", cascade="all, delete-orphan")

class Set(Base):
    __tablename__ = "sets"
    id = Column(Integer, primary_key=True, index=True)
    reps = Column(String)
    weight = Column(String)
    workout_id = Column(Integer, ForeignKey("workouts.id"))

class Workout(Base):
    __tablename__ = "workouts"
    id = Column(Integer, primary_key=True, index=True)
    muscle_group = Column(String)
    workout_type = Column(String)
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(String)

    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("Users", back_populates="workouts")

    sets = relationship("Set", backref="workout", cascade="all, delete-orphan")

class Diet(Base):
    __tablename__ = "diets"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String)
    meal_type = Column(String)
    food = Column(String)
    quantity = Column(Integer)
    calories = Column(Integer)
    protein = Column(Integer)
    carbohydrates = Column(Integer)
    fat = Column(Integer)

    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("Users", back_populates="diets")

# DB setup
engine = create_engine("sqlite:///./workouts.db", connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
