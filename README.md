# Smart DevTool – AI-Powered API Integration Assistant

Smart DevTool is an advanced full-stack developer acceleration platform designed to automate web API analysis and integration. By supplying a raw API documentation link, the platform ingests, resolves, parses, and converts it into custom-synthesized client library wrappers (SDKs) across 10 programming languages, complete with pagination, retry heuristics, logging, and environment configurations.

---

## 🚀 Features

- **Document Parsing Engine**: Automatically parses Swagger specifications, OpenAPI schemas (JSON/YAML), GraphQL SDL (Schema Definition Language), or raw unstructured HTML web documentation and Markdown files.
- **SSRF Security Protection**: Validates and restricts target domains to protect against Server-Side Request Forgeries.
- **Intelligent LLM Analysis**: Harnesses Google Gemini API for deep documentation analysis, parsing unstructured text, generating semantic summaries, and crafting client wrapper integration advice.
- **10-Language Client SDK Synthesis**: Generates full production-ready SDKs for:
  - Python (requests)
  - JavaScript (fetch)
  - TypeScript (axios)
  - Java (HttpClient)
  - C# (HttpClient)
  - Go (net/http)
  - PHP (Guzzle)
  - Ruby (Net::HTTP)
  - Kotlin (OkHttp)
  - Swift (URLSession)
- **Interactive UI Dashboard**: Features a Postman-like interface where developers can query routes, read request/response schemas, filter endpoints by HTTP verb, and copy sample requests.
- **Downloads & History**: Keeps an SQLite database track of prior integrations, ready to download as packed client library ZIP packages.

---

## 🛠️ Technologies Used

### Backend
- **Python 3.10+**
- **FastAPI**: Asynchronous high-performance REST APIs.
- **Uvicorn**: ASGI server.
- **SQLite / SQLAlchemy**: Database tracking engine.
- **Google Generative AI**: Gemini LLM integration.
- **BeautifulSoup4 & Requests**: Static web page parsing.
- **Playwright**: JavaScript SPA (Single Page Application) rendering.

### Frontend
- **Streamlit**: SaaS dashboard web UI.
- **HTML5 & CSS3**: Tailored dark-theme stylesheets.

---

## 📂 Folder Structure

```
smart-devtool/
├── backend/
│   ├── main.py              # FastAPI server entrypoint
│   ├── routes/              # API router endpoints (/health, /analyze, /generate, /download)
│   ├── services/            # Fetchers and format detection helpers
│   ├── parsers/             # OpenAPI, HTML, and GraphQL parsing engines
│   ├── ai/                  # Gemini client interactions
│   ├── generators/          # Language-specific SDK compilers
│   ├── database/            # SQLite connection init
│   ├── utils/               # SSRF security and zip utilities
│   └── models/              # Pydantic validation models
├── frontend/
│   ├── app.py               # Streamlit router entrypoint
│   ├── pages/               # Setting, Generator, About, Dashboard views
│   ├── components/          # Custom styled components
│   └── styles/              # custom.css Dark styling overrides
├── generated/               # Directory containing generated source code files
├── downloads/               # Compiled project ZIP downloads
├── README.md                # System documentation
└── requirements.txt         # Project dependencies
```

---

## ⚙️ Installation & Running Instructions

### 1. Clone & Set Up Directory
Navigate to the directory:
```bash
cd c:\Users\SHANMATHY\OneDrive\Documents\Desktop\Smart_devtool
```

### 2. Install Dependencies
Initialize a virtual environment and install the required modules:
```bash
python -m venv venv
venv\Scripts\activate      # On Windows
pip install -r requirements.txt
```

*(Optional)* Install browser binaries if dynamic JS documentation loading via Playwright is needed:
```bash
playwright install chromium
```

### 3. Environment Configuration
Create a `.env` file in the root folder containing your Gemini API credentials:
```env
GEMINI_API_KEY="AIzaSyYourGeminiAPIKeyHere"
DATABASE_URL="sqlite:///backend/database/database.db"
PORT=8000
```

### 4. Run the Backend API Server
Start the FastAPI service:
```bash
uvicorn backend.main:app --port 8000 --reload
```
The documentation interactive Swagger docs will be live at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 5. Run the Frontend Dashboard
In a separate terminal shell, execute the Streamlit application:
```bash
streamlit run frontend/app.py
```
Open [http://localhost:8501](http://localhost:8501) to explore the system dashboard.

---

## 🔌 API Endpoints (Backend)

- **`GET /health`**: Returns system state, SQLite status, and Gemini configurations.
- **`POST /analyze`**: Accepts a JSON URL/Use Case and runs parsing heuristics.
- **`POST /generate`**: Accepts API ID and language selection, compiles client SDK, and builds ZIP archive.
- **`GET /download/{project_id}`**: Streams the generated SDK ZIP archive file payload as an attachment.

---

## 💻 Sample SDK Wrapper Usage (Python Example)

Below is an illustration of what the generated Python SDK class looks like:

```python
import requests
import time
import logging

class APIClient:
    """Client for Target API v1.0.0."""
    
    def __init__(self, base_url="https://api.example.com/v1", token=None, timeout=30):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})
            
    def get_pet_by_id(self, pet_id: int):
        """Find pet by ID."""
        return self._request("GET", f"/pet/{pet_id}")

    def _request(self, method, path, **kwargs):
        url = f"{self.base_url}{path}"
        # Exponential backoff retry loop
        retries = 3
        backoff = 1.0
        for attempt in range(retries):
            try:
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
                if response.status_code == 429: # Rate limit
                    time.sleep(backoff)
                    backoff *= 2
                    continue
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    raise RuntimeError(f"Request failed: {e}")
                time.sleep(backoff)
                backoff *= 2
```

---

## 📸 Dashboard Preview

*(Mockups sections placeholder)*
The interface utilizes linear card frames, Postman-colored operation badges, horizontal flow loaders, syntax-highlighted code panels, and full search filtering.
