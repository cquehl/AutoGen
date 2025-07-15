# authenticate.py

import os
import requests
import warnings
from dotenv import load_dotenv

# New imports needed for the client
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.models import ModelInfo

# Load environment variables
load_dotenv()

def check_ip_address():
    # ... (this function remains exactly the same)
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

# This function is updated to return a client instance
def get_gemini_client():
    """Loads the Google API key and returns an OpenAIChatCompletionClient instance."""
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("FATAL: GOOGLE_API_KEY not found in .env file.")

    # Create the client instance as shown in the documentation
    model_client = OpenAIChatCompletionClient(
        model="gemini-1.5-flash", # Use a valid Gemini model
        api_key=google_api_key,
        base_url="https://generativelanguage.googleapis.com/v1beta", # The OpenAI-compatible endpoint
    )
    return model_client