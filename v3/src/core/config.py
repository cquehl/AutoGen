"""
Suntory v3 - Configuration Management
Type-safe configuration using Pydantic Settings
"""

from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class GreetingStyle(str, Enum):
    """Alfred's greeting style"""
    FORMAL = "formal"
    CASUAL = "casual"
    TIME_AWARE = "time_aware"


class PersonalityMode(str, Enum):
    """Alfred's personality mode"""
    PROFESSIONAL = "professional"
    WITTY = "witty"
    BALANCED = "balanced"


class SuntorySettings(BaseSettings):
    """
    Main configuration for Suntory v3 System
    Loads from environment variables and .env file
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Provider Configuration

    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None

    # Azure OpenAI
    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_deployment_name: Optional[str] = None

    # Default model
    default_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Default LLM model to use"
    )

    # System Configuration

    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        description="Running environment"
    )

    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )

    database_url: str = Field(
        default="sqlite:///./v3/data/suntory.db",
        description="Database connection URL"
    )

    chroma_db_path: str = Field(
        default="./v3/data/chroma",
        description="ChromaDB storage path"
    )

    workspace_dir: str = Field(
        default="./v3/workspace",
        description="Workspace directory for agent operations"
    )

    # Docker Configuration

    docker_enabled: bool = Field(
        default=True,
        description="Enable Docker sandboxing"
    )

    docker_timeout: int = Field(
        default=300,
        description="Docker operation timeout in seconds"
    )

    # Security Configuration

    allowed_directories: List[str] = Field(
        default_factory=lambda: ["./v3/workspace", "./v3/data", "./v3/logs"],
        description="Allowed directories for file operations"
    )

    operation_timeout: int = Field(
        default=60,
        description="Maximum time for operations in seconds"
    )

    # Observability Configuration

    enable_telemetry: bool = Field(
        default=True,
        description="Enable telemetry and tracing"
    )

    metrics_port: int = Field(
        default=9090,
        description="Metrics export port"
    )

    service_name: str = Field(
        default="suntory-v3",
        description="Service name for tracing"
    )

    # Alfred Configuration

    alfred_greeting_style: GreetingStyle = Field(
        default=GreetingStyle.TIME_AWARE,
        description="Alfred's greeting style"
    )

    alfred_personality: PersonalityMode = Field(
        default=PersonalityMode.BALANCED,
        description="Alfred's personality mode"
    )

    # Agent Configuration

    max_team_turns: int = Field(
        default=30,
        description="Maximum turns for team conversations"
    )

    agent_timeout: int = Field(
        default=120,
        description="Agent response timeout in seconds"
    )

    enable_agent_memory: bool = Field(
        default=True,
        description="Enable persistent agent memory"
    )

    # User Preference Privacy Settings

    enable_llm_preference_extraction: bool = Field(
        default=True,
        description="Enable LLM-based preference extraction (sends data to LLM provider)"
    )

    preference_retention_days: int = Field(
        default=365,
        description="Number of days to retain user preferences (0 = forever)"
    )

    # Validators

    @field_validator("workspace_dir", "chroma_db_path")
    @classmethod
    def create_directories(cls, v: str) -> str:
        """Ensure directories exist"""
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("allowed_directories")
    @classmethod
    def validate_directories(cls, v: List[str]) -> List[str]:
        """Create allowed directories"""
        for dir_path in v:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
        return v

    # Helper Methods

    def has_llm_provider(self) -> bool:
        """Check if at least one LLM provider is configured"""
        return any([
            self.openai_api_key,
            self.anthropic_api_key,
            self.google_api_key,
            self.azure_openai_api_key
        ])

    def get_available_providers(self) -> List[str]:
        """Get list of available LLM providers"""
        providers = []
        if self.openai_api_key:
            providers.append("openai")
        if self.anthropic_api_key:
            providers.append("anthropic")
        if self.google_api_key:
            providers.append("google")
        if self.azure_openai_api_key:
            providers.append("azure")
        return providers

    def get_workspace_path(self) -> Path:
        """Get workspace path as Path object"""
        return Path(self.workspace_dir)

    def get_chroma_path(self) -> Path:
        """Get ChromaDB path as Path object"""
        return Path(self.chroma_db_path)


# Singleton instance
_settings: Optional[SuntorySettings] = None


def get_settings() -> SuntorySettings:
    """Get or create settings singleton"""
    global _settings
    if _settings is None:
        _settings = SuntorySettings()
    return _settings


def reset_settings() -> None:
    """Reset settings (useful for testing)"""
    global _settings
    _settings = None
