"""Minimal Streamlit application shell."""

from __future__ import annotations

from point_audit.config import get_settings


def main() -> None:
    """Render the placeholder UI without invoking analysis logic."""
    import streamlit as st

    settings = get_settings()
    st.set_page_config(page_title="Point Audit", page_icon="📊")
    st.title("Point Audit")
    st.info("Khung dự án đã sẵn sàng. Logic phân tích Excel chưa được triển khai.")
    st.caption(f"AI đang {'bật' if settings.ai_enabled else 'tắt'}.")

