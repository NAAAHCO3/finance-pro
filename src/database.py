import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Tenta pegar a URL do banco dos segredos do Streamlit
# Se não existir (rodando local sem config), usa SQLite local como fallback
try:
    # No Streamlit Cloud, usaremos st.secrets["DATABASE_URL"]
    SQLALCHEMY_DATABASE_URL = st.secrets["DATABASE_URL"]
    
    # Ajuste para compatibilidade do driver (postgres:// -> postgresql://)
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)
        
except FileNotFoundError:
    # Fallback para local se não houver secrets configurado
    SQLALCHEMY_DATABASE_URL = "sqlite:///./finance.db"
except Exception:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./finance.db"

# Cria a engine
# Se for SQLite, precisa do check_same_thread=False
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
else:
    # Configuração para PostgreSQL (Neon/Supabase)
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Função auxiliar para pegar o banco
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()