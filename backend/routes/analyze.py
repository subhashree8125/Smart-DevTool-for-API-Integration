import uuid
import json
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.models.schemas import APIAnalysisRequest, APIAnalysisResponse, EndpointSchema
from backend.database.connection import get_db_connection
from backend.services.doc_fetcher import fetch_documentation
from backend.services.doc_detector import detect_documentation_type
from backend.parsers.openapi_parser import parse_openapi
from backend.parsers.html_parser import parse_html_or_markdown
from backend.parsers.graphql_parser import parse_graphql
from backend.ai.gemini_client import analyze_unstructured_docs, generate_api_summary

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/analyze", response_model=APIAnalysisResponse)
async def analyze_api(request: APIAnalysisRequest):
    """
    Fetches, detects type, parses endpoints, analyzes via Gemini,
    and returns full structured API documentation model.
    """
    url = request.url.strip()
    use_case = request.use_case.strip() if request.use_case else ""
    
    try:
        # Step 1: Fetch content
        raw_doc_content = fetch_documentation(url)
        
        # Step 2: Detect format
        doc_type = detect_documentation_type(raw_doc_content)
        logger.info(f"Detected documentation type for {url}: {doc_type}")
        
        # Step 3: Run Parser
        parsed_data = {}
        if doc_type in ("openapi", "swagger"):
            parsed_data = parse_openapi(raw_doc_content)
        elif doc_type == "graphql":
            parsed_data = parse_graphql(raw_doc_content)
        else:
            # HTML / Markdown -> Clean and use Gemini to structure
            parsed_data = parse_html_or_markdown(
                raw_doc_content, 
                use_case=use_case, 
                gemini_analyzer=analyze_unstructured_docs
            )

        api_name = parsed_data.get("name", "Extracted API")
        api_version = parsed_data.get("version", "1.0.0")
        base_url = parsed_data.get("base_url", "/")
        auth_type = parsed_data.get("auth_type", "None")
        endpoints_list = parsed_data.get("endpoints", [])

        # Validate that endpoints list matches Pydantic schemas (defensive parsing)
        endpoints_models = []
        for ep in endpoints_list:
            if isinstance(ep, dict):
                try:
                    # Skip definitions/schemas that lack required routing keys
                    if not ep.get("method") or not ep.get("path"):
                        logger.warning(f"Skipping non-endpoint metadata schema component: {ep}")
                        continue
                    endpoints_models.append(EndpointSchema(**ep))
                except Exception as ve:
                    logger.warning(f"Skipping malformed endpoint schema component due to validation error: {ve}")
                    continue
            else:
                endpoints_models.append(ep)

        # Step 4: Generate API Summary & Recommendation using Gemini
        try:
            # Create a lightweight outline for Gemini to avoid sending huge JSON schemas
            lightweight_endpoints = [
                {
                    "method": ep.method,
                    "path": ep.path,
                    "description": ep.description,
                    "auth_required": ep.auth_required
                }
                for ep in endpoints_models
            ]
            temp_details = {
                "name": api_name,
                "version": api_version,
                "base_url": base_url,
                "auth_type": auth_type,
                "endpoints": lightweight_endpoints
            }
            ai_summary_data = generate_api_summary(temp_details, use_case)
            summary = ai_summary_data.get("summary", "No summary generated.")
            sdk_recommendation = ai_summary_data.get("sdk_recommendation", "REST client recommended.")
        except Exception as ae:
            logger.error(f"Gemini API analysis summary generation failed: {ae}")
            summary = "Failed to run Gemini AI analysis. Using auto-generated parsing outline."
            sdk_recommendation = "Manual integration using the auto-extracted REST schema is recommended."

        # Step 5: Save to SQLite database
        api_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Save main API record
        cursor.execute("""
            INSERT INTO apis (id, url, use_case, name, version, base_url, doc_type, auth_type, summary, sdk_recommendation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            api_id, url, use_case, api_name, api_version, base_url, 
            doc_type, auth_type, summary, sdk_recommendation
        ))
        
        # Save endpoints records
        for ep in endpoints_models:
            ep.id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO endpoints (
                    id, api_id, method, path, description, auth_required, 
                    headers, query_params, path_params, request_body, 
                    response_body, status_codes, sample_request, sample_response
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ep.id,
                api_id,
                ep.method,
                ep.path,
                ep.description or "",
                1 if ep.auth_required else 0,
                json.dumps(ep.headers or []),
                json.dumps(ep.query_params or []),
                json.dumps(ep.path_params or []),
                json.dumps(ep.request_body or {}),
                json.dumps(ep.response_body or {}),
                json.dumps(ep.status_codes or [200]),
                ep.sample_request or "",
                ep.sample_response or ""
            ))
            
        conn.commit()
        conn.close()

        return APIAnalysisResponse(
            id=api_id,
            url=url,
            use_case=use_case,
            name=api_name,
            version=api_version,
            base_url=base_url,
            doc_type=doc_type,
            auth_type=auth_type,
            summary=summary,
            sdk_recommendation=sdk_recommendation,
            endpoints=endpoints_models,
            created_at=created_at
        )

    except Exception as e:
        logger.error(f"Error during API analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze API: {str(e)}")
