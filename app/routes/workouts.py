from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from routes.db import get_db, Workout as DBWorkout, Set as DBSet, Users as DBUsers
# Gemini (Google Generative AI)
import google.generativeai as genai




# 🚨 Replace this with your actual key from https://makersuite.google.com/app
GEMINI_API_KEY = ""
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

router = APIRouter()

# Pydantic Models
class SetDetails(BaseModel):
    reps: str
    weight: str

class WorkoutCreate(BaseModel):
    muscle_group: str
    workout_type: str
    sets: List[SetDetails]
    date: str  # YYYY-MM-DD
    notes: str = ""

class WorkoutResponse(WorkoutCreate):
    id: int

    class Config:
        from_attributes = True

# Create Workout for a User
@router.post("/workout", response_model=dict)
def create_workout(
    workout: WorkoutCreate,
    user_id: int = Query(..., description="User ID"),
    db: Session = Depends(get_db)
):
    user = db.query(DBUsers).filter(DBUsers.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        workout_date = datetime.strptime(workout.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    db_workout = DBWorkout(
        muscle_group=workout.muscle_group,
        workout_type=workout.workout_type,
        date=workout_date,
        notes=workout.notes,
        user_id=user_id,
        sets=[DBSet(reps=s.reps, weight=s.weight) for s in workout.sets]
    )
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    return {"message": "Workout added", "workout_id": db_workout.id}

# Get Workouts Grouped by User
@router.get("/workouts", response_model=Dict[str, List[WorkoutResponse]])
def get_user_workouts(user_id: int, db: Session = Depends(get_db)):
    workouts = db.query(DBWorkout).filter(DBWorkout.user_id == user_id).all()
    if not workouts:
        return {}

    grouped = {}
    for w in workouts:
        date_str = w.date.strftime("%Y-%m-%d")
        sets = [SetDetails(reps=s.reps, weight=s.weight) for s in w.sets]
        wr = WorkoutResponse(
            id=w.id,
            muscle_group=w.muscle_group,
            workout_type=w.workout_type,
            date=date_str,
            notes=w.notes,
            sets=sets
        )
        grouped.setdefault(date_str, []).append(wr)
    return grouped

# Get a single workout
@router.get("/workout/{workout_id}", response_model=WorkoutResponse)
def get_workout_by_id(workout_id: int, db: Session = Depends(get_db)):
    workout = db.query(DBWorkout).filter(DBWorkout.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    sets = [SetDetails(reps=s.reps, weight=s.weight) for s in workout.sets]
    return WorkoutResponse(
        id=workout.id,
        muscle_group=workout.muscle_group,
        workout_type=workout.workout_type,
        sets=sets,
        date=workout.date.strftime("%Y-%m-%d"),
        notes=workout.notes
    )

# Update workout
@router.put("/workout/{workout_id}")
def update_workout(
    workout_id: int,
    updated: WorkoutCreate,
    db: Session = Depends(get_db)
):
    workout = db.query(DBWorkout).filter(DBWorkout.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    workout.muscle_group = updated.muscle_group
    workout.workout_type = updated.workout_type
    workout.date = datetime.strptime(updated.date, "%Y-%m-%d")
    workout.notes = updated.notes
    workout.sets.clear()
    workout.sets = [DBSet(reps=s.reps, weight=s.weight) for s in updated.sets]
    db.commit()
    return {"message": "Workout updated"}

# Delete workout
@router.delete("/workout/{workout_id}")
def delete_workout(workout_id: int, db: Session = Depends(get_db)):
    workout = db.query(DBWorkout).filter(DBWorkout.id == workout_id).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    db.delete(workout)
    db.commit()
    return {"message": "Workout deleted"}

@router.get("/ai-suggestions")
async def get_ai_suggestions(user_id: int = Query(...), db: Session = Depends(get_db)):
    user = db.query(DBUsers).filter(DBUsers.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    workouts = (
        db.query(DBWorkout)
        .filter(DBWorkout.user_id == user_id)
        .order_by(DBWorkout.date.desc())
        .limit(7)
        .all()
    )

    if not workouts:
        return {"suggestion": "Workout history is empty."}

    history_lines = []
    for w in workouts:
        if not w.sets:
            continue
        sets_summary = ", ".join([f"{s.reps}@{s.weight}" for s in w.sets])
        history_lines.append(f"{w.date.strftime('%Y-%m-%d')}: {w.muscle_group} - {w.workout_type} ({sets_summary})")

    today_workout = workouts[0]
    today_sets_summary = ", ".join([f"{s.reps}@{s.weight}" for s in today_workout.sets]) if today_workout.sets else "No sets logged"
    today_summary = (
        f"{today_workout.date.strftime('%Y-%m-%d')}: {today_workout.muscle_group} - "
        f"{today_workout.workout_type} ({today_sets_summary})"
    )

    user_info = (
        f"User Profile:\n"
        f"- Gender: {user.gender}\n"
        f"- Age: {user.age}\n"
        f"- Height: {user.height} cm\n"
        f"- Weight: {user.weight} kg\n"
        f"- Target Weight: {user.target_weight} kg\n"
        f"- Activity Level: {user.activity_level}\n"
    )

    prompt = (
        f"You are a world-class personal trainer AI.\n"
        f"{user_info}\n"
        f"Today's Workout:\n{today_summary}\n\n"
        f"Recent Workout History (excluding today):\n" + "\n".join(history_lines[1:]) + "\n\n"
        "Instructions:\n"
        "- Review today's workout first. Check if all muscle parts were properly hit (e.g., all 3 heads of the deltoid)."
        " If the coverage is partial, list specific missing parts and exercises to fix it:\n"
        "  Then give 2–3 brutally honest observations from workout history (e.g., imbalance, bad variety, repetitive muscle use).\n"
        " suggest what workout he did and which part of muscle group is activated by that and suggest workouts for missing parts (e.g., if he did only incline bench press, suggest flat bench press for lower chest).\n"
        " sample output:(incline bench press : upper chest \n flat bench press : lower chest(new workouts)) in bullet points with no limits\n"
        "  Only the last 2 bullet points should talk about:\n"
        "   1. Next day's suggested muscle group and exercise order\n"
        "   2. Weekly split based on past workouts\n"
        "-  Use exactly 8-9 bullet points. No fluff. No paragraphs\n"
        "- - Output must be raw, blunt, and short — act like a coach who doesn’t sugarcoat\n"
        "Return only bullet points. Avoid nutrition/sleep advice.\n"
    )

    try:
        response = await run_in_threadpool(gemini_model.generate_content, prompt)
        return {"suggestion": response.text.strip()}
    except Exception as e:
        print(f"Gemini API error: {e}")
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")
