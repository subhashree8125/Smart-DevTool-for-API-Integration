import json
import yaml
import logging
from typing import Dict, Any, List, Optional
from backend.models.schemas import EndpointSchema

logger = logging.getLogger(__name__)

def resolve_ref(ref: str, document: Dict[str, Any]) -> Dict[str, Any]:
    """Resolves local OpenAPI JSON references ($ref)."""
    if not ref or not ref.startswith("#/"):
        return {}
    
    parts = ref.split("/")[1:]
    current = document
    try:
        for part in parts:
            current = current[part]
        return current
    except (KeyError, TypeError):
        return {}

def schema_to_mock_json(schema: Dict[str, Any], document: Dict[str, Any], depth: int = 0) -> Any:
    """Converts OpenAPI schema definition into mock JSON data."""
    if depth > 4:  # Avoid infinite recursion
        return "..."
    
    if not schema:
        return None

    if "$ref" in schema:
        resolved = resolve_ref(schema["$ref"], document)
        return schema_to_mock_json(resolved, document, depth + 1)

    schema_type = schema.get("type", "object")
    
    if schema_type == "object":
        mock_obj = {}
        properties = schema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            mock_obj[prop_name] = schema_to_mock_json(prop_schema, document, depth + 1)
        return mock_obj
    
    elif schema_type == "array":
        items = schema.get("items", {})
        return [schema_to_mock_json(items, document, depth + 1)]
    
    elif schema_type == "string":
        if "enum" in schema:
            return schema["enum"][0]
        if schema.get("format") == "date-time":
            return "2026-06-26T09:00:00Z"
        return "string"
    
    elif schema_type == "integer" or schema_type == "number":
        return 0
    
    elif schema_type == "boolean":
        return True
        
    return None

def extract_schema_details(schema: Dict[str, Any], document: Dict[str, Any]) -> Dict[str, Any]:
    """Generates clean structure details of a schema."""
    if "$ref" in schema:
        resolved = resolve_ref(schema["$ref"], document)
        ref_name = schema["$ref"].split("/")[-1]
        return {"type": ref_name, "properties": schema_to_mock_json(resolved, document)}
    return {"type": schema.get("type", "object"), "properties": schema_to_mock_json(schema, document)}

