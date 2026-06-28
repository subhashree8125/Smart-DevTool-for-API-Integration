import sys
import os

# Add parent directory to python path for modular module imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import requests
from dotenv import load_dotenv

# Set page config as the very first Streamlit call
st.set_page_config(
    page_title="Smart DevTool – AI-Powered API Integration Assistant",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load environment configuration
load_dotenv()

from frontend.components.ui import inject_custom_css
from frontend.pages import analyze, dashboard, generator, history, settings, about, copilot
from backend.database.connection import get_db_connection

# Initialize page state
if "page" not in st.session_state:
    # Check if there are existing APIs in database to choose default screen
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM apis;")
        count = cursor.fetchone()[0]
        conn.close()
        st.session_state.page = "Dashboard" if count > 0 else "Analyze API"
    except Exception:
        st.session_state.page = "Analyze API"

def main():
    # Inject premium styles
    inject_custom_css()

    # Sidebar Navigation Branding
    st.sidebar.markdown(
        """
        <div style="padding: 10px 0; text-align: center;">
            <h1 style="color: #3b82f6; font-size: 1.8rem; margin: 0; font-weight: 800; text-shadow: 0 0 10px rgba(59,130,246,0.2);">⚡ Smart DevTool</h1>
            <span style="color: #64748b; font-size: 0.85rem; font-weight: 500;">AI API Integration Assistant</span>
        </div>
        <hr style="border: 0; border-top: 1px solid #1e293b; margin: 15px 0;"/>
        """,
        unsafe_allow_html=True
    )

    # Sidebar options
    nav_options = [
        "Dashboard",
        "Analyze API",
        "Wrapper Generator",
        "Generated Projects",
        "AI Copilot",
        "Settings",
        "About"
    ]

    selected_page = st.sidebar.radio(
        "Navigation Menu",
        nav_options,
        index=nav_options.index(st.session_state.page) if st.session_state.page in nav_options else 1
    )
    
    # Update page state if manual change made
    if selected_page != st.session_state.page:
        st.session_state.page = selected_page

    st.sidebar.markdown("---")
    backend_url = st.sidebar.text_input("Backend API Base URL", value="http://127.0.0.1:8000", key="settings_backend_url_shared")
    
    # Quick health check in sidebar footer
    try:
        health_resp = requests.get(f"{backend_url}/health", timeout=2)
        if health_resp.status_code == 200:

            h_data = health_resp.json()
            gemini_configured = h_data.get("gemini_configured", False)
            
            status_color = "#10b981"
            status_text = "Backend Online"
            
            st.sidebar.markdown(
                f"""
                <div style="font-size: 0.8rem; color: #94a3b8;">
                    🔌 Connection: <span style="color: {status_color}; font-weight: 600;">{status_text}</span><br/>
                    🧠 Gemini: <span style="color: {'#10b981' if gemini_configured else '#ef4444'}; font-weight: 600;">{'Configured' if gemini_configured else 'Key Missing'}</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        else:
            st.sidebar.markdown("🔌 Connection: <span style='color: #ef4444; font-weight: 600;'>API Error</span>", unsafe_allow_html=True)
    except Exception:
        st.sidebar.markdown("🔌 Connection: <span style='color: #f59e0b; font-weight: 600;'>Offline</span>", unsafe_allow_html=True)

    # Page Routing Trigger
    if st.session_state.page == "Dashboard":
        dashboard.app()
    elif st.session_state.page == "Analyze API":
        analyze.app()
    elif st.session_state.page == "Wrapper Generator":
        generator.app()
    elif st.session_state.page == "Generated Projects":
        history.app()
    elif st.session_state.page == "AI Copilot":
        copilot.app()
    elif st.session_state.page == "Settings":
        settings.app()
    elif st.session_state.page == "About":
        about.app()

if __name__ == "__main__":
    main()
