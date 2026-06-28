from bs4 import BeautifulSoup
import re
import logging
from typing import Dict, Any, List
from backend.models.schemas import EndpointSchema

logger = logging.getLogger(__name__)

def extract_clean_text(html_content: str) -> str:
    """
    Cleans raw HTML by stripping scripting tags, styles, sidebars, and navigation,
    and returns a clean, token-efficient text string for AI ingestion.
    """
    # If the content is markdown already, we don't need BeautifulSoup parsing
    if not html_content.strip().startswith("<") and ("#" in html_content or "**" in html_content):
        return html_content

    try:
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Remove noisy tags
        for element in soup(["script", "style", "nav", "footer", "header", "svg", "noscript", "iframe", "aside"]):
            element.extract()
            
        # Get text
        text = soup.get_text(separator="\n")
        
        # Clean whitespaces
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = "\n".join(chunk for chunk in chunks if chunk)
        
        # Cap length at 50,000 chars to prevent token overflow while keeping major context
        return clean_text[:50000]
    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        return html_content[:20000]

def local_static_html_parser(html_content: str) -> Dict[str, Any]:
    """
    Statically scrapes HTML content to extract API name and endpoints using regex
    as a robust local fallback when Gemini API is rate-limited.
    """
    api_name = "Static Scraped API"
    endpoints = []
    
    # 1. Extract API Name from <title> tag
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        title_tag = soup.find("title")
        if title_tag and title_tag.text.strip():
            raw_title = title_tag.text.strip()
            # Clean title (remove common documentation page suffixes)
            api_name = re.sub(r'(\s*-\s*|\s*\|\s*)(docs|documentation|api|developer|portal|home).*$', '', raw_title, flags=re.IGNORECASE)
            api_name = api_name.strip()
    except Exception:
        pass

    # 2. Extract clean text to run regex scanning
    clean_text = extract_clean_text(html_content)
    
    # Scan for common patterns like: GET /api/users or POST /posts
    pattern = r'\b(GET|POST|PUT|DELETE|PATCH)\b[\s:]*(/[a-zA-Z0-9_\-\{\}/]*)'
    matches = re.findall(pattern, clean_text)
    
    seen = set()
    for method, path in matches:
        path = path.strip()
        # Exclude root redirects, empty routes, and static assets
        if path == "/" or len(path) < 3 or path.endswith((".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".ico")):
            continue
            
        key = (method.upper(), path)
        if key not in seen:
            seen.add(key)
            endpoints.append({
                "method": method.upper(),
                "path": path,
                "description": f"Statically extracted endpoint from {api_name} documentation.",
                "auth_required": False,
                "headers": [],
                "query_params": [],
                "path_params": [],
                "request_body": {},
                "response_body": {},
                "status_codes": [200],
                "sample_request": "",
                "sample_response": ""
            })

    # If no endpoints found using direct HTTP methods, scan for general path strings
    if not endpoints:
        api_paths = re.findall(r'/[a-zA-Z0-9_\-\{\}/]+/?[a-zA-Z0-9_\-\{\}/]*', clean_text)
        for path in api_paths:
            path = path.strip()
            if any(term in path.lower() for term in ("api", "v1", "v2", "users", "posts", "comments", "todos", "fact", "weather", "coins", "breeds")) and not path.endswith((".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".ico")):
                if len(path) > 3 and path not in [e["path"] for e in endpoints]:
                    endpoints.append({
                        "method": "GET",
                        "path": path,
                        "description": f"Statically inferred query path from {api_name}.",
                        "auth_required": False,
                        "headers": [],
                        "query_params": [],
                        "path_params": [],
                        "request_body": {},
                        "response_body": {},
                        "status_codes": [200],
                        "sample_request": "",
                        "sample_response": ""
                    })

    # Cap to top 25 endpoints for UI performance
    endpoints = endpoints[:25]

    return {
        "name": api_name or "Statically Extracted API",
        "version": "1.0.0",
        "base_url": "/",
        "auth_type": "None",
        "endpoints": endpoints
    }

def parse_html_or_markdown(content: str, use_case: str = None, gemini_analyzer=None) -> Dict[str, Any]:
    """
    Cleans unstructured HTML/Markdown and delegates endpoint structure extraction
    to the Gemini AI service. Falls back to static regex scraper on Gemini errors.
    """
    clean_text = extract_clean_text(content)
    
    if not gemini_analyzer:
        # Local static scraper if analyzer is not passed
        return local_static_html_parser(content)

    try:
        # Ask Gemini to parse the clean text
        result = gemini_analyzer(clean_text, use_case)
        return result
    except Exception as e:
        logger.warning(f"Gemini unstructured parsing failed: {e}. Executing local static extraction fallback...")
        return local_static_html_parser(content)

