from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
from routes.db import get_db, Diet, Users as DBUsers
from routes.user import get_current_user
import requests
import google.generativeai as genai

diet_router = APIRouter()

# External APIs
DIET_API_KEY = ""
api_url = 'https://api.calorieninjas.com/v1/nutrition?query='

GEMINI_API_KEY = ""
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# Request schema
class DietRequest(BaseModel):
    date: str  # YYYY-MM-DD
    meal_type: str
    food: str
    quantity: int

# Update schema
class DietUpdateRequest(BaseModel):
    meal_type: str | None = None
    food: str | None = None
    quantity: int | None = None
    date: str | None = None  # Optional update

# Response schema
class DietResponse(BaseModel):
    id: int
    user_id: int
    date: str
    meal_type: str
    food: str
    quantity: int
    calories: int
    protein: int
    carbohydrates: int
    fat: int

    class Config:
        from_attributes = True

# Create diet entry
@diet_router.post("/diet", response_model=DietResponse)
async def create_diet_entry(
    request: DietRequest, 
    current_user: DBUsers = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = f"{request.quantity}g {request.food}"
    response = requests.get(api_url + query, headers={'X-Api-Key': DIET_API_KEY})

    if response.status_code == 200:
        data = response.json()
        if not data['items']:
            raise HTTPException(status_code=404, detail="No nutrition info found.")

        item = data['items'][0]

        db_diet = Diet(
            user_id=current_user.id,
            date=request.date,
            meal_type=request.meal_type,
            food=item['name'],
            quantity=request.quantity,
            calories=int(item['calories']),
            protein=int(item['protein_g']),
            carbohydrates=int(item['carbohydrates_total_g']),
            fat=int(item['fat_total_g'])
        )

        db.add(db_diet)
        db.commit()
        db.refresh(db_diet)

        return db_diet
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)

# Get today's diet logs
@diet_router.get("/diet", response_model=list[DietResponse])
def get_user_diet_logs(
    current_user: DBUsers = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(Diet).filter(
        (Diet.user_id == current_user.id) & 
        (Diet.date == datetime.today().strftime("%Y-%m-%d"))
    ).all()

# Get diet logs by date
@diet_router.get("/diet/{date}", response_model=list[DietResponse])
def get_user_diet_logs_by_date(
    date: str,
    current_user: DBUsers = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return db.query(Diet).filter(
        (Diet.user_id == current_user.id) & 
        (Diet.date == date)
    ).all()

# Delete a diet entry
@diet_router.delete("/diet/{diet_id}", response_model=dict)
def delete_diet_entry(
    diet_id: int,
    current_user: DBUsers = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    diet_entry = db.query(Diet).filter(
        Diet.id == diet_id,
        Diet.user_id == current_user.id
    ).first()
    
    if not diet_entry:
        raise HTTPException(status_code=404, detail="Diet entry not found")
    
    db.delete(diet_entry)
    db.commit()
    return {"message": "Diet entry deleted successfully"}

# Update a diet entry
@diet_router.put("/diet/{diet_id}", response_model=DietResponse)
def update_diet_entry(
    diet_id: int, 
    request: DietUpdateRequest,
    current_user: DBUsers = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    diet_entry = db.query(Diet).filter(
        Diet.id == diet_id,
        Diet.user_id == current_user.id
    ).first()
    
    if not diet_entry:
        raise HTTPException(status_code=404, detail="Diet entry not found")
    
    # Update fields if provided
    if request.meal_type is not None:
        diet_entry.meal_type = request.meal_type
    if request.food is not None:
        diet_entry.food = request.food
    if request.quantity is not None:
        diet_entry.quantity = request.quantity
    if request.date is not None:
        diet_entry.date = request.date
    
    db.commit()
    db.refresh(diet_entry)
    return diet_entry

# Get diet summary for a date range
@diet_router.get("/diet/summary/{start_date}/{end_date}")
def get_diet_summary(
    start_date: str,
    end_date: str,
    current_user: DBUsers = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    diet_entries = db.query(Diet).filter(
        (Diet.user_id == current_user.id) &
        (Diet.date >= start_date) &
        (Diet.date <= end_date)
    ).all()
    
    if not diet_entries:
        return {
            "total_calories": 0,
            "total_protein": 0,
            "total_carbohydrates": 0,
            "total_fat": 0,
            "entry_count": 0
        }
    
    total_calories = sum(entry.calories for entry in diet_entries)
    total_protein = sum(entry.protein for entry in diet_entries)
    total_carbohydrates = sum(entry.carbohydrates for entry in diet_entries)
    total_fat = sum(entry.fat for entry in diet_entries)
    
    return {
        "total_calories": total_calories,
        "total_protein": total_protein,
        "total_carbohydrates": total_carbohydrates,
        "total_fat": total_fat,
        "entry_count": len(diet_entries)
    }

# AI Diet Suggestions
@diet_router.post("/diet/suggestions", response_model=dict)
async def generate_diet_suggestions(
    current_user: DBUsers = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get user's recent diet entries
    recent_diets = db.query(Diet).filter(
        Diet.user_id == current_user.id
    ).filter(Diet.date == datetime.now().date()).all()

    if not recent_diets:
        return {"suggestions": "No diet history found. Start by logging your meals to get personalized suggestions."}
    
    # Calculate average daily calories
    daily_calories = {}
    for diet in recent_diets:
        if diet.date not in daily_calories:
            daily_calories[diet.date] = 0
        daily_calories[diet.date] += diet.calories
    
    avg_calories = sum(daily_calories.values()) / len(daily_calories) if daily_calories else 0
    
    prompt = f"""
    User Profile:
    - Age: {current_user.age}
    - Gender: {current_user.gender}
    - Current Weight: {current_user.weight}
    - Target Weight: {current_user.target_weight}
    - Activity Level: {current_user.activity_level}
    - Average Daily Calories: {avg_calories:.0f}

    Recent Diet History:
    {', '.join([f"{d.food} ({d.calories} cal)({d.date})" for d in recent_diets[:5]])}

    Analyze and respond in this structure:

1. What was done right – briefly state 2–3 good dietary habits.

2. Over/Under Intake – check calorie/macronutrient imbalances. Suggest precise correction (e.g., +20g protein, -30g sugar).

3. Today's Diet Plan – give calorie + macros target. Suggest 4 clean meals with time.

4. Mistakes – list major flaws (e.g., skipped meals, junk, poor hydration).

5. Tomorrow's Plan – adjustments based on current errors.

6. Weekly Diet Split – clean split for 7 days (e.g., 3 high protein days, 2 low carb, 1 refeed, 1 clean cheat if needed).

Be blunt. No fluff. No emojis. No motivation. Just facts and correction.
    """
    
    try:
        response = await run_in_threadpool(
            lambda: gemini_model.generate_content(prompt)
        )
        return {"suggestions": response.text}
    except Exception as e:
        return {"suggestions": f"Unable to generate suggestions: {str(e)}"}
