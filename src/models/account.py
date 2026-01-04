from sqlalchemy import Column, Integer, String, ForeignKey, Float
from sqlalchemy.orm import relationship
from src.database import Base

class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    # Adicionei balance pois seu service tenta usá-lo na criação
    balance = Column(Float, default=0.0) 
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Relacionamento reverso
    user = relationship("User", back_populates="accounts")
    
    # Relacionamento com transações (opcional, mas recomendado)
    transactions = relationship("Transaction", back_populates="account")