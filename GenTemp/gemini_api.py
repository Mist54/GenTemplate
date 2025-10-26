# gemini_api.py
import google.genai as genai
import streamlit as st
from typing import Optional


@st.cache_resource
def get_gemini_client() -> Optional[genai.Client]:
    """Return a cached Gemini client."""
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        api_key = None

    if not api_key:
        return None

    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None


def generate_response(prompt: str) -> str:
    """
    Generate a response from Gemini that works across SDK versions.
    Falls back gracefully if optional args are unsupported.
    """
    client = get_gemini_client()
    if not client:
        return "Initialization failed: missing or invalid API key."

    model_name = "gemini-2.5-flash"

    try:
        # try with config-like args first
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                temperature=0.7,
                max_output_tokens=1000,
            )
        except TypeError:
            # fallback for SDKs that don't accept temperature directly
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )

        # extract text safely
        if hasattr(response, "text") and response.text:
            return response.text.strip()

        # fallback: stringify object if structure differs
        return str(response)

    except Exception as e:
        return f"Gemini API Error: {e}"
