from fastapi import FastAPI
from routes.workouts import app as workouts_router
from fastapi.middleware.cors import CORSMiddleware
from routes.diet import diet_router


app = FastAPI()
app.include_router(workouts_router)
app.include_router(diet_router , prefix="/diet")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


