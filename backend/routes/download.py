import os
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from backend.database.connection import get_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/download/{project_id}")
async def download_project(project_id: str):
    """
    Downloads the zipped SDK wrapper package.
    Resolves the ZIP path from SQLite and streams it as attachment.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT zip_path, language FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Requested project download not found.")
        
    relative_zip_path = row["zip_path"]
    language = row["language"]
    
    # Resolve absolute path and verify safety
    absolute_zip_path = os.path.abspath(relative_zip_path)
    
    # Verify that the path resides within the workspace downloads folder to prevent directory traversal
    downloads_root = os.path.abspath("downloads")
    if not absolute_zip_path.startswith(downloads_root):
        raise HTTPException(status_code=403, detail="Access denied: Directory traversal detected.")
        
    if not os.path.exists(absolute_zip_path):
        raise HTTPException(status_code=404, detail="ZIP package file not found on disk.")
        
    filename = os.path.basename(absolute_zip_path)
    
    return FileResponse(
        path=absolute_zip_path,
        media_type="application/zip",
        filename=filename
    )
