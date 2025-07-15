# settings.py

import os
import requests
import warnings
from dotenv import load_dotenv
from autogen_ext.models.openai import OpenAIChatCompletionClient

load_dotenv()

def check_ip_address():
    # This function is fine as-is
    allowed_ip = os.environ.get("ALLOWED_IP")
    if not allowed_ip:
        warnings.warn("ALLOWED_IP not set in .env. Skipping IP check.", UserWarning)
        return
    try:
        response = requests.get("https://checkip.amazonaws.com", timeout=5)
        response.raise_for_status()
        current_ip = response.text.strip()
        if current_ip == allowed_ip:
            print(f"✅ IP Check Passed: Current IP ({current_ip}) is authorized.")
        else:
            warnings.warn(
                f"IP MISMATCH: Current IP ({current_ip}) does not match allowed IP ({allowed_ip}). "
                "Update your key's restrictions in Google Cloud.",
                UserWarning
            )
    except requests.exceptions.RequestException as e:
        warnings.warn(f"Could not check IP address: {e}", UserWarning)

def get_gemini_client():
    """Loads the Google API key and returns an OpenAIChatCompletionClient instance."""
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("FATAL: GOOGLE_API_KEY not found in .env file.")

    model_client = OpenAIChatCompletionClient(
        model="gemini-1.5-flash",
        api_key=google_api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta",
    )
    return model_client