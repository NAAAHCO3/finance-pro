import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 1. Configuração da URL (Mantivemos igual)
try:
    SQLALCHEMY_DATABASE_URL = st.secrets["DATABASE_URL"]
    if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)
except:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./finance.db"

# 2. Cria a Engine
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 3. MUDANÇA TOTAL AQUI: Classe de Contexto
# Isso evita o TypeError "generator object" de uma vez por todas
class DBConnection:
    def __enter__(self):
        self.db = SessionLocal()
        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()

# Função simples que chama a classe
def get_db():
    return DBConnection()