import requests
import logging
import time
import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from backend.utils.security import validate_url

logger = logging.getLogger(__name__)

COMMON_SPEC_SUFFIXES = [
    "/swagger.json",
    "/openapi.json",
    "/v2/api-docs",
    "/v3/api-docs",
    "/swagger.yaml",
    "/swagger.yml",
    "/openapi.yaml",
    "/openapi.yml",
    "/api-docs"
]

def fetch_with_retry(url: str, headers: dict, timeout: int = 15) -> requests.Response:
    """
    Fetches the URL with up to 3 retries and exponential backoff.
    Handles connection errors, SSL issues, timeouts, and redirect chains.
    """
    retries = 3
    backoff = 1.0
    
    for attempt in range(retries):
        try:
            # verify=False is used for local self-signed certs testing, but we suppress warnings
            # We enforce a clear timeout and allow redirects
            response = requests.get(url, headers=headers, timeout=timeout, verify=False, allow_redirects=True)
            return response
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError, requests.exceptions.Timeout) as ne:
            if attempt == retries - 1:
                logger.error(f"Network error on final attempt for {url}: {ne}")
                raise ne
            logger.warning(f"Attempt {attempt + 1} failed for {url} ({ne}). Retrying in {backoff}s...")
            time.sleep(backoff)
            backoff *= 2
            
    raise RuntimeError("Failed to connect after retries.")

