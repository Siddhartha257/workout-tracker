from fastapi import FastAPI, Request
from routes.workouts import router as workouts_router
from fastapi.middleware.cors import CORSMiddleware
from routes.diet import diet_router
from routes.user import user_router
import time


app = FastAPI()
app.include_router(workouts_router)
app.include_router(diet_router)
app.include_router(user_router)
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


