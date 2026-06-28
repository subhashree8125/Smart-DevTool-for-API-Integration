import streamlit as st
import os
from dotenv import load_dotenv
from frontend.components.ui import api_header

def app():
    api_header("Settings", "Configure API keys, environment settings, and local database storage")

    # Load active variables
    load_dotenv()
    active_key = os.getenv("GEMINI_API_KEY", "")
    active_groq_key = os.getenv("GROQ_API_KEY", "")
    
    # Load configuration settings from environment (default to True/auto)
    active_provider = os.getenv("PRIMARY_AI_PROVIDER", "Auto-Fallback (Gemini + Groq)")
    active_retry = os.getenv("SDK_RETRY_LOGIC", "True") == "True"
    active_logging = os.getenv("SDK_LOGGING", "True") == "True"
    active_types = os.getenv("SDK_TYPE_SAFETY", "True") == "True"

    st.markdown("### 🔌 AI Connection Status")
    
    col1, col2 = st.columns(2)
    with col1:
        if active_key:
            st.success("🟢 **Google Gemini API**: Active & Connected")
        else:
            st.error("🔴 **Google Gemini API**: Key Missing")
            
    with col2:
        if active_groq_key:
            st.success("🟢 **Groq API**: Active & Connected")
        else:
            st.warning("🟡 **Groq API (Fallback)**: Key Missing")

    st.markdown("### ⚙️ Project Configuration Preferences")

    # 1. AI Provider Preference
    provider_options = ["Auto-Fallback (Gemini + Groq)", "Gemini Only", "Groq Only"]
    default_provider_idx = provider_options.index(active_provider) if active_provider in provider_options else 0
    selected_provider = st.selectbox(
        "Preferred AI Model Provider",
        provider_options,
        index=default_provider_idx,
        help="Select which AI provider compiles summaries and synthesized wrappers. Auto-Fallback shifts to Groq if Gemini fails."
    )

    # 2. SDK Wrapper Features
    st.markdown("**SDK Client Library Compilation Settings**")
    include_retry = st.checkbox(
        "Enable Exponential Backoff Retries",
        value=active_retry,
        help="Generates client functions that automatically retry network requests on 429/5xx responses."
    )
    include_logging = st.checkbox(
        "Enable Client-Side Logging",
        value=active_logging,
        help="Embeds logging configurations to trace outbound HTTP requests and returned responses."
    )
    include_types = st.checkbox(
        "Enforce Strict Type Annotations",
        value=active_types,
        help="Includes clean type hints and typing schemas (e.g. Dict, List) in synthesized class functions."
    )

    if st.button("Save Project Configuration"):
        # Save configuration to local .env file
        try:
            env_path = ".env"
            env_data = {}
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if "=" in line and not line.strip().startswith("#"):
                            parts = line.split("=", 1)
                            k = parts[0].strip()
                            v = parts[1].strip().strip('"').strip("'")
                            env_data[k] = v
            
            # Update configuration variables
            env_data["PRIMARY_AI_PROVIDER"] = selected_provider
            env_data["SDK_RETRY_LOGIC"] = "True" if include_retry else "False"
            env_data["SDK_LOGGING"] = "True" if include_logging else "False"
            env_data["SDK_TYPE_SAFETY"] = "True" if include_types else "False"
            
            # Write back to .env
            with open(env_path, "w", encoding="utf-8") as f:
                for k, v in env_data.items():
                    f.write(f'{k}="{v}"\n')
            
            # Apply to environment variables actively
            os.environ["PRIMARY_AI_PROVIDER"] = selected_provider
            os.environ["SDK_RETRY_LOGIC"] = "True" if include_retry else "False"
            os.environ["SDK_LOGGING"] = "True" if include_logging else "False"
            os.environ["SDK_TYPE_SAFETY"] = "True" if include_types else "False"
            
            st.success("Project settings saved successfully! Key configurations have been updated.")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to write to configuration file: {e}")

    st.markdown("""
    ---
    ### ℹ️ Architecture Note
    These compilation preferences directly adjust how the AI generation engine structures your downloaded wrapper client ZIP files.
    """)
