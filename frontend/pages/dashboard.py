import streamlit as st
import json
import sqlite3
from frontend.components.ui import api_header, metric_card, method_badge
from backend.database.connection import get_db_connection

def fetch_all_apis():
    """Fetches list of all ingested APIs from SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, version, url FROM apis ORDER BY created_at DESC;")
    rows = cursor.fetchall()
    conn.close()
    return rows

def fetch_api_details(api_id: str):
    """Fetches full API details including endpoints."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM apis WHERE id = ?;", (api_id,))
    api_row = cursor.fetchone()
    
    if not api_row:
        conn.close()
        return None, []
        
    cursor.execute("SELECT * FROM endpoints WHERE api_id = ?;", (api_id,))
    endpoint_rows = cursor.fetchall()
    
    conn.close()
    return api_row, endpoint_rows

def app():
    api_header("API Analysis Dashboard", "Interact with extracted endpoints and explore AI integration advice")

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
        "Select Analyzed API", 
        list(api_options.keys()),
        index=default_index
    )
    api_id = api_options[selected_name]
    st.session_state.active_api_id = api_id

    # Load Details
    api_info, endpoints = fetch_api_details(api_id)
    if not api_info:
        st.error("API details not found.")
        return

    # 1. API Metadata Cards
    col1, col2, col3 = st.columns(3)
    with col1:
        metric_card("Total Endpoints", str(len(endpoints)), f"Doc Type: {api_info['doc_type'].upper()}")
    with col2:
        auth_status = "Secure" if api_info["auth_type"] != "None" else "Open"
        metric_card("Authentication Status", auth_status, f"Type: {api_info['auth_type']}")
    with col3:
        # Determine recommendations text briefly
        rec_status = "Custom Wrapper"
        if "official" in api_info["sdk_recommendation"].lower():
            rec_status = "Official SDK"
        metric_card("Integration Path", rec_status, "AI Recommendation Summary")

    # 2. Hero Metadata Row
    st.markdown(
        f"""
        <div style="background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 16px; margin: 15px 0;">
            <table style="width: 100%; border-collapse: collapse; border: none; color: #e2e8f0;">
                <tr style="border: none;">
                    <td style="font-weight: 600; width: 120px;">Documentation:</td>
                    <td><a href="{api_info['url']}" target="_blank" style="color: #3b82f6;">{api_info['url']}</a></td>
                </tr>
                <tr style="border: none;">
                    <td style="font-weight: 600;">Base URL:</td>
                    <td><code>{api_info['base_url']}</code></td>
                </tr>
                <tr style="border: none;">
                    <td style="font-weight: 600;">API Version:</td>
                    <td><code>{api_info['version']}</code></td>
                </tr>
            </table>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 3. AI Generated Reports
    with st.expander("🤖 AI Integration Summary & SDK Recommendation", expanded=True):
        st.markdown("### 📝 API Overview")
        st.markdown(api_info["summary"])
        st.markdown("### 💡 SDK Recommendation Details")
        st.markdown(api_info["sdk_recommendation"])

    # 4. Search and Filter
    st.markdown("### 🚀 Endpoints Explorer")
    search_term = st.text_input("🔍 Search endpoints by path or description", placeholder="e.g. /pet or find")
    
    # Verb Filter
    verb_filter = st.radio(
        "HTTP Method Filter", 
        ["ALL", "GET", "POST", "PUT", "DELETE", "PATCH"],
        horizontal=True
    )

    # Filter loop
    filtered_endpoints = []
    for ep in endpoints:
        # Text query check
        match_search = (
            not search_term or 
            search_term.lower() in ep["path"].lower() or 
            (ep["description"] and search_term.lower() in ep["description"].lower())
        )
        # HTTP verb check
        match_verb = (
            verb_filter == "ALL" or 
            ep["method"].upper() == verb_filter
        )
        
        if match_search and match_verb:
            filtered_endpoints.append(ep)

    # Display endpoints
    if not filtered_endpoints:
        st.info("No endpoints matching filters were found.")
        return

    for ep in filtered_endpoints:
        auth_badge = " 🔒" if ep["auth_required"] else ""
        badge_html = method_badge(ep["method"])
        
        # Display summary title inside markdown
        expander_title = f"{ep['method']} {ep['path']} {auth_badge}"
        
        with st.expander(expander_title):
            # Parse lists
            try:
                headers = json.loads(ep["headers"]) if ep["headers"] else []
            except Exception:
                headers = []
            try:
                query_params = json.loads(ep["query_params"]) if ep["query_params"] else []
            except Exception:
                query_params = []
            try:
                path_params = json.loads(ep["path_params"]) if ep["path_params"] else []
            except Exception:
                path_params = []
            try:
                request_body = json.loads(ep["request_body"]) if ep["request_body"] else {}
            except Exception:
                request_body = {}
            try:
                response_body = json.loads(ep["response_body"]) if ep["response_body"] else {}
            except Exception:
                response_body = {}
            try:
                status_codes = json.loads(ep["status_codes"]) if ep["status_codes"] else [200]
            except Exception:
                status_codes = [200]

            st.write(f"**Description**: {ep['description'] or 'No description provided.'}")
            
            # Show parameter tables
            tab_desc, tab_req, tab_resp = st.tabs(["Parameters", "Request Body Structure", "Response Schema"])
            
            with tab_desc:
                # Path params
                if path_params:
                    st.markdown("##### Path Parameters")
                    st.table(path_params)
                # Query params
                if query_params:
                    st.markdown("##### Query Parameters")
                    st.table(query_params)
                # Headers
                if headers:
                    st.markdown("##### Request Headers")
                    st.table(headers)
                if not (path_params or query_params or headers):
                    st.info("This endpoint does not accept parameters or custom request headers.")

            with tab_req:
                if request_body:
                    st.markdown("##### Schema Properties")
                    st.json(request_body)
                if ep["sample_request"]:
                    st.markdown("##### Sample Request Payload")
                    st.code(ep["sample_request"], language="json")
                if not request_body and not ep["sample_request"]:
                    st.info("No request body content required.")

            with tab_resp:
                st.markdown(f"**HTTP Status Codes**: {', '.join(map(str, status_codes))}")
                if response_body:
                    st.markdown("##### Schema Properties")
                    st.json(response_body)
                if ep["sample_response"]:
                    st.markdown("##### Sample Response Payload")
                    st.code(ep["sample_response"], language="json")