def parse_openapi(content: str) -> Dict[str, Any]:
    """
    Parses OpenAPI 3.x and Swagger 2.0 specifications.
    Extracts all metadata and generates EndpointSchema models.
    """
    # Load document
    document: Dict[str, Any] = {}
    try:
        document = json.loads(content)
    except json.JSONDecodeError:
        try:
            document = yaml.safe_load(content)
        except Exception as e:
            raise ValueError(f"Failed to parse OpenAPI document. Not valid JSON or YAML: {e}")

    if not isinstance(document, dict):
        raise ValueError("OpenAPI document root must be an object.")

    # 1. API Metadata
    info = document.get("info", {})
    api_name = info.get("title", "Unknown API")
    api_version = info.get("version", "1.0.0")

    # Base URL extraction
    base_url = "/"
    if "servers" in document and document["servers"]:
        base_url = document["servers"][0].get("url", "/")
    elif "host" in document:
        host = document.get("host", "")
        base_path = document.get("basePath", "")
        schemes = document.get("schemes", ["http"])
        base_url = f"{schemes[0]}://{host}{base_path}"

    # Auth details
    auth_types = []
    # OpenAPI v3 securitySchemes
    components = document.get("components", {})
    security_schemes = components.get("securitySchemes", {})
    # Swagger v2 securityDefinitions
    if not security_schemes:
        security_schemes = document.get("securityDefinitions", {})

    for name, scheme in security_schemes.items():
        auth_types.append(f"{name} ({scheme.get('type', 'unknown')})")
    
    global_auth_type = ", ".join(auth_types) if auth_types else "None"

    # Global Security Requirements
    global_security = document.get("security", [])

    # 2. Parse Endpoints
    endpoints = []
    paths = document.get("paths", {})
    
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
            
        # Common parameters across all HTTP methods in this path
        common_parameters = path_item.get("parameters", [])

        for method, op in path_item.items():
            if method.lower() not in ("get", "post", "put", "delete", "patch", "options", "head"):
                continue

            op_id = op.get("operationId", f"{method}_{path.replace('/', '_').strip('_')}")
            description = op.get("description", op.get("summary", ""))
            
            # Authentication requirement
            op_security = op.get("security", global_security)
            auth_required = len(op_security) > 0

            # Parameters
            op_params = op.get("parameters", [])
            all_params = common_parameters + op_params
            
            headers = []
            query_params = []
            path_params = []

            for p in all_params:
                # Resolve parameter reference if any
                if "$ref" in p:
                    p = resolve_ref(p["$ref"], document)

                p_in = p.get("in", "")
                p_name = p.get("name", "")
                p_required = p.get("required", False)
                p_desc = p.get("description", "")
                p_schema = p.get("schema", {}) if "schema" in p else p

                param_info = {
                    "name": p_name,
                    "type": p_schema.get("type", "string") if isinstance(p_schema, dict) else "string",
                    "required": p_required,
                    "description": p_desc
                }

                if p_in == "header":
                    headers.append(param_info)
                elif p_in == "query":
                    query_params.append(param_info)
                elif p_in == "path":
                    path_params.append(param_info)

            # Request Body
            request_body = None
            sample_request = None
            if "requestBody" in op: # OpenAPI 3.x
                req_body_def = op["requestBody"]
                if "$ref" in req_body_def:
                    req_body_def = resolve_ref(req_body_def["$ref"], document)
                content_types = req_body_def.get("content", {})
                json_content = content_types.get("application/json", {})
                if "schema" in json_content:
                    schema = json_content["schema"]
                    request_body = extract_schema_details(schema, document)
                    mock_data = schema_to_mock_json(schema, document)
                    sample_request = json.dumps(mock_data, indent=2) if mock_data else None
            else: # Swagger 2.0 (Check for body parameter)
                for p in all_params:
                    if "$ref" in p:
                        p = resolve_ref(p["$ref"], document)
                    if p.get("in") == "body":
                        schema = p.get("schema", {})
                        request_body = extract_schema_details(schema, document)
                        mock_data = schema_to_mock_json(schema, document)
                        sample_request = json.dumps(mock_data, indent=2) if mock_data else None
                        break

            # Response Body
            response_body = None
            sample_response = None
            status_codes = []
            responses = op.get("responses", {})
            for code_str, resp in responses.items():
                if "$ref" in resp:
                    resp = resolve_ref(resp["$ref"], document)
                try:
                    code = int(code_str)
                    status_codes.append(code)
                except ValueError:
                    continue  # handles 'default' or other string status codes
                
                # Check for schema (v3 content -> application/json -> schema OR v2 schema)
                schema = None
                if "content" in resp:
                    json_content = resp["content"].get("application/json", {})
                    schema = json_content.get("schema")
                elif "schema" in resp:
                    schema = resp["schema"]

                if schema and code in (200, 201):
                    response_body = extract_schema_details(schema, document)
                    mock_data = schema_to_mock_json(schema, document)
                    sample_response = json.dumps(mock_data, indent=2) if mock_data else None

            endpoints.append(EndpointSchema(
                id=op_id,
                method=method.upper(),
                path=path,
                description=description,
                auth_required=auth_required,
                headers=headers,
                query_params=query_params,
                path_params=path_params,
                request_body=request_body,
                response_body=response_body,
                status_codes=status_codes,
                sample_request=sample_request,
                sample_response=sample_response
            ))

    return {
        "name": api_name,
        "version": api_version,
        "base_url": base_url,
        "auth_type": global_auth_type,
        "endpoints": endpoints
    }