def extract_spec_url_from_html(html: str, base_url: str) -> str:
    """
    Scrapes HTML content for Swagger/Redoc spec URLs or JSON links.
    Also fetches linked scripts (e.g. swagger-initializer.js) to inspect config code.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        )
    }

    # Helper function to run regex on string
    def find_in_text(text: str) -> str:
        swagger_url_patterns = [
            r'''defaultDefinitionUrl\s*=\s*['"]([^'"]+)['"]''',
            r'''url\s*:\s*['"]([^'"]*(?:swagger|openapi|api-docs)[^'"]*\.(?:json|yaml|yml))['"]''',
            r'''url\s*:\s*['"]([^'"]+\.json)['"]''',
            r'''spec-url\s*=\s*['"]([^'"]+)['"]''',
            r'''spec\s*:\s*['"]([^'"]+)['"]''',
            r'''["']url["']\s*:\s*["']([^"']+)["']'''
        ]
        for pattern in swagger_url_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                found_url = match.group(1)
                # Filter out placeholders
                if found_url and not found_url.startswith("http") and not found_url.endswith("js"):
                    resolved = urljoin(base_url, found_url)
                    return resolved
                elif found_url.startswith("http"):
                    return found_url
        return ""

    # Check main HTML first
    url_found = find_in_text(html)
    if url_found:
        return url_found

    # Check external scripts
    try:
        soup = BeautifulSoup(html, "html.parser")
        for script in soup.find_all("script", src=True):
            src = script["src"]
            # Exclude standard third-party CDNs (google tags, google analytics, etc.) to avoid spam
            if any(term in src.lower() for term in ("swagger", "initializer", "redoc", "config")) or not src.startswith("http"):
                script_url = urljoin(base_url, src)
                logger.info(f"Checking external script config: {script_url}")
                try:
                    resp = requests.get(script_url, headers=headers, timeout=5, verify=False)
                    if resp.status_code == 200:
                        url_found = find_in_text(resp.text)
                        if url_found:
                            logger.info(f"Located spec URL inside script {script_url}: {url_found}")
                            return url_found
                except Exception as script_err:
                    logger.debug(f"Failed to fetch script {script_url}: {script_err}")
    except Exception as e:
        logger.warning(f"Soup script tag parsing failed: {e}")

    # Check BeautifulSoup anchor tags as fallback
    try:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if any(term in href.lower() for term in ("swagger.json", "openapi.json", "swagger.yaml", "api-docs")) or href.endswith((".json", ".yaml", ".yml")):
                resolved = urljoin(base_url, href)
                return resolved
    except Exception as e:
        logger.warning(f"Soup anchor tag parsing failed: {e}")

    return ""


def try_common_endpoints_fallback(url: str, headers: dict) -> str:
    """
    Queries common OpenAPI endpoints relative to the domain or base path.
    Returns the spec content if found, empty string otherwise.
    """
    parsed = urlparse(url)
    base_domain = f"{parsed.scheme}://{parsed.netloc}"
    
    # Also try parent path
    parent_path = "/".join(parsed.path.split("/")[:-1])
    parent_url = f"{parsed.scheme}://{parsed.netloc}{parent_path}"

    candidates = []
    # Generate check URLs
    for suffix in COMMON_SPEC_SUFFIXES:
        candidates.append(urljoin(parent_url + "/", suffix.lstrip("/")))
        candidates.append(urljoin(base_domain, suffix.lstrip("/")))

    # De-duplicate list preserving order
    checked_urls = []
    for c in candidates:
        if c not in checked_urls and validate_url(c):
            checked_urls.append(c)

    for check_url in checked_urls:
        logger.info(f"Fallback probe: checking common path {check_url}...")
        try:
            resp = requests.get(check_url, headers=headers, timeout=5, verify=False)
            if resp.status_code == 200:
                content = resp.text
                # Verify it looks like JSON or YAML spec before returning
                if "openapi" in content or "swagger" in content or "paths" in content:
                    logger.info(f"Success! Located working OpenAPI specification at: {check_url}")
                    return content
        except Exception:
            continue
            
    return ""

def fetch_documentation(url: str) -> str:
    """
    Fetches API documentation.
    - Validates URL safety (SSRF).
    - Downloads page with retry logic.
    - Resolves single-page app Swagger UI / Redoc specifications.
    - Queries relative endpoints on 404 errors.
    - Employs Playwright rendering if required.
    """
    if not validate_url(url):
        raise ValueError("The provided documentation URL could not be accessed. (Blocked by SSRF validation).")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/json,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    response = None
    try:
        response = fetch_with_retry(url, headers)
    except Exception as e:
        # If the main URL connection timed out or failed, try common paths before throwing error
        logger.warning(f"Connection to primary URL failed. Triggering common paths probe... {e}")
        fallback_content = try_common_endpoints_fallback(url, headers)
        if fallback_content:
            return fallback_content
        raise ValueError("The provided documentation URL could not be accessed.")

    # Handle HTTP Error Cases
    if response.status_code == 404:
        logger.warning("Primary documentation URL returned 404. Running fallback paths...")
        fallback_content = try_common_endpoints_fallback(url, headers)
        if fallback_content:
            return fallback_content
        raise ValueError("OpenAPI specification not found. (Primary URL returned 404).")
        
    elif response.status_code in (401, 403):
        raise ValueError("Access to the documentation URL was forbidden (HTTP 401/403).")
        
    elif response.status_code >= 500:
        raise ValueError(f"The documentation server returned a server error (HTTP {response.status_code}).")

    content = response.text
    content_type = response.headers.get("Content-Type", "").lower()

    # If direct JSON or YAML specification, return directly
    if "json" in content_type or "yaml" in content_type or "yml" in content_type:
        return content

    # If it's HTML, check if it is a Swagger/Redoc UI wrapping a JSON spec URL
    if "html" in content_type or content.strip().startswith("<"):
        # Search script configurations for direct spec URLs
        spec_url = extract_spec_url_from_html(content, url)
        if spec_url:
            try:
                spec_response = fetch_with_retry(spec_url, headers)
                if spec_response.status_code == 200:
                    return spec_response.text
            except Exception as se:
                logger.warning(f"Failed to download spec from extracted link {spec_url}: {se}. Proceeding with HTML parse.")

        # Playwright fallback for dynamic JavaScript-rendered pages
        is_spa = ("<div id=\"swagger-ui\">" in content or 
                  "<redoc" in content or 
                  "redoc-container" in content or 
                  "swagger-ui-container" in content or
                  "swaggerui" in content.lower())
                  
        if is_spa:
            try:
                from playwright.sync_api import sync_playwright
                logger.info("SPA detected. Launching Playwright to render documentation...")
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    rendered_content = page.content()
                    browser.close()
                    
                    # Search inside rendered content for spec URLs
                    spec_url_rendered = extract_spec_url_from_html(rendered_content, url)
                    if spec_url_rendered:
                        spec_resp = fetch_with_retry(spec_url_rendered, headers)
                        if spec_resp.status_code == 200:
                            return spec_resp.text
                            
                    return rendered_content
            except Exception as pe:
                logger.warning(f"Playwright rendering failed: {pe}. Returning raw HTML content.")

    return content
