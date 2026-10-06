"""Resolve the CWA key from local or hosting-provider secret stores."""

import os


def get_secret(name: str) -> str | None:
    """Return CWA_API_KEY, preferring the process environment.

    Local ``.env`` loading is optional so deployed environments do not need
    python-dotenv to exist at runtime. Streamlit's secrets are checked last.
    """
    try:
        from dotenv import load_dotenv

        load_dotenv(override=False)
    except ImportError:
        pass

    value = os.getenv(name, "").strip()
    if value:
        return value

    try:
        import streamlit as st

        value = str(st.secrets.get(name, "")).strip()
    except Exception:
        return None
    return value or None


def get_api_key() -> str | None:
    return get_secret("CWA_API_KEY")
