import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager # <--- 1. IMPORTAÇÃO NOVA
import os

# Tenta pegar a URL do banco dos segredos do Streamlit
try:
    SQLALCHEMY_DATABASE_URL = st.secrets["DATABASE_URL"]
    
    # Fix para compatibilidade do driver PostgreSQL (postgres:// -> postgresql://)
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)
        
except FileNotFoundError:
    # Fallback para local se não houver secrets
    SQLALCHEMY_DATABASE_URL = "sqlite:///./finance.db"
except Exception:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./finance.db"

# Cria a engine
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    # Configuração para PostgreSQL (Nuvem)
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# --- AQUI ESTAVA O PROBLEMA ---
@contextmanager # <--- 2. ADICIONAR ESTE DECORADOR
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()