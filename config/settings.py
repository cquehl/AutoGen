# config/settings.py

import os
import requests
import warnings
from dotenv import load_dotenv
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient

# Load environment variables from .env file
load_dotenv()

def check_ip_address():
    """
    Checks if the current public IP address is authorized. This is useful
    for cloud provider services that have IP-based security rules.
    """
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

def get_gemini_llm_config():
    """
    Returns the LLM configuration for a Gemini model.
    """
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    if not google_api_key:
        raise ValueError("FATAL: GOOGLE_API_KEY not found in .env file.")

    # The llm_config is a dictionary that specifies the provider, model, and API key.
    llm_config = {
        "provider": "google",
        "model": "gemini-1.5-flash",
        "api_key": google_api_key,
        # "base_url" is not a standard pyautogen config key for Gemini.
        # The library handles the endpoint automatically.
    }
    print("✅ LLM Config created for Gemini.")
    return llm_config


def get_azure_llm_config():
    """
    Returns the LLM configuration for an Azure OpenAI deployment.
    """
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "StellaSource-GPT4o")
    api_version = "2024-02-01"

    if not all([api_key, endpoint]):
        raise ValueError("FATAL: AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT must be in your .env file.")

    # The llm_config dictionary is the new standard for configuring agents.
    llm_config = {
        "provider": "azure",
        "model": deployment_name,
        "api_key": api_key,
        "azure_endpoint": endpoint,
        "api_version": api_version,
        # You can add other parameters like 'temperature' here if needed.
        "model_info": {
            "model": "gpt-4o-2024-08-06",
            "family": "gpt-4o",              # Identify the underlying model family
            "vision": True,                  # It can process images
            "function_calling": True,        # It can use tools
            "json_output": True,             # It can produce guaranteed JSON
            "structured_output": True,       # It can produce structured objects (Pydantic models)
            "multiple_system_messages": True # It supports multiple system prompts
        }
    }
    
    print(f"✅ LLM Config created for Azure deployment: {deployment_name}")
    return llm_config

