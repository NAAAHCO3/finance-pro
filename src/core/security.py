from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
import secrets

# =========================================================
# CONFIGURAÇÕES DE SEGURANÇA
# =========================================================

# Algoritmo de hash (padrão de mercado)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

# Tempo padrão de expiração de sessão (em horas)
SESSION_EXPIRE_HOURS = 8

# =========================================================
# HASH DE SENHA
# =========================================================

def hash_password(password: str) -> str:
    """
    Gera hash seguro da senha.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica se a senha informada bate com o hash salvo.
    """
    return pwd_context.verify(plain_password, hashed_password)

# =========================================================
# TOKEN DE SESSÃO (STREAMLIT-FRIENDLY)
# =========================================================

def generate_session_token() -> str:
    """
    Gera um token seguro para sessão.
    (Usado no session_state do Streamlit)
    """
    return secrets.token_urlsafe(32)


def session_expired(
    created_at: datetime,
    expires_hours: int = SESSION_EXPIRE_HOURS
) -> bool:
    """
    Verifica se a sessão expirou.
    """
    return datetime.utcnow() > created_at + timedelta(hours=expires_hours)
