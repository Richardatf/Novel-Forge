from __future__ import annotations

import hmac
import os

import streamlit as st


def login_required() -> bool:
    """Render a fail-closed password gate when hosted mode is enabled."""
    hosted = os.getenv("NOVEL_FORGE_HOSTED", "").lower() in {"1", "true", "yes"}
    configured_password = os.getenv("APP_PASSWORD", "")

    if not hosted and not configured_password:
        return True
    if hosted and not configured_password:
        st.error("Hosted mode is locked because APP_PASSWORD has not been configured.")
        st.caption("Set APP_PASSWORD in the hosting provider's secret manager, then restart the app.")
        st.stop()
    if st.session_state.get("novel_forge_authenticated"):
        return True

    st.title("The Novel Forge")
    st.subheader("Private studio sign-in")
    with st.form("studio_login"):
        entered = st.text_input("Studio password", type="password")
        submitted = st.form_submit_button("Enter studio", type="primary")
    if submitted:
        if hmac.compare_digest(entered, configured_password):
            st.session_state["novel_forge_authenticated"] = True
            st.rerun()
        else:
            st.error("That password is not correct.")
    st.stop()
    return False

