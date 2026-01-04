import logging
from typing import List, Any
from sqlalchemy.orm import Session
from src.models.account import Account

logger = logging.getLogger(__name__)

class AccountService:
    """
    Serviço responsável por gerenciar contas financeiras do usuário.
    Camada de domínio (não depende de Streamlit).
    """

    def __init__(self, db: Session):
        self.db = db

    # ======================================================
    # CONSULTA
    # ======================================================
    def listar(self, user_id: int) -> List[Account]:
        """
        Retorna a lista de OBJETOS Account do usuário.
        (Necessário retornar o objeto completo para acessar .id e .name no frontend)
        """
        try:
            # CORREÇÃO: Removemos o .query(Account.name) e usamos .query(Account)
            # para trazer o objeto completo com ID, Name e Balance.
            contas = (
                self.db.query(Account)
                .filter(Account.user_id == user_id)
                .order_by(Account.name)
                .all()
            )
            return contas

        except Exception:
            logger.exception(
                "Erro ao listar contas | user_id=%s", user_id
            )
            return []

    # ======================================================
    # CRIAÇÃO
    # ======================================================
    def criar(self, user_id: int, conta: str, saldo: Any = 0.0) -> None:
        """
        Cria uma nova conta financeira para o usuário.
        Lança exceção em caso de erro.
        """
        nome_conta = str(conta).strip()
        if not nome_conta:
            raise ValueError("Nome da conta inválido")

        valor_inicial = self._normalizar_valor(saldo)

        try:
            # Verifica duplicidade
            existente = (
                self.db.query(Account)
                .filter(
                    Account.user_id == user_id,
                    Account.name == nome_conta
                )
                .first()
            )

            if existente:
                raise ValueError("Conta já existe para este usuário")

            # Criação do objeto
            conta_db = Account(
                user_id=user_id,
                name=nome_conta,
                # Certifique-se que seu model Account tem a coluna 'balance'
                # Caso não tenha, remova a linha abaixo.
                # balance=valor_inicial 
            )

            self.db.add(conta_db)
            self.db.commit()

            logger.info(
                "Conta criada | user_id=%s conta=%s saldo=%.2f",
                user_id, nome_conta, valor_inicial
            )

        except Exception as e:
            self.db.rollback()
            logger.exception(
                "Erro ao criar conta | user_id=%s conta=%s",
                user_id, nome_conta
            )
            raise e

    # ======================================================
    # UTIL
    # ======================================================
    @staticmethod
    def _normalizar_valor(valor: Any) -> float:
        """Converte valor monetário para float seguro."""
        try:
            return float(str(valor).replace(",", "."))
        except Exception:
            raise ValueError(f"Saldo inválido: {valor}")