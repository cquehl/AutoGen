"""
Yamazaki v2 - Pydantic Configuration Models

Type-safe, validated configuration using Pydantic.
All settings are defined here with validation, defaults, and documentation.
"""

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List, Dict, Literal
from pathlib import Path
from enum import Enum


class ModelProvider(str, Enum):
    """Supported LLM providers"""
    AZURE = "azure"
    OPENAI = "openai"
    GOOGLE = "google"


class DatabaseConfig(BaseModel):
    """Database configuration with connection pooling"""

    url: str = Field(
        default="sqlite:///./data/yamazaki.db",
        description="Database connection URL"
    )
    pool_size: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of connections in the pool"
    )
    max_overflow: int = Field(
        default=10,
        ge=0,
        le=50,
        description="Additional connections beyond pool_size"
    )
    pool_timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Seconds to wait for connection from pool"
    )
    query_timeout: int = Field(
        default=30,
        ge=1,
        le=600,
        description="Maximum query execution time in seconds"
    )
    pool_recycle: int = Field(
        default=3600,
        ge=60,
        description="Recycle connections after N seconds"
    )

    @property
    def async_url(self) -> str:
        """Convert to async-compatible URL"""
        if self.url.startswith("sqlite:///"):
            return self.url.replace("sqlite:///", "sqlite+aiosqlite:///")
        elif self.url.startswith("postgresql://"):
            return self.url.replace("postgresql://", "postgresql+asyncpg://")
        elif self.url.startswith("mysql://"):
            return self.url.replace("mysql://", "mysql+aiomysql://")
        return self.url


class SecurityConfig(BaseModel):
    """Security configuration for tools and operations"""

    allowed_directories: List[Path] = Field(
        default_factory=lambda: [
            Path.cwd(),
            Path.home() / "agent_output",
            Path.home() / "data",
        ],
        description="Directories allowed for file operations"
    )
    blocked_file_patterns: List[str] = Field(
        default_factory=lambda: [
            r"\.ssh",
            r"\.aws",
            r"\.env",
            r"id_rsa",
            r"password",
            r"secret",
            r"/etc/",
            r"\.key$",
        ],
        description="Regex patterns for blocked file paths"
    )
    allowed_sql_commands: List[str] = Field(
        default=["SELECT", "INSERT", "UPDATE", "DELETE"],
        description="Allowed SQL command types"
    )
    blocked_sql_patterns: List[str] = Field(
        default_factory=lambda: [
            r"\bDROP\b",
            r"\bTRUNCATE\b",
            r"\bALTER\b",
            r"\bCREATE\b",
            r"\bEXEC\b",
            r"\bSHUTDOWN\b",
            r"\bGRANT\b",
            r"\bREVOKE\b",
        ],
        description="SQL patterns that are blocked"
    )
    max_query_length: int = Field(
        default=10000,
        ge=100,
        le=100000,
        description="Maximum allowed SQL query length"
    )
    enable_audit_log: bool = Field(
        default=True,
        description="Enable security audit logging"
    )
    operation_timeout: int = Field(
        default=30,
        ge=1,
        le=600,
        description="Default timeout for security-validated operations"
    )


class AgentConfig(BaseModel):
    """Configuration for individual agents"""

    name: str = Field(description="Agent name")
    model_provider: ModelProvider = Field(
        default=ModelProvider.AZURE,
        description="LLM provider to use"
    )
    model: Optional[str] = Field(
        default=None,
        description="Model name/deployment"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM temperature"
    )
    max_tokens: int = Field(
        default=4096,
        ge=1,
        description="Maximum tokens for responses"
    )
    tools: List[str] = Field(
        default_factory=list,
        description="List of tool names this agent can use"
    )
    system_message: Optional[str] = Field(
        default=None,
        description="Custom system message"
    )
    reflect_on_tool_use: bool = Field(
        default=True,
        description="Enable tool use reflection"
    )


class ObservabilityConfig(BaseModel):
    """Observability configuration (logging, tracing, metrics)"""

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    log_format: Literal["json", "console"] = Field(
        default="console",
        description="Log output format"
    )
    enable_telemetry: bool = Field(
        default=True,
        description="Enable OpenTelemetry tracing and metrics"
    )
    otlp_endpoint: Optional[str] = Field(
        default=None,
        description="OpenTelemetry collector endpoint"
    )
    service_name: str = Field(
        default="yamazaki-v2",
        description="Service name for telemetry"
    )
    enable_metrics: bool = Field(
        default=True,
        description="Enable Prometheus metrics"
    )
    metrics_port: int = Field(
        default=9090,
        ge=1024,
        le=65535,
        description="Port for Prometheus metrics endpoint"
    )


class TeamConfig(BaseModel):
    """Configuration for agent teams"""

    name: str = Field(description="Team name")
    agents: List[str] = Field(
        description="List of agent names in this team"
    )
    max_turns: int = Field(
        default=15,
        ge=1,
        le=100,
        description="Maximum conversation turns"
    )
    allow_repeated_speaker: bool = Field(
        default=False,
        description="Allow same agent to speak consecutively"
    )
    selector_prompt: Optional[str] = Field(
        default=None,
        description="Custom selector prompt for team coordination"
    )


