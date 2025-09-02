from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint to verify API status"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
