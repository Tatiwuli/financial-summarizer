from fastapi import FastAPI, status, Request, File, Form, UploadFile
from fastapi.responses import JSONResponse
from src.services.precheck import PrecheckError, run_precheck
from src.services.summary_workflow import SummaryWorkflowError, run_summary_workflow
from pydantic import BaseModel
from typing import List, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import os
import logging
import time

app = FastAPI(title="Summarizer v1")

raw_origins = os.getenv("CORS_ORIGINS", "")
ALLOWED_ORIGINS = [o.strip() for o in raw_origins.split(",") if o.strip()]
# ALLOWED_ORIGINS_LOCALHOST = ["http://localhost:8081","http://192.168.15.3:8081"]

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")
logger.info(f"CORS_ORIGINS raw='{raw_origins}', parsed={ALLOWED_ORIGINS}")


# Enable CORS for React Native
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https:\/\/financial-summarizer-git-.*-tatiane-wu-lis-projects\.vercel\.app$",
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)



# Middleware to log request/response and CORS headers for debugging
@app.middleware("http")
async def cors_debug_logger(request: Request, call_next):
    start_time = time.time()
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    host = request.headers.get("host")
    xff = request.headers.get("x-forwarded-for")
    xfp = request.headers.get("x-forwarded-proto")
    logger.info(
        f"REQ method={request.method} path={request.url.path} origin={origin} referer={referer} host={host} xff={xff} xfp={xfp}"
    )
    response = await call_next(request)
    aco = response.headers.get("access-control-allow-origin")
    vary = response.headers.get("vary")
    duration_ms = int((time.time() - start_time) * 1000)
    logger.info(
        f"RES path={request.url.path} status={response.status_code} A-C-Allow-Origin={aco} Vary={vary} durMs={duration_ms}"
    )
    return response


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class SummaryResponse(BaseModel):
    title: str
    call_type: str
    blocks: List[Any]


class PrecheckResponse(BaseModel):
    blocks: List[Any]

# ---------EXCEPTION HANDLERS ---------------


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


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/v1/precheck")
def precheck():
    """
    Validate the pdf size and text sections with a pdf path 
    """

    payload = run_precheck()
    return payload


@app.post("/v1/summarize")
async def summarize(
    file: UploadFile = File(..., description="The pdf file to summarize"),
    call_type: str = Form(..., description="The type of call to summarize"),

    summary_length: str = Form(..., description="The length of the summary")
):

    if file.content_type != "application/pdf":
        raise PrecheckError(
            "invalid_file_type", f"Tipo de arquivo inválido. Esperado arquivo com extensao '.pdf ', mas recebido '{file.content_type}'")

    payload = run_summary_workflow(
        file=file, call_type=call_type, summary_length=summary_length)
    return payload


@app.post("/v1/judge")
async def judge(
    file: UploadFile = File(..., description="The pdf file to judge"),
    version_prompt: str = Form(...,
                               description="The version of the prompt to use"),
    qa_transcript: str = Form(..., description="The transcript of the Q&A"),
    qa_summary: str = Form(..., description="The summary of the Q&A"),
    summary_structure: str = Form(...,
                                  description="The structure of the summary")
):
    payload = run_judge_workflow(file=file, version_prompt=version_prompt,
                                 qa_transcript=qa_transcript, qa_summary=qa_summary, summary_structure=summary_structure)
    return payload
