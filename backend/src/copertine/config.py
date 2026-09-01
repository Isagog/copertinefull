"""Configuration and logging. Read once, at startup, and never mutated."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

#: A cover JPEG runs 100-450 KB. The ceiling exists because `fetch_asset`
#: refuses to buffer without one — an unguarded whole-file read is the defect
#: the corpus library removed.
DEFAULT_MAX_IMAGE_BYTES = 25 * 1024 * 1024

DEFAULT_DIRECTUS_URL = "https://pulse.ilmanifesto.it"

#: Project root, four levels up from backend/src/copertine/config.py.
_PROJECT_ROOT = Path(__file__).parents[3]


class MissingEnvironmentVariableError(RuntimeError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Environment variable '{name}' must be set.")
        self.name = name


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    directus_url: str
    directus_token: str
    images_dir: Path
    max_image_bytes: int


def load_settings() -> Settings:
    """Build settings from the project-root `.secrets` plus the environment."""
    load_dotenv(dotenv_path=_PROJECT_ROOT / ".secrets", override=True)
    images_dir = Path(os.getenv("COP_IMAGES_DIR") or _PROJECT_ROOT / "images")
    images_dir.mkdir(parents=True, exist_ok=True)
    return Settings(
        database_url=_required("DATABASE_URL"),
        directus_url=os.getenv("COP_DIRECTUS_URL") or DEFAULT_DIRECTUS_URL,
        directus_token=_required("DIRECTUS_API_TOKEN"),
        images_dir=images_dir,
        max_image_bytes=_positive_int("COP_MAX_IMAGE_BYTES", DEFAULT_MAX_IMAGE_BYTES),
    )


def setup_logging() -> logging.Logger:
    """stderr always; a log FILE only when COP_LOG_FILE is set.

    In a container an unconditional log file is both invisible (it lands in the
    writable layer) and unbounded, whereas stderr goes to Docker's json-file
    driver, which the compose file rotates.
    """
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    log_file = os.getenv("COP_LOG_FILE")
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        handlers=handlers,
    )
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    return logging.getLogger("copertine")


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise MissingEnvironmentVariableError(name)
    return value


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default
