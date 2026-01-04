from pathlib import Path
import os

# =========================================================
# BASE PATHS
# =========================================================

# Diretório raiz do projeto
BASE_DIR = Path(__file__).resolve().parents[2]

# =========================================================
# DATABASE
# =========================================================

DB_NAME = os.getenv("DB_NAME", "finance.db")
DB_PATH = BASE_DIR / DB_NAME
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DB_PATH}"
)

# =========================================================
# SECURITY
# =========================================================

# Tempo de sessão (horas)
SESSION_EXPIRE_HOURS = int(os.getenv("SESSION_EXPIRE_HOURS", 8))

# =========================================================
# APP
# =========================================================

APP_NAME = os.getenv("APP_NAME", "Finance DS")
APP_ICON = os.getenv("APP_ICON", "💰")

# =========================================================
# ENV
# =========================================================

ENV = os.getenv("ENV", "dev")  # dev | prod
DEBUG = ENV == "dev"