class AppSettings(BaseSettings):
    """
    Main application settings.

    Loaded from environment variables and settings.yaml.
    Environment variables take precedence.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Environment-specific settings
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment"
    )

    # LLM Provider Configuration
    azure_api_key: Optional[str] = Field(
        default=None,
        alias="AZURE_OPENAI_API_KEY",
        description="Azure OpenAI API key"
    )
    azure_endpoint: Optional[str] = Field(
        default=None,
        alias="AZURE_OPENAI_ENDPOINT",
        description="Azure OpenAI endpoint"
    )
    azure_deployment_name: Optional[str] = Field(
        default="StellaSource-GPT4o",
        alias="AZURE_OPENAI_DEPLOYMENT_NAME",
        description="Azure deployment name"
    )
    azure_api_version: str = Field(
        default="2024-02-01",
        description="Azure OpenAI API version"
    )

    openai_api_key: Optional[str] = Field(
        default=None,
        alias="OPENAI_API_KEY",
        description="OpenAI API key"
    )

    google_api_key: Optional[str] = Field(
        default=None,
        alias="GOOGLE_API_KEY",
        description="Google API key"
    )

    # Component Configurations
    database: DatabaseConfig = Field(
        default_factory=DatabaseConfig,
        description="Database configuration"
    )
    security: SecurityConfig = Field(
        default_factory=SecurityConfig,
        description="Security configuration"
    )
    observability: ObservabilityConfig = Field(
        default_factory=ObservabilityConfig,
        description="Observability configuration"
    )

    # Agent and Team Configurations
    agents: Dict[str, AgentConfig] = Field(
        default_factory=dict,
        description="Agent configurations"
    )
    teams: Dict[str, TeamConfig] = Field(
        default_factory=dict,
        description="Team configurations"
    )

    # Default model provider
    default_provider: ModelProvider = Field(
        default=ModelProvider.AZURE,
        description="Default LLM provider"
    )

    @field_validator("azure_api_key", "azure_endpoint")
    @classmethod
    def validate_azure_config(cls, v, info):
        """Validate Azure configuration when Azure is the default provider"""
        # Note: This is a simplified validator
        # In production, you'd check if default_provider is AZURE
        return v

    def get_llm_config(self, provider: Optional[ModelProvider] = None) -> dict:
        """
        Get LLM configuration for specified provider.

        Args:
            provider: LLM provider (defaults to default_provider)

        Returns:
            Configuration dict for ChatCompletionClient.load_component()
        """
        provider = provider or self.default_provider

        if provider == ModelProvider.AZURE:
            if not self.azure_api_key or not self.azure_endpoint:
                raise ValueError(
                    "Azure OpenAI configuration missing. "
                    "Set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT"
                )
            return {
                "provider": "azure",
                "model": self.azure_deployment_name,
                "api_key": self.azure_api_key,
                "azure_endpoint": self.azure_endpoint,
                "api_version": self.azure_api_version,
            }

        elif provider == ModelProvider.OPENAI:
            if not self.openai_api_key:
                raise ValueError("OPENAI_API_KEY not set")
            return {
                "provider": "openai",
                "model": "gpt-4",
                "api_key": self.openai_api_key,
            }

        elif provider == ModelProvider.GOOGLE:
            if not self.google_api_key:
                raise ValueError("GOOGLE_API_KEY not set")
            return {
                "provider": "google",
                "model": "gemini-1.5-flash",
                "api_key": self.google_api_key,
            }

        else:
            raise ValueError(f"Unknown provider: {provider}")

    def get_model_client(self, provider: Optional[ModelProvider] = None):
        """
        Get ChatCompletionClient for specified provider.

        Args:
            provider: LLM provider (defaults to default_provider)

        Returns:
            ChatCompletionClient instance
        """
        from autogen_core.models import ChatCompletionClient

        llm_config = self.get_llm_config(provider)

        component_config = {
            "provider": "azure_openai_chat_completion_client",
            "config": llm_config
        }

        return ChatCompletionClient.load_component(component_config)


# Singleton instance (loaded on import)
_settings: Optional[AppSettings] = None


def get_settings() -> AppSettings:
    """
    Get application settings singleton.

    Returns:
        AppSettings instance
    """
    global _settings
    if _settings is None:
        _settings = AppSettings()
    return _settings


def load_settings_from_yaml(yaml_path: Path) -> AppSettings:
    """
    Load settings from YAML file.

    Args:
        yaml_path: Path to settings.yaml

    Returns:
        AppSettings instance with values from YAML
    """
    import yaml

    with open(yaml_path) as f:
        config_data = yaml.safe_load(f)

    return AppSettings(**config_data)


def reset_settings():
    """Reset settings singleton (useful for testing)"""
    global _settings
    _settings = None
