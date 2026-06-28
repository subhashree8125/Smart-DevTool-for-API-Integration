import streamlit as st

def inject_custom_css():
    """Reads and injects the custom stylesheet into the Streamlit session."""
    try:
        with open("frontend/styles/custom.css", "r") as f:
            css = f.read()
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

def card(title: str, content: str, subtitle: str = "") -> None:
    """Renders a custom UI card container."""
    subtitle_html = f"<div style='color: #94a3b8; font-size: 0.85rem; margin-top: -8px; margin-bottom: 12px;'>{subtitle}</div>" if subtitle else ""
    st.markdown(
        f"""
        <div class="custom-card">
            <h3 style="margin-top: 0; color: #f8fafc; font-size: 1.2rem;">{title}</h3>
            {subtitle_html}
            <div style="color: #cbd5e1; font-size: 0.95rem;">{content}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def metric_card(label: str, value: str, description: str = "") -> None:
    """Renders a premium visual metric indicator card."""
    desc_html = f"<div style='color: #94a3b8; font-size: 0.8rem; margin-top: 6px;'>{description}</div>" if description else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <div style="color: #94a3b8; font-size: 0.85rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em;">{label}</div>
            <div style="color: #f8fafc; font-size: 2rem; font-weight: 700; margin-top: 4px;">{value}</div>
            {desc_html}
        </div>
        """,
        unsafe_allow_html=True
    )

def method_badge(method: str) -> str:
    """Returns the HTML string for a colored HTTP method badge."""
    m_lower = method.lower()
    badge_class = f"badge-{m_lower}" if m_lower in ("get", "post", "put", "delete", "patch") else "badge-get"
    return f'<span class="badge {badge_class}">{method}</span>'

def api_header(title: str, subtitle: str = "") -> None:
    """Renders a hero section headers with visual division."""
    subtitle_html = f"<p style='color: #94a3b8; font-size: 1.1rem; margin-top: -10px; margin-bottom: 24px;'>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div style="margin-bottom: 30px;">
            <h1 style="color: #f8fafc; font-size: 2.2rem; font-weight: 800; margin-bottom: 8px;">{title}</h1>
            {subtitle_html}
            <hr style="border: 0; border-top: 1px solid #1e293b; margin: 0 0 20px 0;">
        </div>
        """,
        unsafe_allow_html=True
    )

def progress_stepper(current_step: int, steps: list) -> None:
    """Renders a visual horizontal multi-step progress indicators."""
    cols = st.columns(len(steps))
    for i, step in enumerate(steps):
        with cols[i]:
            if i < current_step:
                # Completed step
                st.markdown(
                    f"""
                    <div style="border-top: 4px solid #10b981; padding-top: 8px;">
                        <span style="color: #10b981; font-weight: 600; font-size: 0.85rem;">✓ {step}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            elif i == current_step:
                # Active step
                st.markdown(
                    f"""
                    <div style="border-top: 4px solid #3b82f6; padding-top: 8px;">
                        <span style="color: #3b82f6; font-weight: 700; font-size: 0.85rem; text-shadow: 0 0 8px rgba(59,130,246,0.3);">▶ {step}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                # Pending step
                st.markdown(
                    f"""
                    <div style="border-top: 4px solid #334155; padding-top: 8px;">
                        <span style="color: #64748b; font-weight: 500; font-size: 0.85rem;">{step}</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    st.write("")  # padding spacer
