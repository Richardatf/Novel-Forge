from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    data_dir: Path = Path(os.getenv("NOVEL_FORGE_DATA_DIR", ROOT / "data"))
    export_dir: Path = Path(os.getenv("NOVEL_FORGE_EXPORT_DIR", ROOT / "exports"))
    model: str = os.getenv("NOVEL_FORGE_MODEL", "gpt-5-mini")

    @property
    def db_path(self) -> Path:
        return self.data_dir / "novel_forge.db"

    @property
    def backup_dir(self) -> Path:
        return self.data_dir / "backups"


settings = Settings()

