# settings.py

import os
import requests
import warnings
from dotenv import load_dotenv
from autogen_ext.models.openai import OpenAIChatCompletionClient, AzureOpenAIChatCompletionClient
from azure.core.credentials import AzureKeyCredential
from autogen_core.models import ModelFamily

load_dotenv()

def check_ip_address():
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


def get_azure_openai_client():
    """Loads Azure OpenAI credentials and returns a client instance."""
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_version = "2024-02-01"  # Define the API version
    deployment_name = "StellaSource-GPT4o"

    if not all([api_key, endpoint]):
        raise ValueError("FATAL: AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT must be in your .env file.")

    # Construct the full URL to the deployment
    full_endpoint_url = f"{endpoint.rstrip('/')}/openai/deployments/{deployment_name}"

    model_info = {
        "model": deployment_name,
        "family": ModelFamily.GPT_4O,
        "vision": True,
        "function_calling": True,
        "json_output": True,
        "structured_output": True,
        "context_window": 128000,
        "price": [5.00, 15.00],
    }

    # --- FIX: Initialize the client using the credential object ---
    model_client = AzureOpenAIChatCompletionClient(
        model=deployment_name,
        model_info=model_info,
        endpoint=full_endpoint_url,
        credential=AzureKeyCredential(api_key),
        api_version=api_version,
    )
    
    print(f"✅ Client configured for Azure deployment: {deployment_name}")
    return model_client