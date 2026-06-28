import streamlit as st
from frontend.components.ui import api_header

def app():
    api_header("About Smart DevTool", "SaaS AI-Powered API Integration Platform")

    st.markdown("""
    ### ⚡ What is Smart DevTool?
    **Smart DevTool** is an advanced developer utility built to automate the tedious and time-consuming process of integrating third-party APIs. 
    Instead of manually reading through pages of documentation, writing custom network request wrappers, and figuring out error handling or pagination, **Smart DevTool does it all for you automatically**.

    Simply provide a link to any API documentation page, and the tool will scrape the content, extract all API endpoints, and use AI to generate fully functional, production-ready SDK client libraries.
    """)

    st.markdown("### 🛠️ How the Integration Pipeline Works")
    
    st.markdown("""
    The tool processes documentation URLs through four specialized pipeline stages:
    
    1. **Ingest & Scrape**: Downloads the target document page. If it is an HTML or SPA page (like Swagger or Redoc), it scans scripts to extract specification JSON URLs, using dynamic Playwright rendering or static crawlers.
    2. **Parse & Structure**: Standardizes endpoints, query variables, request headers, status codes, and mock JSON payloads into a local SQLite database.
    3. **AI Core Analysis**: Leverages Google Gemini (with Llama-3.1 Groq fallbacks) to compile integration summaries and evaluate pagination/rate limit patterns.
    4. **SDK Client Synthesis**: Generates code folders (SDK wrapper libraries, exceptions, configuration loaders) and packages them into download archives.
    """)

    st.markdown("### 💻 Supported SDK Languages")
    
    # Render supported languages in a clean grid layout
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("🐍 **Python**")
        st.markdown("☕ **Java**")
    with col2:
        st.markdown("🌐 **JavaScript**")
        st.markdown("📘 **TypeScript**")
    with col3:
        st.markdown("🐹 **Go**")
        st.markdown("🎯 **C#**")
    with col4:
        st.markdown("🐘 **PHP**")
        st.markdown("💎 **Ruby**")

    st.markdown("""
    ---
    <div style="text-align: center; color: #64748b; font-size: 0.9rem;">
        Developed to accelerate backend and frontend integrations. Smart DevTool – 2026.
    </div>
    """, unsafe_allow_html=True)
