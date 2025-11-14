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
        raise ValueError(
            "\n❌ GOOGLE_API_KEY not found in .env file.\n\n"
            "To fix this:\n"
            "1. Get your API key from: https://aistudio.google.com/app/apikey\n"
            "2. Create/edit .env file in the project root\n"
            "3. Add this line: GOOGLE_API_KEY=your_actual_key_here\n"
            "4. Run the CLI again\n\n"
            "Need help? Check the README or run: ./cli.py --help"
        )

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
        missing = []
        if not api_key:
            missing.append("AZURE_OPENAI_API_KEY")
        if not endpoint:
            missing.append("AZURE_OPENAI_ENDPOINT")

        raise ValueError(
            f"\n❌ Missing Azure OpenAI configuration: {', '.join(missing)}\n\n"
            "To fix this:\n"
            "1. Create an Azure OpenAI resource:\n"
            "   → Go to: https://portal.azure.com\n"
            "   → Search for 'Azure OpenAI'\n"
            "   → Create a resource and deploy a model (e.g., gpt-4o)\n\n"
            "2. Get your credentials:\n"
            "   → In Azure Portal, go to your Azure OpenAI resource\n"
            "   → Click 'Keys and Endpoint' in the left menu\n"
            "   → Copy 'KEY 1' and 'Endpoint'\n\n"
            "3. Create/edit .env file in the project root and add:\n"
            "   AZURE_OPENAI_API_KEY=your_key_from_azure\n"
            "   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/\n"
            "   AZURE_OPENAI_DEPLOYMENT_NAME=your_deployment_name\n\n"
            "4. Run the CLI again\n\n"
            "Need help? Run: ./setup_cli.sh"
        )

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


def get_llm_config(provider: str = "azure"):
    """
    Returns the LLM configuration for the specified provider.

    Args:
        provider: One of "azure", "google", or "openai"

    Returns:
        Dictionary with LLM configuration
    """
    if provider.lower() == "azure":
        return get_azure_llm_config()
    elif provider.lower() == "google":
        return get_gemini_llm_config()
    elif provider.lower() == "openai":
        # For OpenAI, use similar structure to Azure
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "\n❌ OPENAI_API_KEY not found in .env file.\n\n"
                "To fix this:\n"
                "1. Get your API key from: https://platform.openai.com/api-keys\n"
                "   (You'll need an OpenAI account)\n\n"
                "2. Create/edit .env file in the project root\n"
                "3. Add this line: OPENAI_API_KEY=sk-your_actual_key_here\n"
                "4. Run the CLI again\n\n"
                "💡 Tip: OpenAI keys start with 'sk-'\n\n"
                "Need help? Check the README or run: ./cli.py --help"
            )

        llm_config = {
            "provider": "openai",
            "model": "gpt-4",
            "api_key": api_key,
        }
        print("✅ LLM Config created for OpenAI.")
        return llm_config
    else:
        raise ValueError(f"Unknown provider: {provider}. Choose 'azure', 'google', or 'openai'.")

