from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
from routes.db import get_db, Diet, Users as DBUsers
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
    user_id: int
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
async def create_diet_entry(request: DietRequest, db: Session = Depends(get_db)):
    user = db.query(DBUsers).filter(DBUsers.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    query = f"{request.quantity}g {request.food}"
    response = requests.get(api_url + query, headers={'X-Api-Key': DIET_API_KEY})

    if response.status_code == 200:
        data = response.json()
        if not data['items']:
            raise HTTPException(status_code=404, detail="No nutrition info found.")

        item = data['items'][0]

        db_diet = Diet(
            user_id=request.user_id,
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
@diet_router.get("/diet/{user_id}", response_model=list[DietResponse])
def get_user_diet_logs(user_id: int, db: Session = Depends(get_db)):
    return db.query(Diet).filter((Diet.user_id == user_id) & (Diet.date == datetime.today().date())).all()


# Delete a diet entry
@diet_router.delete("/diet/{diet_id}", response_model=dict)
def delete_diet_entry(diet_id: int, db: Session = Depends(get_db)):
    diet_entry = db.query(Diet).filter(Diet.id == diet_id).first()
    if not diet_entry:
        raise HTTPException(status_code=404, detail="Diet entry not found.")

    db.delete(diet_entry)
    db.commit()
    return {"message": f"Diet entry {diet_id} deleted successfully."}


# Update a diet entry (with updated nutrition if food/quantity changed)
@diet_router.put("/diet/{diet_id}", response_model=DietResponse)
def update_diet_entry(diet_id: int, request: DietUpdateRequest, db: Session = Depends(get_db)):
    diet_entry = db.query(Diet).filter(Diet.id == diet_id).first()
    if not diet_entry:
        raise HTTPException(status_code=404, detail="Diet entry not found.")

    updated = False
    food = request.food if request.food else diet_entry.food
    quantity = request.quantity if request.quantity else diet_entry.quantity

    # If food or quantity changed, fetch updated nutrition
    if request.food is not None or request.quantity is not None:
        query = f"{quantity}g {food}"
        response = requests.get(api_url + query, headers={'X-Api-Key': DIET_API_KEY})
        if response.status_code == 200:
            data = response.json()
            if data["items"]:
                item = data["items"][0]
                diet_entry.food = item["name"]
                diet_entry.quantity = quantity
                diet_entry.calories = int(item["calories"])
                diet_entry.protein = int(item["protein_g"])
                diet_entry.carbohydrates = int(item["carbohydrates_total_g"])
                diet_entry.fat = int(item["fat_total_g"])
                updated = True
            else:
                raise HTTPException(status_code=404, detail="No nutrition info found for updated food.")
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)

    if request.meal_type is not None:
        diet_entry.meal_type = request.meal_type
        updated = True
    if request.date is not None:
        diet_entry.date = request.date
        updated = True

    if updated:
        db.commit()
        db.refresh(diet_entry)

    return diet_entry


# Generate diet suggestions using Gemini
@diet_router.post("/diet/suggestions", response_model=dict)
async def generate_diet_suggestions(user_id: int, db: Session = Depends(get_db)):
    user = db.query(DBUsers).filter(DBUsers.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    diet_logs = db.query(Diet).filter(Diet.user_id == user_id).order_by(Diet.date.desc()).limit(7).all()
    if not diet_logs:
        raise HTTPException(status_code=404, detail="No diet logs found for this user.")

    today = date.today()
    today_nutrients = db.query(
        func.sum(Diet.calories).label("calories"),
        func.sum(Diet.protein).label("protein"),
        func.sum(Diet.carbohydrates).label("carbs"),
        func.sum(Diet.fat).label("fats")
    ).filter(Diet.user_id == user_id, Diet.date == today).first()

    prompt = (
        f"You are a professional nutritionist. Based on the following data, give a strict, concise bullet-point diet analysis.\n"
        f"\n--- USER INFO ---\n"
        f"• Age: {user.age} years\n"
        f"• Height: {user.height} cm\n"
        f"• Weight: {user.weight} kg\n"
        f"• Target Weight: {user.target_weight} kg\n"
        f"• Activity Level: {user.activity_level}\n"
        f"\n--- TODAY'S TOTAL NUTRIENTS ---\n"
        f"• Calories: {today_nutrients.calories or 0} kcal\n"
        f"• Protein: {today_nutrients.protein or 0} g\n"
        f"• Carbs: {today_nutrients.carbs or 0} g\n"
        f"• Fats: {today_nutrients.fats or 0} g\n"
        f"\n--- DIET LOGS (last 7 days) ---\n"
    )

    for log in reversed(diet_logs):  # Oldest first
        prompt += f"- {log.date} | {log.meal_type.capitalize()}: {log.food} ({log.quantity}g)\n"

    prompt += (
        "\n--- INSTRUCTIONS FOR OUTPUT ---\n"
        "Respond with concise bullet points:\n"
        "start with user detials\n"
        "1. What's nutritionally correct in user's diet.\n"
        "2. What's deficient or excessive.\n"
        "3. What to add/remove to balance nutrients.\n"
        "4. Suggestions to reach the target weight goal.\n"
        "5. Any other relevant nutritional advice.\n"
        "Be short, blunt, no soft language, no paragraphs. Straight to the point."
    )

    try:
        response = await run_in_threadpool(gemini_model.generate_content, prompt)
        return {"suggestion": response.text.strip()}
    except Exception as e:
        print(f"Gemini API error: {e}")
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")
