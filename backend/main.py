import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment configuration
load_dotenv()

from backend.database.connection import init_db
from backend.routes import health, analyze, generate, download

# Initialize sqlite tables on load
init_db()

app = FastAPI(
    title="Smart DevTool API",
    description="AI-Powered API Integration Assistant Backend Service",
    version="1.0.0"
)

# Set up CORS middleware to allow Streamlit UI connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health.router, tags=["Health"])
app.include_router(analyze.router, tags=["Analysis"])
app.include_router(generate.router, tags=["Code Generation"])
app.include_router(download.router, tags=["Downloads"])

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    # Run uvicorn server
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=True)
