from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_DEFAULT_SQLITE = f"sqlite:///{(_BACKEND_DIR / 'talash.db').as_posix()}"


def _env_files() -> tuple[str, ...]:
    candidates = (_BACKEND_DIR / ".env", _PROJECT_ROOT / ".env")
    found = tuple(str(path) for path in candidates if path.is_file())
    return found if found else (".env",)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "dev"

    database_url: str = _DEFAULT_SQLITE

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
