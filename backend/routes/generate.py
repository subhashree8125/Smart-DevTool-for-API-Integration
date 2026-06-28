import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from backend.models.schemas import WrapperGenerateRequest, WrapperGenerateResponse, EndpointSchema
from backend.database.connection import get_db_connection
from backend.generators.wrapper_generator import build_sdk_project

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/generate", response_model=WrapperGenerateResponse)
async def generate_wrapper(request: WrapperGenerateRequest):
    """Generates the SDK wrapper and packs it into a ZIP package."""
    api_id = request.api_id
    language = request.language.lower()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Fetch API details from database
    cursor.execute("SELECT * FROM apis WHERE id = ?", (api_id,))
    api_row = cursor.fetchone()
    if not api_row:
        conn.close()
        raise HTTPException(status_code=404, detail="API registration details not found.")
        
    api_name = api_row["name"]
    api_version = api_row["version"]
    base_url = api_row["base_url"]
    auth_type = api_row["auth_type"]
    summary = api_row["summary"]
    
    # 2. Fetch endpoints
    cursor.execute("SELECT * FROM endpoints WHERE api_id = ?", (api_id,))
    endpoint_rows = cursor.fetchall()
    
    endpoints = []
    import json
    for ep in endpoint_rows:
        try:
            headers = json.loads(ep["headers"]) if ep["headers"] else []
        except Exception:
            headers = []
            
        try:
            query_params = json.loads(ep["query_params"]) if ep["query_params"] else []
        except Exception:
            query_params = []
            
        try:
            path_params = json.loads(ep["path_params"]) if ep["path_params"] else []
        except Exception:
            path_params = []
            
        try:
            request_body = json.loads(ep["request_body"]) if ep["request_body"] else {}
        except Exception:
            request_body = {}
            
        try:
            response_body = json.loads(ep["response_body"]) if ep["response_body"] else {}
        except Exception:
            response_body = {}
            
        try:
            status_codes = json.loads(ep["status_codes"]) if ep["status_codes"] else [200]
        except Exception:
            status_codes = [200]

        endpoints.append(EndpointSchema(
            id=ep["id"],
            method=ep["method"],
            path=ep["path"],
            description=ep["description"],
            auth_required=bool(ep["auth_required"]),
            headers=headers,
            query_params=query_params,
            path_params=path_params,
            request_body=request_body,
            response_body=response_body,
            status_codes=status_codes,
            sample_request=ep["sample_request"],
            sample_response=ep["sample_response"]
        ))
        
    # Reconstruct API payload for AI generator (optimized to prevent token bloat and timeouts)
    endpoints_lightweight = []
    for ep in endpoints:
        endpoints_lightweight.append({
            "id": ep.id,
            "method": ep.method,
            "path": ep.path,
            "description": ep.description,
            "auth_required": ep.auth_required,
            "headers": ep.headers,
            "query_params": ep.query_params,
            "path_params": ep.path_params,
            "request_body": ep.request_body,
            "sample_request": ep.sample_request
        })

    api_details = {
        "name": api_name,
        "version": api_version,
        "base_url": base_url,
        "auth_type": auth_type,
        "summary": summary,
        "endpoints": endpoints_lightweight
    }
    
    try:
        # 3. Generate wrapper assets and build archive
        project_data = build_sdk_project(
            api_id=api_id,
            api_name=api_name,
            api_version=api_version,
            base_url=base_url,
            language=language,
            api_details=api_details
        )
        
        project_id = project_data["id"]
        wrapper_code = project_data["wrapper_code"]
        readme_code = project_data["readme_code"]
        zip_path = project_data["zip_path"]
        created_at = datetime.utcnow()
        
        # 4. Save project record in SQLite
        cursor.execute("""
            INSERT INTO projects (id, api_id, language, wrapper_code, readme_code, zip_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (project_id, api_id, language, wrapper_code, readme_code, zip_path))
        
        conn.commit()
        conn.close()
        
        return WrapperGenerateResponse(
            id=project_id,
            api_id=api_id,
            language=language,
            wrapper_code=wrapper_code,
            readme_code=readme_code,
            zip_path=zip_path,
            created_at=created_at
        )
    except Exception as e:
        conn.close()
        logger.error(f"Failed to generate client library SDK wrapper: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
