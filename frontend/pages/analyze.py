import streamlit as st
import requests
import time
from frontend.components.ui import api_header, progress_stepper

def app():
    backend_url = st.session_state.get("settings_backend_url_shared", "http://127.0.0.1:8000")
    api_header("Analyze API", "Incorporate new external documentation URLs to run AI ingestion")

    # Form parameters
    url = st.text_input("API Documentation URL", placeholder="https://petstore.swagger.io/v2/swagger.json")
    use_case = st.text_area("Integration Use Case (Optional)", placeholder="e.g. Fetch product catalog and sync orders into database.")
    
    preferred_language = st.selectbox(
        "Preferred SDK Language",
        ["Python", "JavaScript", "TypeScript", "Java", "C#", "Go", "PHP", "Ruby", "Kotlin", "Swift"]
    )

    if st.button("Start Analysis"):
        if not url:
            st.error("Please enter a valid API Documentation URL.")
            return

        steps = [
            "Fetching Documentation", 
            "Detecting Documentation Type", 
            "Parsing API", 
            "Extracting Endpoints", 
            "AI Analysis", 
            "Wrapper Generation", 
            "Completed"
        ]

        # Render active stepper
        stepper_container = st.empty()
        status_message = st.empty()
        
        try:
            # Step 0: Fetching
            stepper_container.empty()
            with stepper_container.container():
                progress_stepper(0, steps)
            status_message.info("🔄 Initiating network connection to target documentation URL...")
            time.sleep(0.5)

            # Step 1: Detecting
            with stepper_container.container():
                progress_stepper(1, steps)
            status_message.info("🔍 Analyzing payload structural signatures for type identification...")
            time.sleep(0.5)

            # Step 2: Parsing
            with stepper_container.container():
                progress_stepper(2, steps)
            status_message.info("⚙️ Extracting data models and schema paths...")
            time.sleep(0.5)

            # Step 3: Extracting Endpoints & Step 4: AI Analysis
            with stepper_container.container():
                progress_stepper(4, steps)
            status_message.info("🧠 Resolving schemas and running Gemini AI deep summary analysis...")

            # Fire request to FastAPI backend
            payload = {
                "url": url,
                "use_case": use_case,
                "preferred_language": preferred_language.lower()
            }
            
            response = requests.post(f"{backend_url}/analyze", json=payload, timeout=180)
            
            if response.status_code != 200:
                error_detail = response.json().get("detail", "Unknown server error.")
                st.error(f"Backend analysis failed: {error_detail}")
                return

            api_data = response.json()
            api_id = api_data["id"]

            # Step 5: SDK Wrapper Generation
            with stepper_container.container():
                progress_stepper(5, steps)
            status_message.info(f"💾 Synthesizing production client SDK wrapper for {preferred_language}...")
            
            gen_payload = {
                "api_id": api_id,
                "language": preferred_language.lower()
            }
            gen_response = requests.post(f"{backend_url}/generate", json=gen_payload, timeout=180)
            
            if gen_response.status_code != 200:
                st.warning("Analysis completed successfully, but automatic SDK generation failed. You can retry from the Wrapper Generator.")
                time.sleep(1.5)
            
            # Step 6: Completed
            with stepper_container.container():
                progress_stepper(6, steps)
            status_message.success("🎉 API Ingestion and Client Wrapper synthesis completed successfully!")
            
            # Store target API in session and redirect to dashboard
            st.session_state.active_api_id = api_id
            st.session_state.page = "Dashboard"
            st.balloons()
            time.sleep(1.0)
            st.rerun()

        except requests.exceptions.ConnectionError:
            st.error(f"Could not connect to FastAPI backend at {backend_url}. Please ensure the backend server is running.")
        except Exception as e:
            st.error(f"An unexpected error occurred during processing: {e}")
