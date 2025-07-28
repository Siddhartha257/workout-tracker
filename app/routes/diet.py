from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session 
from datetime import datetime
from routes.db import Workout as DBWorkout, get_db
import requests

diet_router = APIRouter()
DIET_API_KEY = "af60yyFJgzAp1xK2X7oclg==Fjex2feiZOS31cZU"
api_url = 'https://api.calorieninjas.com/v1/nutrition?query='

@diet_router.get("/{query}")
async def diet_info(query: str):
    response = requests.get(api_url + query, headers={'X-Api-Key': DIET_API_KEY})
    if response.status_code == requests.codes.ok:
        return response.json()
    else:
        raise HTTPException(status_code=response.status_code, detail=response.text)

