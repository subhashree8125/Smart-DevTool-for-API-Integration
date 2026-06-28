from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class APIAnalysisRequest(BaseModel):
    url: str = Field(..., description="The URL of the API documentation")
    use_case: Optional[str] = Field(None, description="Optional use case for Gemini AI focus")
    preferred_language: Optional[str] = Field("python", description="Target programming language for SDK")

class EndpointSchema(BaseModel):
    id: Optional[str] = None
    method: str = Field(..., description="HTTP Method (GET, POST, etc.)")
    path: str = Field(..., description="API endpoint path relative to Base URL")
    description: Optional[str] = None
    auth_required: bool = False
    headers: Optional[List[Dict[str, Any]]] = None  # e.g., [{"name": "Content-Type", "type": "string", "required": true}]
    query_params: Optional[List[Dict[str, Any]]] = None
    path_params: Optional[List[Dict[str, Any]]] = None
    request_body: Optional[Dict[str, Any]] = None  # Schema description or JSON sample
    response_body: Optional[Dict[str, Any]] = None
    status_codes: Optional[List[int]] = None
    sample_request: Optional[str] = None
    sample_response: Optional[str] = None

class APIAnalysisResponse(BaseModel):
    id: str
    url: str
    use_case: Optional[str] = None
    name: Optional[str] = None
    version: Optional[str] = None
    base_url: Optional[str] = None
    doc_type: Optional[str] = None
    auth_type: Optional[str] = None
    summary: Optional[str] = None
    sdk_recommendation: Optional[str] = None
    endpoints: List[EndpointSchema] = []
    created_at: datetime

class WrapperGenerateRequest(BaseModel):
    api_id: str = Field(..., description="The ID of the analyzed API")
    language: str = Field(..., description="The programming language to generate the wrapper in")

class WrapperGenerateResponse(BaseModel):
    id: str
    api_id: str
    language: str
    wrapper_code: str
    readme_code: str
    zip_path: str
    created_at: datetime

class HealthResponse(BaseModel):
    status: str
    database: str
    gemini_configured: bool
