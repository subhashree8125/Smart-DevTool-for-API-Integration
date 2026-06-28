import streamlit as st
import requests
import os
from frontend.components.ui import api_header
from backend.database.connection import get_db_connection

def fetch_all_apis():
    """Fetches list of all ingested APIs from SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, version FROM apis ORDER BY created_at DESC;")
    rows = cursor.fetchall()
    conn.close()
    return rows

def app():
    backend_url = st.session_state.get("settings_backend_url_shared", "http://127.0.0.1:8000")
    api_header("Wrapper Generator", "Generate custom client libraries including retry logic, logging, and error handling")

    apis = fetch_all_apis()
    if not apis:
        st.markdown(
            """
            <div style="text-align: center; margin: 50px 0;">
                <h3 style="color: #64748b;">No APIs Ingested Yet</h3>
                <p style="color: #94a3b8;">Start by entering an API Documentation URL on the Analyze page.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        if st.button("Go to Analyze API"):
            st.session_state.page = "Analyze API"
            st.rerun()
        return

    # Select Active API
    api_options = {row["name"]: row["id"] for row in apis}
    default_index = 0
    if "active_api_id" in st.session_state and st.session_state.active_api_id in api_options.values():
        default_index = list(api_options.values()).index(st.session_state.active_api_id)

    selected_name = st.selectbox(
        "Select Target API", 
        list(api_options.keys()),
        index=default_index
    )
    api_id = api_options[selected_name]
    st.session_state.active_api_id = api_id

    # Choose language
    languages = [
        "Python", "JavaScript", "TypeScript", "Java", "C#", "Go", "PHP", "Ruby", "Kotlin", "Swift"
    ]
    language = st.selectbox("Select Target Language", languages)

    if st.button("Generate SDK Client Library"):
        payload = {
            "api_id": api_id,
            "language": language.lower()
        }

        with st.spinner(f"🚀 Building client library SDK wrapper for {language} with retry logic, exceptions, logging, and configuration..."):
            try:
                response = requests.post(f"{backend_url}/generate", json=payload, timeout=180)
                
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.last_generated_project = data
                    st.success(f"🎉 Successfully generated {language} Client Library!")
                else:
                    error_detail = response.json().get("detail", "Unknown server error.")
                    st.error(f"Failed to generate SDK: {error_detail}")
            except Exception as e:
                st.error(f"Network error or backend offline: {e}")

    # Render Explorer view if code has been generated
    if "last_generated_project" in st.session_state and st.session_state.last_generated_project.get("api_id") == api_id:
        proj = st.session_state.last_generated_project
        if proj["language"].lower() == language.lower():
            st.markdown("---")
            st.markdown("### 🗂️ Generated Assets Explorer")

            tab_code, tab_readme, tab_download = st.tabs(["💻 Wrapper Class Code", "📖 README / Integration Guide", "📥 Download Center"])

            with tab_code:
                st.markdown(f"**Client Library Wrapper** (Syntax: {language})")
                st.code(proj["wrapper_code"], language=language.lower())

            with tab_readme:
                st.markdown("**Client Integration Guide** (Markdown)")
                st.markdown(proj["readme_code"])

            with tab_download:
                st.markdown("#### Download SDK Package")
                st.info("The generated project contains the SDK client wrapper file, the instruction integration guide README, and configuration boilerplate.")
                
                zip_relative_path = proj["zip_path"]
                if os.path.exists(zip_relative_path):
                    with open(zip_relative_path, "rb") as f:
                        zip_bytes = f.read()
                    
                    st.download_button(
                        label="📥 Download Client SDK Wrapper (ZIP)",
                        data=zip_bytes,
                        file_name=os.path.basename(zip_relative_path),
                        mime="application/zip",
                        use_container_width=True
                    )
                else:
                    st.error("ZIP package file was not found on backend disk.")
