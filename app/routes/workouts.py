from typing import List, Optional, Dict
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime
from starlette.concurrency import run_in_threadpool
from fastapi import APIRouter

app = APIRouter()
# Gemini (Google Generative AI)
import google.generativeai as genai

# Local DB models and session
from routes.db import Workout as DBWorkout, Set as DBSet, get_db

# FastAPI & CORS



# 🚨 Replace this with your actual key from https://makersuite.google.com/app
GEMINI_API_KEY = "AIzaSyA5pJu0pgTuMn_-wr04vJs7Mb8UVYZOQQ4"
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")




# 🧱 Pydantic Schemas
class SetDetails(BaseModel):
    reps: str = Field(..., description="Reps")
    weight: str = Field(..., description="Weight")

class WorkoutCreate(BaseModel):
    muscle_group: str
    workout_type: str
    sets: List[SetDetails]
    date: str  # YYYY-MM-DD
    notes: Optional[str] = None

class WorkoutResponse(WorkoutCreate):
    id: int

# 📌 Create Workout
@app.post("/workout")
def create_workout(workout: WorkoutCreate, db: Session = Depends(get_db)):
    try:
        workout_datetime = datetime.strptime(workout.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    
    db_workout = DBWorkout(
        muscle_group=workout.muscle_group,
        workout_type=workout.workout_type,
        date=workout_datetime,
        notes=workout.notes,
        sets=[DBSet(reps=s.reps, weight=s.weight) for s in workout.sets]
    )
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    return {"message": "Workout created successfully", "workout_id": db_workout.id}

# 📌 Get Workouts Grouped by Date & Muscle Group
@app.get("/workouts", response_model=Dict[str, Dict[str, List[WorkoutResponse]]])
def get_workouts(db: Session = Depends(get_db)):
    workouts = db.query(DBWorkout).all()
    grouped: Dict[str, Dict[str, List[WorkoutResponse]]] = {}

    for workout in workouts:
        date_str = workout.date.strftime("%Y-%m-%d")
        sets = [SetDetails(reps=s.reps, weight=s.weight) for s in workout.sets]
        workout_data = WorkoutResponse(
            id=workout.id,
            muscle_group=workout.muscle_group,
            workout_type=workout.workout_type,
            sets=sets,
            notes=workout.notes,
            date=date_str,
        )
        grouped.setdefault(date_str, {}).setdefault(workout.muscle_group, []).append(workout_data)
    return grouped

# 📌 Get Single Workout by ID
@app.get("/workout/{workout_id}", response_model=WorkoutResponse)
def get_workout(workout_id: int, db: Session = Depends(get_db)):
    workout = db.query(DBWorkout).filter(DBWorkout.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found.")

    sets = [SetDetails(reps=s.reps, weight=s.weight) for s in workout.sets]
    return WorkoutResponse(
        id=workout.id,
        muscle_group=workout.muscle_group,
        workout_type=workout.workout_type,
        sets=sets,
        date=workout.date.strftime("%Y-%m-%d"),
        notes=workout.notes,
    )

# 📌 Update Workout
@app.put("/workout/{workout_id}")
def update_workout(workout_id: int, updated: WorkoutCreate, db: Session = Depends(get_db)):
    workout = db.query(DBWorkout).filter(DBWorkout.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found.")

    workout.muscle_group = updated.muscle_group
    workout.workout_type = updated.workout_type
    workout.date = datetime.strptime(updated.date, "%Y-%m-%d")
    workout.notes = updated.notes
    workout.sets.clear()
    workout.sets = [DBSet(reps=s.reps, weight=s.weight) for s in updated.sets]
    db.commit()
    return {"message": "Workout updated successfully"}

# 📌 Delete Workout
@app.delete("/workout/{workout_id}")
def delete_workout(workout_id: int, db: Session = Depends(get_db)):
    workout = db.query(DBWorkout).filter(DBWorkout.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found.")
    
    db.delete(workout)
    db.commit()
    return {"message": "Workout deleted successfully"}

# 📌 Raw Data for Show/Export
@app.get("/details")
def get_details(db: Session = Depends(get_db)):
    workouts = db.query(DBWorkout).all()
    details = []
    for workout in workouts:
        details.append([
            workout.id,
            workout.muscle_group,
            workout.workout_type,
            workout.date.strftime("%Y-%m-%d"),
            workout.notes,
            [{"reps": s.reps, "weight": s.weight} for s in workout.sets]
        ])
    return details

# 🤖 Gemini AI Suggestions
@app.get("/ai-suggestions")
async def get_ai_suggestions(db: Session = Depends(get_db)):
    workouts = db.query(DBWorkout).order_by(DBWorkout.date.desc()).limit(5).all()
    if not workouts:
        return {"suggestion": "Workout history is empty."}

    # 🧠 Format prompt from workout logs
    history_lines = []
    for w in workouts:
        if not w.sets:
            continue
        sets_summary = ", ".join([f"{s.reps}@{s.weight}" for s in w.sets])
        history_lines.append(f"{w.date.strftime('%Y-%m-%d')}: {w.muscle_group} - {w.workout_type} ({sets_summary})")

    prompt = (
    "You are a professional personal fitness coach powered by AI.\n\n"
    "Below is a log of the user's recent daily workout sessions. "
    "Each entry contains the date, muscle group worked, workout type, and sets (with reps and weights).\n\n"
    "Workout History:\n"
    + "\n".join(history_lines) +
    "\n\nInstructions:\n"
    "- Focus strictly on workout-related suggestions: training splits, workout variety, reps, and weights.\n"
    "- If history includes fewer than 7 unique days, assume the user is just starting.\n"
    "    → In this case, suggest: beginner-friendly split plans, how to distribute workouts across the week, "
    "and simple rep/weight progression tips.\n"
    "- If the log spans 7+ days, analyze for patterns: imbalanced muscle groups, repeated workouts, or missing elements.\n"
    "- DO NOT include nutrition, recovery, supplements, or general fitness advice.\n"
    "- Keep feedback brief and helpful — use bullet points (no paragraphs).\n"
    "- Output 4–6 short bullet points only.\n"
    "- Always use a positive, supportive tone.\n\n"
    "Now based on this workout history, give personalized suggestions strictly focused on training structure, variety, reps, and weights."
)




    try:
        response = await run_in_threadpool(gemini_model.generate_content, prompt)
        return {"suggestion": response.text.strip()}
    except Exception as e:
        print(f"Gemini API error: {e}")
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")
