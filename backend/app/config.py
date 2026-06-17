from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database — required, no default
    database_url: str

    # GitHub OAuth — required for auth flow
    github_client_id: str
    github_client_secret: str
    github_redirect_uri: str = "http://localhost:8000/auth/callback"

    # JWT — required, must be set in env
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    # API keys — required for core functionality
    groq_api_key: str
    voyage_api_key: str

    # Encryption — required, must be at least 32 characters
    encryption_key: str

    # LLM defaults
    default_llm_model: str = "groq/llama-3.1-70b-versatile"
    embedding_model: str = "voyage-code-3"
    embedding_dimension: int = 1024

    # Repo limits
    max_repo_files: int = 500
    max_repo_size_mb: int = 50
    clone_timeout_seconds: int = 120

    # CORS
    frontend_url: str = "http://localhost:5173"

    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("ENCRYPTION_KEY must be at least 32 characters")
        return v

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 16:
            raise ValueError("JWT_SECRET must be at least 16 characters")
        return v

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
