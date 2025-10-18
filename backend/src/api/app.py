from fastapi import FastAPI, status, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
import logging
import time

from src.services.precheck import PrecheckError
from src.services.summary_workflow import SummaryWorkflowError
from src.config.constants import RETENTION_DAYS, FORCE_CLEANUP_DAYS, CLEANUP_INTERVAL_SECONDS
from src.config.constants import CACHE_DIR

# Routers
from src.api.routes.health import router as health_router
from src.api.routes.summary import router as summary_router
from src.api.routes.file_validation import router as validation_router

# Initializing the FastAPI app
app = FastAPI(title="Summarizer v1")

# Defining the origins to allow requests from
raw_origins = os.getenv("CORS_ORIGINS", "")
ALLOWED_ORIGINS = [o.strip() for o in raw_origins.split(",") if o.strip()]

# For local test
ALLOWED_ORIGINS_LOCALHOST = [
    "http://localhost:8081", "http://192.168.15.3:8081"]

# Initializing the logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")
logger.info(f"CORS_ORIGINS raw='{raw_origins}', parsed={ALLOWED_ORIGINS}")

# CORS for allowing connection from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS or ALLOWED_ORIGINS_LOCALHOST,  # frontend's URLs
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)




class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


@app.exception_handler(PrecheckError)
async def precheck_error_handler(request: Request, exc: PrecheckError):
    return JSONResponse(
        content=ErrorResponse(error=ErrorDetail(
            code=exc.code, message=exc.message)).model_dump(),
        status_code=status.HTTP_400_BAD_REQUEST
    )


@app.exception_handler(SummaryWorkflowError)
async def summary_workflow_error_handler(request: Request, exc: SummaryWorkflowError):
    code_map = {
        "llm_invalid_json": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "llm_summary_error": status.HTTP_502_BAD_GATEWAY,
        "llm_judge_error": status.HTTP_502_BAD_GATEWAY,
        "llm_overview_error": status.HTTP_502_BAD_GATEWAY,
    }

    status_code = code_map.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    return JSONResponse(
        content=ErrorResponse(error=ErrorDetail(
            code=exc.code, message=exc.message)).model_dump(),
        status_code=status_code
    )

# ------------------- API ROUTES---------------------


@app.get("/")
def root():
    return {"message": "Financial Summarizer API"}


# Include routers
app.include_router(health_router, tags=["health"])
app.include_router(summary_router, tags=["summary"])
app.include_router(validation_router, tags=["validation"])
