import os
from pathlib import Path
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "IBVAP - Intelligent Border Video Analytics Platform"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"

    # Workspace & File Paths (Absolute)
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    WORKSPACE_ROOT: Path = Path(__file__).resolve().parent.parent.parent.parent

    DATA_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent / "data"
    EVIDENCE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "evidence"
    CROSSINGS_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "vehicle_crossings"
    UPLOADS_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "uploads"
    AI_CORE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent / "OutLiners_SIH"

    # SQLite Database Configuration
    DATABASE_URL: str = ""

    # Security
    SECRET_KEY: str = "ibvap-tactical-sentry-secret-key-sih-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("DATA_DIR", "EVIDENCE_DIR", "CROSSINGS_DIR", "UPLOADS_DIR", "AI_CORE_DIR", mode="after")
    @classmethod
    def resolve_paths(cls, v: Path) -> Path:
        workspace_root = Path(__file__).resolve().parent.parent.parent.parent
        if not v.is_absolute():
            cand = (workspace_root / v).resolve()
            return cand
        return v.resolve()

    @field_validator("DATABASE_URL", mode="after")
    @classmethod
    def resolve_db_url(cls, v: str) -> str:
        workspace_root = Path(__file__).resolve().parent.parent.parent.parent
        data_dir = workspace_root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure local ./data directory in current working directory exists
        Path("./data").resolve().mkdir(parents=True, exist_ok=True)

        if not v or v == "sqlite:///./data/ibvap.db":
            db_file = data_dir / "ibvap.db"
            return f"sqlite:///{db_file.as_posix()}"
        
        if v.startswith("sqlite:///./"):
            rel_subpath = v.replace("sqlite:///./", "")
            target_path = (workspace_root / rel_subpath).resolve()
            target_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{target_path.as_posix()}"

        return v

    def ensure_directories(self) -> None:
        """Ensures all essential local storage directories exist."""
        for directory in [self.DATA_DIR, self.EVIDENCE_DIR, self.CROSSINGS_DIR, self.UPLOADS_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Ensure local ./data and backend/data directories exist
        Path("./data").mkdir(parents=True, exist_ok=True)
        (self.BASE_DIR / "data").mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.ensure_directories()
