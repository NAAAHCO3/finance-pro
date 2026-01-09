import logging
from typing import List, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
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
        """
        try:
            return (
                self.db.query(Account)
                .filter(Account.user_id == user_id)
                .order_by(Account.name)
                .all()
            )
        except Exception:
            logger.exception("Erro ao listar contas | user_id=%s", user_id)
            return []

    # ======================================================
    # CRIAÇÃO
    # ======================================================
    def criar(self, user_id: int, conta: str, saldo: Any = 0.0) -> None:
        """
        Cria uma nova conta financeira.
        """
        nome_conta = str(conta).strip()
        if not nome_conta:
            raise ValueError("Nome da conta inválido")

        # valor_inicial = self._normalizar_valor(saldo) # (Opcional, se tiver saldo inicial)

        try:
            # Verifica duplicidade
            existente = (
                self.db.query(Account)
                .filter(Account.user_id == user_id, Account.name == nome_conta)
                .first()
            )

            if existente:
                raise ValueError("Conta já existe para este usuário")

            conta_db = Account(
                user_id=user_id,
                name=nome_conta
                # balance=valor_inicial # Descomente se seu model tiver balance e quiser usar
            )

            self.db.add(conta_db)
            self.db.commit()

            logger.info("Conta criada: %s", nome_conta)

        except Exception as e:
            self.db.rollback()
            logger.exception("Erro ao criar conta")
            raise e

    # ======================================================
    # ATUALIZAÇÃO (RENOMEAR)
    # ======================================================
    def atualizar(self, user_id: int, account_id: int, novo_nome: str) -> bool:
        """
        Renomeia uma conta existente.
        """
        nome_limpo = str(novo_nome).strip()
        if not nome_limpo:
            return False

        try:
            acc = self.db.query(Account).filter(
                Account.id == account_id, 
                Account.user_id == user_id
            ).first()

            if acc:
                acc.name = nome_limpo
                self.db.commit()
                logger.info("Conta ID %s renomeada para %s", account_id, nome_limpo)
                return True
            return False
        except Exception:
            self.db.rollback()
            logger.exception("Erro ao atualizar conta")
            return False

    # ======================================================
    # EXCLUSÃO (COM PROTEÇÃO)
    # ======================================================
    def deletar(self, user_id: int, account_id: int) -> Tuple[bool, str]:
        """
        Tenta excluir uma conta.
        Retorna: (Sucesso: bool, Mensagem: str)
        """
        try:
            acc = self.db.query(Account).filter(
                Account.id == account_id, 
                Account.user_id == user_id
            ).first()

            if not acc:
                return False, "Conta não encontrada."
            
            self.db.delete(acc)
            self.db.commit()
            logger.info("Conta ID %s excluída", account_id)
            return True, "Conta excluída com sucesso."

        except IntegrityError:
            self.db.rollback()
            return False, "Não é possível excluir: existem transações vinculadas a esta conta."
        
        except Exception as e:
            self.db.rollback()
            logger.exception("Erro ao deletar conta")
            return False, f"Erro interno: {str(e)}"

    # ======================================================
    # UTIL
    # ======================================================
    @staticmethod
    def _normalizar_valor(valor: Any) -> float:
        try:
            return float(str(valor).replace(",", "."))
        except Exception:
            raise ValueError(f"Valor inválido: {valor}")