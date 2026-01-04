from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
import datetime # Alterado para importar o módulo inteiro e evitar conflito de nomes
from src.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    
    type = Column(String, nullable=False)  # 'renda' ou 'gasto'
    amount = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    
    # NOVAS COLUNAS
    # Usamos datetime.date.today para não confundir com o nome da coluna 'date'
    date = Column(Date, default=datetime.date.today)          # Competência (Compra)
    payment_date = Column(Date, default=datetime.date.today)  # Caixa (Pagamento)
    installment = Column(String, nullable=True)               # Ex: "1/10"

    # Relacionamentos
    user = relationship("User", back_populates="transactions")
    category = relationship("Category")
    account = relationship("Account", back_populates="transactions")