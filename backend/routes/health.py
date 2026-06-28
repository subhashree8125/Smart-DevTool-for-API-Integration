import os
from fastapi import APIRouter
from backend.models.schemas import HealthResponse
from backend.database.connection import get_db_connection

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def check_health():
    """Health check endpoint to test backend and database status."""
    db_status = "Healthy"
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1;")
        conn.close()
    except Exception as e:
        db_status = f"Unhealthy: {str(e)}"

    gemini_key = os.getenv("GEMINI_API_KEY", "")
    gemini_configured = len(gemini_key) > 5

    return HealthResponse(
        status="running",
        database=db_status,
        gemini_configured=gemini_configured
    )
