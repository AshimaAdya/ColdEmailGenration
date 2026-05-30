import streamlit as st
import streamlit.components.v1 as components


def copy_button(text: str, label: str = "Copy to Clipboard"):
    """Renders a JS-powered copy-to-clipboard button."""
    escaped = text.replace("`", "\\`").replace("\\", "\\\\").replace("$", "\\$")
    components.html(
        f"""
        <button onclick="navigator.clipboard.writeText(`{escaped}`).then(()=>{{
            this.innerText='Copied!';
            setTimeout(()=>this.innerText='{label}',2000);
        }})" style="
            background:#0e6ebe; color:white; border:none; border-radius:4px;
            padding:6px 14px; cursor:pointer; font-size:13px; font-family:sans-serif;">
            {label}
        </button>
        """,
        height=40,
    )


def download_button(email: str, role: str = ""):
    safe_role = role.replace(" ", "_").replace("/", "-")[:40] if role else "cold_email"
    st.download_button(
        label="Download .txt",
        data=email,
        file_name=f"{safe_role}.txt",
        mime="text/plain",
    )
