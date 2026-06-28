import os
import uuid
import logging
from typing import Dict, Any, List
from backend.ai.gemini_client import generate_sdk_wrapper
from backend.utils.zip_helper import create_project_zip

logger = logging.getLogger(__name__)

# Fallback templates for 10 programming languages if Gemini is unavailable
FALLBACK_TEMPLATES = {
    "python": {
        "wrapper": '''import requests
import time
import logging

class APIClient:
    """Client for {api_name} v{api_version}."""
    
    def __init__(self, base_url="{base_url}", token=None, timeout=30):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.session = requests.Session()
        if token:
            self.session.headers.update({{"Authorization": f"Bearer {{token}}"}})\n
    def _request(self, method, path, **kwargs):
        url = f"{{self.base_url}}{{path}}"
        retries = 3
        backoff = 1.0
        
        for attempt in range(retries):
            try:
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
                if response.status_code == 429:
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    raise RuntimeError(f"Request failed: {{e}}")
                time.sleep(backoff)
                backoff *= 2\n''',
        "readme": "# {api_name} Python Client SDK\n\nFallback Python SDK client installation and basic usage guide."
    },
    "javascript": {
        "wrapper": '''class APIClient {
    constructor(baseUrl = "{base_url}", token = null) {
        this.baseUrl = baseUrl.replace(/\\/$/, "");
        this.token = token;
    }
    
    async request(method, path, body = null, headers = {}) {
        const url = `${this.baseUrl}${path}`;
        const requestHeaders = {
            "Content-Type": "application/json",
            ...headers
        };
        if (this.token) {
            requestHeaders["Authorization"] = `Bearer ${this.token}`;
        }
        
        const response = await fetch(url, {
            method,
            headers: requestHeaders,
            body: body ? JSON.stringify(body) : null
        });
        
        if (!response.ok) {
            throw new Error(`HTTP Error: ${response.status}`);
        }
        return await response.json();
    }
}''',
        "readme": "# {api_name} JS Client SDK\n\nFallback JavaScript SDK client usage guide."
    }
}

# Add basic skeletons for other 8 languages
for lang in ("java", "typescript", "c#", "go", "php", "ruby", "kotlin", "swift"):
    if lang not in FALLBACK_TEMPLATES:
        FALLBACK_TEMPLATES[lang] = {
            "wrapper": f"// Fallback client class for {lang}\n// Please configure GEMINI_API_KEY to generate standard wrapper.",
            "readme": f"# SDK Client for {lang}\nFallback README config guide."
        }

def format_fallback(language: str, api_name: str, api_version: str, base_url: str) -> Dict[str, str]:
    """Generates simple mock wrapper for the API if AI is unavailable."""
    templates = FALLBACK_TEMPLATES.get(language.lower(), FALLBACK_TEMPLATES["python"])
    wrapper_code = templates["wrapper"].format(
        api_name=api_name,
        api_version=api_version,
        base_url=base_url
    )
    readme_code = templates["readme"].format(api_name=api_name)
    return {"wrapper_code": wrapper_code, "readme_code": readme_code}

def build_sdk_project(
    api_id: str,
    api_name: str,
    api_version: str,
    base_url: str,
    language: str,
    api_details: Dict[str, Any]
) -> Dict[str, str]:
    """
    Orchestrates building SDK code files, structure them in the workspace,
    and packaging as a zip file.
    """
    project_id = str(uuid.uuid4())
    
    try:
        # Call Gemini SDK synthesis
        sdk_data = generate_sdk_wrapper(language, api_details)
        wrapper_code = sdk_data["wrapper_code"]
        readme_code = sdk_data["readme_code"]
    except Exception as e:
        logger.warning(f"AI SDK generation failed, using fallback templates: {e}")
        fallback_data = format_fallback(language, api_name, api_version, base_url)
        wrapper_code = fallback_data["wrapper_code"]
        readme_code = fallback_data["readme_code"]

    # Target directory mapping inside workspace
    gen_dir = os.path.abspath(os.path.join("generated", api_id, language))
    os.makedirs(gen_dir, exist_ok=True)

    # Determine code file suffix
    ext = {
        "python": "py",
        "javascript": "js",
        "typescript": "ts",
        "java": "java",
        "c#": "cs",
        "go": "go",
        "php": "php",
        "ruby": "rb",
        "kotlin": "kt",
        "swift": "swift"
    }.get(language.lower(), "txt")

    code_file_name = f"client.{ext}"
    if language.lower() == "go":
        code_file_name = "client.go"
    elif language.lower() == "java":
        code_file_name = "APIClient.java"

    # Write source code files to disk
    code_path = os.path.join(gen_dir, code_file_name)
    readme_path = os.path.join(gen_dir, "README.md")
    
    with open(code_path, "w", encoding="utf-8") as f:
        f.write(wrapper_code)

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_code)

    # Compile ZIP file in downloads folder
    downloads_dir = os.path.abspath("downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    
    # Sanitize API name to ensure OS filename safety (removes invalid chars like |, :, /)
    import re
    sanitized_name = re.sub(r'[^a-zA-Z0-9\-_]', '_', api_name)
    sanitized_name = re.sub(r'_+', '_', sanitized_name).strip('_').lower()
    
    zip_filename = f"{sanitized_name}_{language.lower()}_sdk.zip"
    zip_path = os.path.join(downloads_dir, zip_filename)
    
    create_project_zip(gen_dir, zip_path)

    # Return structure
    relative_zip_path = os.path.relpath(zip_path, os.path.abspath("."))
    
    return {
        "id": project_id,
        "wrapper_code": wrapper_code,
        "readme_code": readme_code,
        "zip_path": relative_zip_path
    }
