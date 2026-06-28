import json
import yaml
import re

def detect_documentation_type(content: str) -> str:
    """
    Detects the format of the provided API documentation string.
    Supported types: openapi, swagger, html, markdown, graphql, unstructured
    """
    cleaned_content = content.strip()

    # 1. Check for JSON format
    if (cleaned_content.startswith("{") and cleaned_content.endswith("}")) or \
       (cleaned_content.startswith("[") and cleaned_content.endswith("]")):
        try:
            data = json.loads(cleaned_content)
            if isinstance(data, dict):
                if "openapi" in data:
                    return "openapi"
                if "swagger" in data:
                    return "swagger"
                if "__schema" in data or "data" in data and "__schema" in data["data"]:
                    return "graphql"
        except json.JSONDecodeError:
            pass

    # 2. Check for OpenAPI / Swagger YAML structure
    if "openapi:" in cleaned_content or "swagger:" in cleaned_content:
        try:
            # Try to load a tiny portion or full text using safe_load
            data = yaml.safe_load(cleaned_content[:20000])  # limit parsing size for safety
            if isinstance(data, dict):
                if "openapi" in data:
                    return "openapi"
                if "swagger" in data:
                    return "swagger"
        except Exception:
            pass

    # 3. Check for HTML structure
    if "<html" in cleaned_content.lower() or "<body" in cleaned_content.lower() or "<!doctype html" in cleaned_content.lower():
        return "html"

    # 4. Check for GraphQL Schema Definition Language (SDL)
    graphql_keywords = ["type Query", "type Mutation", "schema {", "type Subscription", "input "]
    if any(kw in cleaned_content for kw in graphql_keywords):
        return "graphql"

    # 5. Check for Markdown
    # Matches common markdown headers: #, ##, ### or bold text patterns
    markdown_headers = re.findall(r'^#{1,6}\s+\w+', cleaned_content, re.MULTILINE)
    if markdown_headers or "**" in cleaned_content or "```" in cleaned_content:
        return "markdown"

    return "unstructured"
