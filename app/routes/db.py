from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime, timezone

Base = declarative_base()

# Child table: Set per workout
class Set(Base):
    __tablename__ = "sets"
    id = Column(Integer, primary_key=True, index=True)
    reps = Column(String, index=True)
    weight = Column(String, index=True)
    workout_id = Column(Integer, ForeignKey("workouts.id"))  

# Parent table: Workout info
class Workout(Base):
    __tablename__ = "workouts"
    id = Column(Integer, primary_key=True, index=True)
    muscle_group = Column(String, index=True)
    workout_type = Column(String)
    date = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    notes = Column(String)
    sets = relationship("Set", backref="workout", cascade="all, delete-orphan")

# DB setup
engine = create_engine("sqlite:///./workouts.db")
Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# DB dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
