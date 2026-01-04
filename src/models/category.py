from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from src.database import Base

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # 'renda' ou 'gasto'
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Campo opcional, mas útil se você tiver lógica de ativar/desativar
    active = Column(Boolean, default=True) 

    # CORREÇÃO DO ERRO:
    # Esta linha cria a propriedade 'user' que o SQLAlchemy estava reclamando que faltava
    user = relationship("User", back_populates="categories")
    
    # Se houver orçamentos ligados à categoria
    budgets = relationship("Budget", back_populates="category")