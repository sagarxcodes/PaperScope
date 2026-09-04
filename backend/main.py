from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.material import router as material_router
from app.routers.auth import router as auth_router
from app.routers.questions import router as questions_router
from app.routers.assessment import router as assessment_router
from app.routers.adaptive import router as adaptive_router
from app.routers.competency import router as competency_router
from app.routers.recommendation import router as recommendation_router
from app.routers.training import router as training_router
from app.routers.pipeline import router as pipeline_router
from app.routers.demo import router as demo_router
from app.routers.pyq import router as pyq_router
from app.routers.calendar import router as calendar_router
from app.routers.where_you_stand import router as where_you_stand_router
from app.routers.exams import router as exams_router
from app.routers.trends import router as trends_router
from app.routers.notes import router as notes_router
from app.routers.exam_sources import router as exam_sources_router

app = FastAPI(
    title="PaperScope AI Engine",
    description="AI-powered competency intelligence backend for PaperScope",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
        "https://paper-scope-steel.vercel.app",
        # Production frontend is added through the CORS_ORIGINS
        # environment variable after Vercel deployment.
        *[
            origin.strip()
            for origin in __import__("os").getenv("CORS_ORIGINS", "").split(",")
            if origin.strip()
        ],
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "service": "PaperScope AI Engine",
        "version": "1.0.0",
    }


@app.get("/api")
def root():
    return {
        "message": "PaperScope backend is running",
        "engines": [
            "material",
            "question",
            "assessment",
            "adaptive",
            "competency",
            "capacity",
            "recommendation",
            "personalized_plan",
        ],
    }


app.include_router(material_router)

app.include_router(questions_router)

app.include_router(assessment_router)

app.include_router(adaptive_router)

app.include_router(competency_router)

app.include_router(recommendation_router)

app.include_router(training_router)

app.include_router(pipeline_router)

app.include_router(auth_router)

app.include_router(demo_router)
app.include_router(pyq_router)
app.include_router(calendar_router)

app.include_router(where_you_stand_router)

app.include_router(exams_router)

app.include_router(trends_router)

app.include_router(notes_router)
app.include_router(exam_sources_router)
