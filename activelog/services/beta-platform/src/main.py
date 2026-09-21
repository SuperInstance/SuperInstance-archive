from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
from pathlib import Path

from .database import engine, Base
from .feedback.routes import router as feedback_router
from .bug_reporting.routes import router as bug_router
from .feature_requests.routes import router as feature_router
from .rewards.routes import router as rewards_router
from .rollout.routes import router as rollout_router
from .monitoring.routes import router as monitoring_router
from .crash_reporting.routes import router as crash_router
from .analytics.routes import router as analytics_router
from .ab_testing.routes import router as ab_testing_router
from .documentation.routes import router as docs_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="ActiveLog Beta Platform",
    description="Beta testing platform for ActiveLog services",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Include routers
app.include_router(feedback_router, prefix="/api/feedback", tags=["feedback"])
app.include_router(bug_router, prefix="/api/bugs", tags=["bug-reporting"])
app.include_router(feature_router, prefix="/api/features", tags=["feature-requests"])
app.include_router(rewards_router, prefix="/api/rewards", tags=["rewards"])
app.include_router(rollout_router, prefix="/api/rollout", tags=["rollout"])
app.include_router(monitoring_router, prefix="/api/monitoring", tags=["monitoring"])
app.include_router(crash_router, prefix="/api/crashes", tags=["crash-reporting"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])
app.include_router(ab_testing_router, prefix="/api/ab-testing", tags=["ab-testing"])
app.include_router(docs_router, prefix="/api/docs", tags=["documentation"])

@app.get("/")
async def root():
    return {"message": "ActiveLog Beta Platform", "version": "1.0.0", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "beta-platform"}

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8323,
        reload=True,
        access_log=True
    )