import streamlit as st
import os
from frontend.components.ui import api_header
from backend.database.connection import get_db_connection

def fetch_projects():
    """Queries SQLite for all generated projects with metadata."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id, p.language, p.zip_path, p.created_at, a.name as api_name
        FROM projects p
        JOIN apis a ON p.api_id = a.id
        ORDER BY p.created_at DESC;
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows

def app():
    api_header("Generated Projects & Downloads", "Retrieve past generated SDK wrapper client packages")

    projects = fetch_projects()
    
    if not projects:
        st.markdown(
            """
            <div style="text-align: center; margin: 50px 0;">
                <h3 style="color: #64748b;">No Generated Projects Found</h3>
                <p style="color: #94a3b8;">Choose a language and trigger generation from the Wrapper Generator page.</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        if st.button("Go to Wrapper Generator"):
            st.session_state.page = "Wrapper Generator"
            st.rerun()
        return

    # Render grid of projects
    st.markdown("### 🗂️ Generated Client SDK Library Archives")
    
    for row in projects:
        col_info, col_dl = st.columns([3, 1])
        
        with col_info:
            st.markdown(
                f"""
                <div style="background-color: #1e293b; border-left: 4px solid #3b82f6; padding: 12px; border-radius: 4px; margin-bottom: 10px;">
                    <strong style="color: #f8fafc; font-size: 1.05rem;">{row['api_name']}</strong><br/>
                    <span style="color: #94a3b8; font-size: 0.85rem;">
                        Language: <code>{row['language'].upper()}</code> | Generated: {row['created_at']}
                    </span>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        with col_dl:
            # Streamlit download button for the local ZIP file
            zip_path = row["zip_path"]
            if os.path.exists(zip_path):
                with open(zip_path, "rb") as f:
                    zip_bytes = f.read()
                    
                st.download_button(
                    label="📥 Download ZIP",
                    data=zip_bytes,
                    file_name=os.path.basename(zip_path),
                    mime="application/zip",
                    key=f"dl_btn_{row['id']}"
                )
            else:
                st.error("ZIP deleted from server disk.")
