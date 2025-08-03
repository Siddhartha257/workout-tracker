from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from routes.workouts import router as workouts_router
from fastapi.middleware.cors import CORSMiddleware
from routes.diet import diet_router
from routes.user import user_router
import time
import os

app = FastAPI()

# Include routers
app.include_router(workouts_router)
app.include_router(diet_router)
app.include_router(user_router)

# Mount static files
app.mount("/static", StaticFiles(directory="templates"), name="static")

@app.middleware("http")
async def log_response_time(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    print(f"[{request.method}] {request.url.path} - {duration:.3f}s")
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve HTML files
@app.get("/")
async def read_index():
    return FileResponse("templates/index.html")

@app.get("/login.html")
async def read_login():
    return FileResponse("templates/login.html")

@app.get("/signup.html")
async def read_signup():
    return FileResponse("templates/signup.html")

@app.get("/workouts.html")
async def read_workouts():
    return FileResponse("templates/workouts.html")

@app.get("/diet.html")
async def read_diet():
    return FileResponse("templates/diet.html")


