from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "dev"

    database_url: str = "sqlite:///./talash.db"

    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemma-4-26b-a4b-it:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    education_analysis_model: str = ""
    skills_analysis_model: str = ""
    experience_analysis_model: str = ""
    research_analysis_model: str = ""

    supabase_project_url: str = ""
    supabase_publishable_key: str = ""
    supabase_service_role_key: str = ""
    supabase_bucket_name: str = "cv-files"


settings = Settings()
