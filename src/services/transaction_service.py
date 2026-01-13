import logging
import pandas as pd
from datetime import date
from typing import Any, Optional
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from src.models.transaction import Transaction
from src.models.category import Category
from src.models.account import Account

logger = logging.getLogger(__name__)

class TransactionService:
    TIPOS_VALIDOS = {"gasto", "renda"}

    def __init__(self, db: Session):
        self.db = db

    def registrar(
        self,
        user_id: int,
        tipo: str,
        valor_total: Any,
        category_id: int,  # ALTERADO: Recebe ID direto
        account_id: int,   # ALTERADO: Recebe ID direto
        descricao: str = "",
        data_compra: Optional[date] = None,
        data_pagamento: Optional[date] = None,
        parcelas: int = 1
    ) -> None:
        """
        Registra transações usando IDs diretos (Performance e Segurança melhoradas).
        """
        tipo_normalizado = self._validar_tipo(tipo)
        valor_num = self._normalizar_valor(valor_total)
        
        # Datas padrão
        dt_compra = data_compra if data_compra else date.today()
        dt_pagamento_inicial = data_pagamento if data_pagamento else dt_compra

        try:
            # LÓGICA DE PARCELAMENTO
            if parcelas > 1:
                valor_parcela = valor_num / parcelas
                
                for i in range(parcelas):
                    dt_vencimento = dt_pagamento_inicial + relativedelta(months=i)
                    tag_parcela = f"{i+1}/{parcelas}"
                    desc_final = f"{descricao} ({tag_parcela})" if descricao else f"Parcela {tag_parcela}"

                    nova = Transaction(
                        user_id=user_id,
                        type=tipo_normalizado,
                        amount=valor_parcela,
                        category_id=category_id, # ID direto
                        account_id=account_id,   # ID direto
                        description=desc_final,
                        date=dt_compra,           
                        payment_date=dt_vencimento,
                        installment=tag_parcela
                    )
                    self.db.add(nova)
            else:
                # Transação única
                nova = Transaction(
                    user_id=user_id,
                    type=tipo_normalizado,
                    amount=valor_num,
                    category_id=category_id, # ID direto
                    account_id=account_id,   # ID direto
                    description=descricao,
                    date=dt_compra,
                    payment_date=dt_pagamento_inicial,
                    installment=None
                )
                self.db.add(nova)

            self.db.commit()
            logger.info("Transação registrada | user_id=%s parcelas=%s", user_id, parcelas)

        except Exception as e:
            self.db.rollback()
            logger.exception("Erro ao registrar transação")
            raise e

    def df_usuario(self, user_id: int) -> pd.DataFrame:
        try:
            query = (
                self.db.query(
                    Transaction.id,
                    Transaction.date,
                    Transaction.payment_date,
                    Transaction.type,
                    Transaction.amount,
                    Transaction.description,
                    Transaction.installment,
                    Category.name.label("category"),
                    Account.name.label("account_name")
                )
                .join(Category, Transaction.category_id == Category.id)
                .join(Account, Transaction.account_id == Account.id)
                .filter(Transaction.user_id == user_id)
                .order_by(Transaction.payment_date.desc())
            )

            df = pd.read_sql(query.statement, self.db.bind)
            if df.empty: return pd.DataFrame()
            return self._limpar_dataframe(df)

        except Exception:
            logger.exception("Erro ao gerar DF")
            return pd.DataFrame()

    def deletar(self, user_id: int, transaction_id: int) -> bool:
        try:
            transacao = self.db.query(Transaction).filter(
                Transaction.id == transaction_id, Transaction.user_id == user_id
            ).first()
            if not transacao: return False
            self.db.delete(transacao)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False

    @staticmethod
    def _normalizar_valor(valor: Any) -> float:
        try:
            return float(str(valor).replace(",", "."))
        except:
            raise ValueError(f"Valor inválido: {valor}")

    def _validar_tipo(self, tipo: str) -> str:
        if tipo not in self.TIPOS_VALIDOS:
            raise ValueError(f"Tipo inválido: {tipo}")
        return tipo

    @staticmethod
    def _limpar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        if "payment_date" in df.columns:
            df["payment_date"] = pd.to_datetime(df["payment_date"])
        if "amount" in df.columns:
            df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
        return df