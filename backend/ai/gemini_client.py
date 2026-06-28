import os
import json
import logging
import requests
import google.generativeai as genai
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

def get_gemini_client():
    """Initializes and returns the generative model."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured in the environment or settings.")
    genai.configure(api_key=api_key)
    # Using gemini-2.5-flash as the default model
    return genai.GenerativeModel("gemini-2.5-flash")

def clean_json_response(text: str) -> str:
    """
    Strips markdown code block wrappers (e.g. ```json ... ```) 
    from LLM responses to ensure valid JSON parsing.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned

def call_groq(prompt: str, json_mode: bool = False) -> str:
    """
    HTTP-based fallback caller to the Groq API.
    Used when Gemini API hits daily quota limits.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        raise ValueError("Groq API key not configured in environment (GROQ_API_KEY is missing).")
        
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.1-8b-instant",  # Extremely fast and free-tier friendly model
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }
    
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
        
    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers,
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            raise RuntimeError(f"Groq API returned HTTP {response.status_code}: {response.text}")
    except Exception as e:
        logger.error(f"Groq API call exception: {e}")
        raise RuntimeError(f"Groq API call failed: {str(e)}")

def analyze_unstructured_docs(clean_text: str, use_case: Optional[str] = None) -> Dict[str, Any]:
    """
    Calls Gemini API to parse unstructured documentation text.
    Falls back to Groq API if Gemini fails.
    """
    use_case_prompt = f"Target Use Case: {use_case}\n" if use_case else ""
    prompt = (
        "You are an expert API documentation parser. "
        "Analyze the following unstructured API documentation text and extract all endpoints. "
        "Your response MUST be a valid JSON object matching this schema exactly:\n"
        "{\n"
        "  \"name\": \"Name of the API\",\n"
        "  \"version\": \"API version (default: 1.0.0)\",\n"
        "  \"base_url\": \"API base URL (default: /)\",\n"
        "  \"auth_type\": \"Authentication method detected (e.g. Bearer Token, API Key, Basic Auth, None)\",\n"
        "  \"endpoints\": [\n"
        "    {\n"
        "      \"id\": \"unique_operation_id\",\n"
        "      \"method\": \"HTTP Method (GET, POST, PUT, DELETE, PATCH)\",\n"
        "      \"path\": \"Relative path from base URL\",\n"
        "      \"description\": \"Description of what this endpoint does\",\n"
        "      \"auth_required\": true/false,\n"
        "      \"headers\": [{\"name\": \"Header-Name\", \"type\": \"string\", \"required\": true, \"description\": \"description\"}],\n"
        "      \"query_params\": [{\"name\": \"param\", \"type\": \"string/integer/boolean\", \"required\": false, \"description\": \"description\"}],\n"
        "      \"path_params\": [{\"name\": \"param\", \"type\": \"string\", \"required\": true, \"description\": \"description\"}],\n"
        "      \"request_body\": {}, // JSON schema structure or example of request body\n"
        "      \"response_body\": {}, // JSON schema structure or example of response body\n"
        "      \"status_codes\": [200, 400, 401],\n"
        "      \"sample_request\": \"JSON string of sample request payload or empty string\",\n"
        "      \"sample_response\": \"JSON string of sample response payload\"\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"{use_case_prompt}"
        "Documentation Content:\n"
        f"{clean_text}"
    )

    # Helper to parse and secure output dictionary format
    def parse_dict(text_content: str) -> Dict[str, Any]:
        cleaned = clean_json_response(text_content)
        data = json.loads(cleaned)
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        if not isinstance(data, dict):
            raise TypeError("AI response did not resolve to a dictionary schema.")
        return data

    # 1. Try Gemini
    try:
        model = get_gemini_client()
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return parse_dict(response.text)
    except Exception as e:
        logger.error(f"Gemini API structured parsing failure: {e}. Attempting Groq fallback...")
        # 2. Try Groq
        if os.getenv("GROQ_API_KEY"):
            try:
                res_text = call_groq(prompt, json_mode=True)
                return parse_dict(res_text)
            except Exception as ge:
                logger.error(f"Groq fallback structured parsing failed: {ge}")
        raise RuntimeError(f"Gemini and Groq analysis failed: {str(e)}")

def generate_api_summary(api_details: Dict[str, Any], use_case: Optional[str] = None) -> Dict[str, Any]:
    """
    Generates a high-level API summary, authentication flow, rate limits details, 
    pagination and SDK recommendation. Falls back to Groq if Gemini fails.
    """
    use_case_prompt = f"The user's targeted use case: {use_case}\n" if use_case else ""
    prompt = (
        "You are an API integration expert. Review the following API details and build an summary report. "
        "Return a JSON object containing the fields below:\n"
        "{\n"
        "  \"summary\": \"A professional markdown overview of what the API does, its core capabilities, and general structure.\",\n"
        "  \"sdk_recommendation\": \"A markdown-formatted evaluation advising the developer on whether to use official SDKs (if any are known to exist) or construct a custom REST implementation, directly referencing their use case.\",\n"
        "  \"auth_flow\": \"Markdown detailing how authentication works, how tokens are fetched or passed, and which keys go into headers/query.\",\n"
        "  \"rate_limits\": \"Rate limit info, retry policies, or typical industry backing-off thresholds for this type of service.\",\n"
        "  \"pagination\": \"Pagination methods observed (e.g. limit/offset, cursor-based, page-based) and how they should be handled.\"\n"
        "}\n\n"
        f"{use_case_prompt}"
        f"API JSON Metadata:\n{json.dumps(api_details, indent=2, default=str)}"
    )

    # Default fallback data structure
    default_summary = {
        "summary": "AI summary failed to load.",
        "sdk_recommendation": "Use REST implementation.",
        "auth_flow": "Refer to official documentation.",
        "rate_limits": "Not detected.",
        "pagination": "Not detected."
    }

    def parse_dict(text_content: str) -> Dict[str, Any]:
        cleaned = clean_json_response(text_content)
        data = json.loads(cleaned)
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        if not isinstance(data, dict):
            raise TypeError("AI response did not resolve to a dictionary schema.")
        return data

    # 1. Try Gemini
    try:
        model = get_gemini_client()
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return parse_dict(response.text)
    except Exception as e:
        logger.error(f"Gemini API summary generation failure: {e}. Attempting Groq fallback...")
        # 2. Try Groq
        if os.getenv("GROQ_API_KEY"):
            try:
                res_text = call_groq(prompt, json_mode=True)
                return parse_dict(res_text)
            except Exception as ge:
                logger.error(f"Groq fallback summary generation failed: {ge}")
        return default_summary

def generate_sdk_wrapper(language: str, api_details: Dict[str, Any]) -> Dict[str, str]:
    """
    Uses Gemini to generate the wrapper client code and a matching installation/usage README.md.
    Falls back to Groq if Gemini fails.
    """
    prompt = (
        f"You are a Senior SDK Architect. Generate a high-quality, production-ready REST client wrapper "
        f"for the API detailed below, written in the '{language}' language.\n\n"
        "The generated wrapper client MUST include the following:\n"
        "1. Authentication handling (API Keys, Bearer tokens, or Basic Auth as specified by the API).\n"
        "2. Complete HTTP client implementation utilizing idiomatic standard or popular libraries (e.g., requests in Python, axios/fetch in JS/TS, Net::HTTP in Ruby, etc.).\n"
        "3. Advanced error handling & Custom Exception classes.\n"
        "4. Retry logic with exponential backoff for handling 429/5xx responses.\n"
        "5. Logging statements of requests/responses for easier debugging.\n"
        "6. Automatic pagination helper methods if pagination is detected.\n"
        "7. Configurable timeouts, custom headers, and environment variable initialization.\n"
        "8. Complete, clear docstrings/type annotations for all public endpoints.\n\n"
        "Your response MUST be a JSON object matching this schema exactly:\n"
        "{\n"
        "  \"wrapper_code\": \"Complete wrapper/client source code structure.\",\n"
        "  \"readme_code\": \"A thorough, user-facing README.md document describing installation, initialization, environment configuration (.env), and complete code examples of how to initialize and invoke the main operations.\"\n"
        "}\n\n"
        f"API Details:\n{json.dumps(api_details, indent=2, default=str)}"
    )

    def parse_dict(text_content: str) -> Dict[str, Any]:
        cleaned = clean_json_response(text_content)
        data = json.loads(cleaned)
        if isinstance(data, list) and len(data) > 0:
            data = data[0]
        if not isinstance(data, dict):
            raise TypeError("AI response did not resolve to a dictionary schema.")
        return data

    # 1. Try Gemini
    try:
        model = get_gemini_client()
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        return parse_dict(response.text)
    except Exception as e:
        logger.error(f"Gemini API wrapper generation failure: {e}. Attempting Groq fallback...")
        # 2. Try Groq
        if os.getenv("GROQ_API_KEY"):
            try:
                res_text = call_groq(prompt, json_mode=True)
                return parse_dict(res_text)
            except Exception as ge:
                logger.error(f"Groq fallback wrapper generation failed: {ge}")
        raise RuntimeError(f"Failed to generate wrapper using Gemini or Groq: {str(e)}")

def ask_copilot(api_details: Dict[str, Any], wrapper_code: str, chat_history: List[Dict[str, str]], question: str) -> str:
    """
    Invokes Gemini to act as an API Copilot. Falls back to Groq if Gemini fails.
    """
    # Format chat history for context
    history_str = ""
    for msg in chat_history:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_str += f"{role}: {msg['content']}\n"
        
    system_instruction = (
        f"You are the Smart DevTool AI Copilot, a developer assistant specialized in the API '{api_details.get('name', 'API')}' v{api_details.get('version', '1.0.0')}.\n"
        f"The API documentation URL is: {api_details.get('url', 'Not configured')}\n"
        "Here are the details of the parsed API endpoints:\n"
        f"{json.dumps(api_details, indent=2, default=str)}\n\n"
        "Here is the generated SDK client wrapper code:\n"
        f"{wrapper_code or 'No wrapper code generated yet.'}\n\n"
        "CRITICAL RULES:\n"
        "1. You must answer questions ONLY about this API, its documentation URL, its endpoints, parameters, authentication method, or the generated wrapper SDK client library.\n"
        "2. If the user asks ANY question or makes ANY request that is unrelated to this API, the documentation URL, or the wrapper client code, you MUST politely refuse to answer. Do not answer general knowledge, poems, math problems, unrelated coding requests, etc.\n"
        "3. Example response for unrelated queries: 'I am the AI Copilot for this API integration project. I can only assist you with details and code related to this parsed API and its SDK wrapper.'\n"
        "4. Keep your answers concise, accurate, and helpful for software developers.\n"
    )
    
    prompt = (
        f"{system_instruction}\n"
        f"Chat History:\n{history_str}\n"
        f"User Question: {question}\n"
        "Assistant Response:"
    )
    
    # 1. Try Gemini
    try:
        model = get_gemini_client()
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Gemini Copilot execution failed: {e}. Attempting Groq fallback...")
        # 2. Try Groq
        if os.getenv("GROQ_API_KEY"):
            try:
                return call_groq(prompt, json_mode=False)
            except Exception as ge:
                logger.error(f"Groq fallback copilot failed: {ge}")
        return f"Error communicating with AI Copilot: {str(e)}"
