import streamlit as st
import json
from frontend.components.ui import api_header
from backend.database.connection import get_db_connection
from backend.ai.gemini_client import ask_copilot

def fetch_all_apis():
    """Fetches list of all ingested APIs from SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, version FROM apis ORDER BY created_at DESC;")
    rows = cursor.fetchall()
    conn.close()
    return rows

def fetch_api_and_wrapper(api_id: str):
    """Fetches full API details and any generated Python wrapper code for context."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # API info
    cursor.execute("SELECT * FROM apis WHERE id = ?;", (api_id,))
    api_row = cursor.fetchone()
    if not api_row:
        conn.close()
        return None, None, []
        
    # Endpoints
    cursor.execute("SELECT * FROM endpoints WHERE api_id = ?;", (api_id,))
    endpoints = cursor.fetchall()
    
    # Wrapper code (default to first generated project, or python if available)
    cursor.execute("SELECT wrapper_code FROM projects WHERE api_id = ? ORDER BY created_at DESC LIMIT 1;", (api_id,))
    proj_row = cursor.fetchone()
    wrapper_code = proj_row["wrapper_code"] if proj_row else ""
    
    conn.close()
    return api_row, wrapper_code, endpoints

def app():
    api_header("AI Copilot", "Ask questions about the active API endpoints or the generated SDK client wrapper")

    apis = fetch_all_apis()
    if not apis:
        st.markdown(
            """
            <div style="text-align: center; margin: 50px 0;">
                <h3 style="color: #64748b;">No APIs Ingested Yet</h3>
                <p style="color: #94a3b8;">Go to the Analyze API page to parse a documentation URL first.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        return

    # Select Active API
    api_options = {row["name"]: row["id"] for row in apis}
    selected_name = st.selectbox(
        "Target API Context", 
        list(api_options.keys()),
        index=0 if "active_api_id" not in st.session_state else list(api_options.values()).index(st.session_state.active_api_id)
    )
    api_id = api_options[selected_name]
    
    # If active API changes, clear chat history
    if "copilot_api_id" not in st.session_state or st.session_state.copilot_api_id != api_id:
        st.session_state.copilot_api_id = api_id
        st.session_state.copilot_messages = [
            {"role": "assistant", "content": f"Hi! I am your AI Copilot for **{selected_name}**. Ask me any questions about its endpoints, query/path parameters, authentication flow, documentation URL, or how to use the generated wrapper client library code!"}
        ]

    # Fetch API details for context
    api_info, wrapper_code, endpoints_rows = fetch_api_and_wrapper(api_id)
    
    # Format a lightweight details outline to pass to Gemini
    endpoints_lightweight = []
    for ep in endpoints_rows:
        try:
            query_params = json.loads(ep["query_params"]) if ep["query_params"] else []
            headers = json.loads(ep["headers"]) if ep["headers"] else []
        except Exception:
            query_params = []
            headers = []
            
        endpoints_lightweight.append({
            "method": ep["method"],
            "path": ep["path"],
            "description": ep["description"],
            "auth_required": bool(ep["auth_required"]),
            "query_params": query_params,
            "headers": headers,
            "request_body": ep["request_body"]
        })
        
    api_details = {
        "name": api_info["name"],
        "version": api_info["version"],
        "url": api_info["url"],
        "base_url": api_info["base_url"],
        "auth_type": api_info["auth_type"],
        "summary": api_info["summary"],
        "endpoints": endpoints_lightweight
    }

    # Render Chat History
    for msg in st.session_state.copilot_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat Input
    if user_query := st.chat_input("Ask me about endpoint paths, headers, or SDK wrappers..."):
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_query)
            
        # Append user message to history
        st.session_state.copilot_messages.append({"role": "user", "content": user_query})
        
        # Generate assistant response
        with st.spinner("🤖 AI Copilot is thinking..."):
            assistant_response = ask_copilot(
                api_details=api_details,
                wrapper_code=wrapper_code,
                chat_history=st.session_state.copilot_messages[:-1],  # exclude current query from history parameter
                question=user_query
            )
            
        # Display assistant message
        with st.chat_message("assistant"):
            st.markdown(assistant_response)
            
        # Append assistant message to history
        st.session_state.copilot_messages.append({"role": "assistant", "content": assistant_response})
        st.rerun()
