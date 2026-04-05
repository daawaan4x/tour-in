"""Runtime configuration helpers for backend deployment."""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_ENVIRONMENT = "development"
PRODUCTION_ENVIRONMENT = "production"
DEFAULT_PORT = 5000
MIN_PORT = 1
MAX_PORT = 65535
DEFAULT_CORS_ALLOWED_ORIGIN = "*"


@dataclass(frozen=True, slots=True)
class ServerConfig:
    """Backend settings loaded from environment variables."""

    environment: str
    port: int
    graphml_path: str | None
    cors_allowed_origin: str


def load_server_config() -> ServerConfig:
    """Load backend config and validate production-critical settings."""
    environment = os.getenv("TOURIN_ENV", DEFAULT_ENVIRONMENT).strip().lower()
    port = _parse_port()
    graphml_path = _optional("TOURIN_GRAPHML_PATH")
    cors_allowed_origin = _optional("TOURIN_CORS_ALLOWED_ORIGIN")

    if environment == PRODUCTION_ENVIRONMENT:
        missing = []
        if not graphml_path:
            missing.append("TOURIN_GRAPHML_PATH")
        if not cors_allowed_origin:
            missing.append("TOURIN_CORS_ALLOWED_ORIGIN")
        if missing:
            missing_text = ", ".join(missing)
            msg = (
                "Missing required environment variables for production: "
                f"{missing_text}"
            )
            raise RuntimeError(msg)

    return ServerConfig(
        environment=environment,
        port=port,
        graphml_path=graphml_path,
        cors_allowed_origin=cors_allowed_origin or DEFAULT_CORS_ALLOWED_ORIGIN,
    )


def _optional(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _parse_port() -> int:
    raw_port = os.getenv("TOURIN_PORT")
    if raw_port is None or not raw_port.strip():
        return DEFAULT_PORT

    try:
        port = int(raw_port)
    except ValueError as exc:
        msg = "TOURIN_PORT must be an integer."
        raise RuntimeError(msg) from exc

    if not (MIN_PORT <= port <= MAX_PORT):
        msg = f"TOURIN_PORT must be between {MIN_PORT} and {MAX_PORT}."
        raise RuntimeError(msg)
    return port
