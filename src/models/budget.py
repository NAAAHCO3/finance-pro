from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base

class Budget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Ligação correta com a tabela de categorias
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    limit_amount = Column(Float, nullable=False)

    # Relacionamentos para acessar os dados (ex: budget.category.name)
    user = relationship("User", back_populates="budgets")
    category = relationship("Category", back_populates="budgets")