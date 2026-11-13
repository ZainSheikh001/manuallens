"""Project settings, read from environment variables or a .env file."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    data_dir: Path = Path("data")
    render_dpi: int = 150
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""

    @property
    def manifest_path(self) -> Path:
        return self.data_dir / "manifest.csv"

    @property
    def raw_dir(self) -> Path:
        """Downloaded PDFs, one per manual."""
        return self.data_dir / "raw"

    @property
    def pages_dir(self) -> Path:
        """Rendered page images and pages.jsonl metadata."""
        return self.data_dir / "pages"


settings = Settings()
