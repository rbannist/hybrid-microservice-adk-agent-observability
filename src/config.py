import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, computed_field

class Settings(BaseSettings):
    """
    Manages application configuration using environment variables.
    It loads variables from a .env file if present in the project root.
    """
    model_config = SettingsConfigDict(env_file='../.env', env_file_encoding='utf-8', extra='ignore')

    # GCP Configuration
    GCP_PROJECT_ID: str = Field(..., validation_alias='GOOGLE_CLOUD_PROJECT')
    GCP_LOCATION: str = Field("europe-west4", validation_alias='GOOGLE_CLOUD_LOCATION')
    USE_VERTEXAI: bool = Field(True, validation_alias='GOOGLE_GENAI_USE_VERTEXAI')

    # Service Host/Port Configuration
    CALLING_SERVICE_HOST: str = "127.0.0.1"
    CALLING_SERVICE_PORT: int = 8000
    ADK_SERVICE_HOST: str = "127.0.0.1"
    ADK_SERVICE_PORT: int = 8001
    DOWNSTREAM_SERVICE_HOST: str = "127.0.0.1"
    DOWNSTREAM_SERVICE_PORT: int = 8002

    # Agent Configuration
    AGENT_ID: str = "downstream_caller_agent"
    
    # Gemini Configuration
    GEMINI_MODEL: str = "gemini-2.5-flash"

    @computed_field
    @property
    def ADK_SERVICE_BASE_URL(self) -> str:
        return f"http://{self.ADK_SERVICE_HOST}:{self.ADK_SERVICE_PORT}"

    @computed_field
    @property
    def DOWNSTREAM_SERVICE_URL(self) -> str:
        return f"http://{self.DOWNSTREAM_SERVICE_HOST}:{self.DOWNSTREAM_SERVICE_PORT}/status"

# Instantiate the settings object to be used across the application
settings = Settings()