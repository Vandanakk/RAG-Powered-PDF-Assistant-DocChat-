import os
from pathlib import Path
from dotenv import load_dotenv

# Find project root (directory containing .git or README.md)
CURRENT_FILE = Path(__file__).resolve()
BACKEND_APP_DIR = CURRENT_FILE.parent
BACKEND_DIR = BACKEND_APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

# Load .env from project root or backend dir
env_path = PROJECT_ROOT / ".env"
if not env_path.exists():
    env_path = BACKEND_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

def parse_cors_origins(raw_val) -> list:
    """
    Safely parse CORS_ORIGINS from environment variables.
    Handles comma-separated strings, JSON lists, whitespace, quotes, and trailing slashes.
    Guarantees localhost and 127.0.0.1 on ports 5173 and 5174 are always present.
    """
    base_defaults = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]
    if not raw_val:
        return base_defaults

    origins = []
    if isinstance(raw_val, (list, tuple)):
        items = list(raw_val)
    else:
        raw_str = str(raw_val).strip()
        if raw_str.startswith("[") and raw_str.endswith("]"):
            try:
                import json
                items = json.loads(raw_str)
            except Exception:
                items = raw_str.strip("[]").split(",")
        else:
            items = raw_str.split(",")

    for item in items:
        # Strip whitespace, surrounding quotes, and any trailing slash
        clean = str(item).strip().strip("\"'").rstrip("/")
        # Never allow wildcard '*' with credentialed CORS requests
        if clean and clean != "*" and clean not in origins:
            origins.append(clean)

    for default in base_defaults:
        if default not in origins:
            origins.append(default)

    return origins

def get_gemini_api_key() -> str:
    """
    Dynamically retrieve and re-read GEMINI_API_KEY.
    Checks environment and reloads .env if missing or placeholder.
    Strips surrounding quotes and whitespace.
    """
    key = os.getenv("GEMINI_API_KEY", "").strip().strip("\"'")
    if key and key not in ("your_gemini_api_key", "your_gemini_api_key_here"):
        return key

    # Re-check .env from project root, backend dir, or current working dir
    for candidate in [PROJECT_ROOT / ".env", BACKEND_DIR / ".env", Path(".env")]:
        if candidate.exists():
            load_dotenv(dotenv_path=candidate, override=True)
            key = os.getenv("GEMINI_API_KEY", "").strip().strip("\"'")
            if key and key not in ("your_gemini_api_key", "your_gemini_api_key_here"):
                return key
    return key

class Settings:
    PROJECT_NAME: str = "DocChat API"
    VERSION: str = "1.0.0"

    # Server Port (platform-injected $PORT e.g. on Render, or default 8000)
    @property
    def PORT(self) -> int:
        return int(os.getenv("PORT", "8000"))

    # API Keys & Models
    @property
    def GEMINI_API_KEY(self) -> str:
        return get_gemini_api_key()

    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")

    # Storage paths (supports DATA_DIR for persistent cloud disks)
    @property
    def DATA_DIR(self) -> Path:
        data_dir_env = os.getenv("DATA_DIR", "").strip()
        return Path(data_dir_env).resolve() if data_dir_env else (PROJECT_ROOT / "data").resolve()

    @property
    def CHROMA_PERSIST_DIR(self) -> str:
        chroma_env = os.getenv("CHROMA_PERSIST_DIR", "").strip()
        if chroma_env:
            p = Path(chroma_env)
            if p.is_absolute():
                return str(p)
            if os.getenv("DATA_DIR"):
                return str((self.DATA_DIR / p.name).resolve())
            return str((PROJECT_ROOT / p).resolve())
        return str((self.DATA_DIR / "chroma").resolve())

    @property
    def DOCUMENTS_REGISTRY_PATH(self) -> str:
        registry_env = os.getenv("DOCUMENTS_REGISTRY_PATH", "").strip()
        if registry_env:
            p = Path(registry_env)
            if p.is_absolute():
                return str(p)
            if os.getenv("DATA_DIR"):
                return str((self.DATA_DIR / p.name).resolve())
            return str((PROJECT_ROOT / p).resolve())
        return str((self.DATA_DIR / "documents.json").resolve())


    # Chunking & Retrieval parameters
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))
    TOP_K_CHUNKS: int = int(os.getenv("TOP_K_CHUNKS", "5"))

    # Security & Limits
    MAX_UPLOAD_SIZE_BYTES: int = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(20 * 1024 * 1024)))  # 20 MB

    # CORS
    _cors_env = os.getenv("CORS_ORIGINS", "")
    CORS_ORIGINS: list = parse_cors_origins(_cors_env)
    _cors_regex_env = os.getenv("CORS_ORIGIN_REGEX", "")
    CORS_ORIGIN_REGEX: str = _cors_regex_env if _cors_regex_env else r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$|^https://.*\.vercel\.app$|^https://.*\.onrender\.com$"

settings = Settings()




