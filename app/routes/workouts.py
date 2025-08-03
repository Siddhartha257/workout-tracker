from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime
from routes.db import get_db, Workout as DBWorkout, Set as DBSet, Users as DBUsers
from routes.user import get_current_user
# Gemini (Google Generative AI)
import google.generativeai as genai

# 🚨 Replace this with your actual key from https://makersuite.google.com/app
GEMINI_API_KEY = "AIzaSyD4XzFyaNaITSUiGlhuQAYYCRFVtpGku3I"
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

router = APIRouter()

# === Pydantic Models ===
class SetDetails(BaseModel):
    reps: str
    weight: str

class WorkoutCreate(BaseModel):
    muscle_group: str
    workout_type: str
    sets: List[SetDetails]
    date: str  # Format: YYYY-MM-DD
    notes: str = ""

class WorkoutResponse(WorkoutCreate):
    id: int

    class Config:
        from_attributes = True

# === Create Workout ===
@router.post("/workout", response_model=dict)
def create_workout(
    workout: WorkoutCreate,
    current_user: DBUsers = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        workout_date = datetime.strptime(workout.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    db_workout = DBWorkout(
        muscle_group=workout.muscle_group,
        workout_type=workout.workout_type,
        date=workout_date,
        notes=workout.notes,
        user_id=current_user.id,
        sets=[DBSet(reps=s.reps, weight=s.weight) for s in workout.sets]
    )
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)
    return {"message": "Workout added", "workout_id": db_workout.id}

# === Get Workouts Grouped by Date ===
@router.get("/workouts", response_model=Dict[str, List[WorkoutResponse]])
def get_user_workouts(current_user: DBUsers = Depends(get_current_user), db: Session = Depends(get_db)):
    workouts = db.query(DBWorkout).filter(DBWorkout.user_id == current_user.id).all()
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

# === Get Workout by ID ===
@router.get("/workout/{workout_id}", response_model=WorkoutResponse)
def get_workout_by_id(
    workout_id: int, 
    current_user: DBUsers = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workout = db.query(DBWorkout).filter(
        DBWorkout.id == workout_id,
        DBWorkout.user_id == current_user.id
    ).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    
    sets = [SetDetails(reps=s.reps, weight=s.weight) for s in workout.sets]
    return WorkoutResponse(
        id=workout.id,
        muscle_group=workout.muscle_group,
        workout_type=workout.workout_type,
        date=workout.date.strftime("%Y-%m-%d"),
        notes=workout.notes,
        sets=sets
    )

# === Update Workout ===
@router.put("/workout/{workout_id}")
def update_workout(
    workout_id: int,
    updated: WorkoutCreate,
    current_user: DBUsers = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workout = db.query(DBWorkout).filter(
        DBWorkout.id == workout_id,
        DBWorkout.user_id == current_user.id
    ).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    try:
        workout_date = datetime.strptime(updated.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    # Update workout details
    workout.muscle_group = updated.muscle_group
    workout.workout_type = updated.workout_type
    workout.date = workout_date
    workout.notes = updated.notes

    # Clear existing sets and add new ones
    db.query(DBSet).filter(DBSet.workout_id == workout_id).delete()
    workout.sets = [DBSet(reps=s.reps, weight=s.weight) for s in updated.sets]

    db.commit()
    return {"message": "Workout updated successfully"}

# === Delete Workout ===
@router.delete("/workout/{workout_id}")
def delete_workout(
    workout_id: int,
    current_user: DBUsers = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    workout = db.query(DBWorkout).filter(
        DBWorkout.id == workout_id,
        DBWorkout.user_id == current_user.id
    ).first()
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    db.delete(workout)
    db.commit()
    return {"message": "Workout deleted successfully"}

# === AI Suggestions ===
@router.get("/ai-suggestions")
async def get_ai_suggestions(
    current_user: DBUsers = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get user's recent workouts
    recent_workouts = db.query(DBWorkout).filter(
        DBWorkout.user_id == current_user.id
    ).order_by(DBWorkout.date.desc()).limit(5).all()

    if not recent_workouts:
        return {"suggestions": "No workout history found. Start with basic exercises like push-ups, squats, and planks."}

    # Create context for AI
    workout_history = []
    for workout in recent_workouts:
        workout_history.append(f"{workout.muscle_group}: {workout.workout_type} : {workout.date.strftime('%Y-%m-%d')}")

    prompt = f"""
You are a bold and strict personal fitness coach.

User Profile:
- Age: {current_user.age}
- Gender: {current_user.gender}
- Current Weight: {current_user.weight}
- Target Weight: {current_user.target_weight}
- Activity Level: {current_user.activity_level}

Workout History (last 7 days):
{', '.join(workout_history)}

Analyze the user’s profile and past 7-day workout history. Return output only in the following strict structure:

1. What You Did Right
-consider only today's workout(highest date).
-be professional and direct(about parts of muscle groups).
- List specific things the user did well (e.g., consistent training, good push/pull ratio).

2. Muscle Group Status 
- consider only today's workout(highest date).
- Clearly state which parts of today's muscle group are overtrained, undertrained, or skipped.
-talk about todays muscle group only(eg  if user did back and biceps talk about that).
- Give direct correction advice to restore balance.

3. Today's Workout Plan  
- Mention exact muscle groups to target.  
- List 6–9 exercises (grouped by muscle), each with sets, reps, rest time.  
- Prioritize compound lifts and balance across upper/lower/core.  
- Use raw bullet points. Be firm.
- If user did back , suggest back and biceps workout.

4. What You Did Wrong  
- Call out mistakes bluntly. No sugarcoating.  
- Mention overuse, neglect, lack of variation, poor recovery, etc.

5. Tomorrow's Workout Plan  
- Recommend which muscle groups to focus on based on today's session and missed areas.

6. Weekly Split Suggestion  
- Suggest a split based on user goals and history.  
- Include rest and active recovery days.

Be raw, bold, and strict. No emojis, no markdown symbols, no decoration. Only give results — no motivation or praise. Keep it all business.
"""



    try:
        response = await run_in_threadpool(
            lambda: gemini_model.generate_content(prompt)
        )
        return {"suggestions": response.text}
    except Exception as e:
        return {"suggestions": f"Unable to generate suggestions: {str(e)}"}