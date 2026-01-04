import logging
from typing import List
import pandas as pd
from sqlalchemy.orm import Session
from src.models.budget import Budget
from src.models.category import Category

logger = logging.getLogger(__name__)

class BudgetService:
    """
    Serviço responsável por gerenciar e verificar orçamentos.
    Orçamentos são definidos por usuário e vinculados a uma categoria (por ID).
    """

    def __init__(self, db: Session):
        self.db = db

    # ======================================================
    # CRUD (MÉTODOS ESSENCIAIS QUE FALTAVAM)
    # ======================================================
    def listar(self, user_id: int):
        """
        Retorna a lista de orçamentos definidos pelo usuário.
        Faz JOIN com Categoria para poder exibir o nome na tela.
        """
        try:
            return (
                self.db.query(Budget)
                .join(Category)  # Garante que a categoria existe
                .filter(Budget.user_id == user_id)
                .all()
            )
        except Exception:
            logger.exception("Erro ao listar orçamentos | user_id=%s", user_id)
            return []

    def definir_orcamento(self, user_id: int, category_id: int, limite: float):
        """
        Cria ou Atualiza (Upsert) um orçamento para uma categoria específica.
        """
        try:
            # Verifica se já existe orçamento para essa categoria
            orcamento_existente = (
                self.db.query(Budget)
                .filter(
                    Budget.user_id == user_id,
                    Budget.category_id == category_id
                )
                .first()
            )

            if orcamento_existente:
                # Atualiza existente
                orcamento_existente.limit_amount = limite
                logger.info("Orçamento atualizado | user_id=%s cat_id=%s", user_id, category_id)
            else:
                # Cria novo
                novo_orcamento = Budget(
                    user_id=user_id, 
                    category_id=category_id, 
                    limit_amount=limite
                )
                self.db.add(novo_orcamento)
                logger.info("Orçamento criado | user_id=%s cat_id=%s", user_id, category_id)
            
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            logger.exception("Erro ao definir orçamento")
            raise e

    # ======================================================
    # ALERTAS (LÓGICA CORRIGIDA)
    # ======================================================
    def alertas(
        self,
        user_id: int,
        df_gastos: pd.DataFrame
    ) -> List[str]:
        """
        Verifica se os gastos do usuário ultrapassaram os limites definidos.
        """
        if df_gastos is None or df_gastos.empty:
            return []

        try:
            orcamentos = self.listar(user_id)

            if not orcamentos:
                return []

            alertas = []

            for orcamento in orcamentos:
                # CORREÇÃO: orcamento.category é um OBJETO. Pegamos o .name
                categoria_nome = orcamento.category.name
                limite = orcamento.limit_amount

                total_gasto = self._total_por_categoria(
                    df_gastos, categoria_nome
                )

                if total_gasto >= limite:
                    alertas.append(
                        self._formatar_alerta(
                            categoria_nome, total_gasto, limite
                        )
                    )

            return alertas

        except Exception:
            logger.exception(
                "Erro ao verificar orçamentos | user_id=%s", user_id
            )
            return []

    # ======================================================
    # UTILITÁRIOS
    # ======================================================
    @staticmethod
    def _total_por_categoria(
        df: pd.DataFrame,
        categoria_nome: str
    ) -> float:
        """
        Calcula o total gasto de uma categoria específica.
        """
        try:
            if "category" not in df.columns or "amount" not in df.columns:
                return 0.0

            # Filtra onde a coluna 'category' (nome) bate com o nome da categoria do orçamento
            filtro = (df["category"] == categoria_nome)
            
            # Se houver coluna type, filtra só gasto. Se não houver, assume tudo.
            if "type" in df.columns:
                filtro = filtro & (df["type"] == "gasto")

            return float(df.loc[filtro, "amount"].sum())
        except Exception:
            return 0.0

    @staticmethod
    def _formatar_alerta(
        categoria: str,
        gasto: float,
        limite: float
    ) -> str:
        return (
            f"🚨 {categoria}: R$ {gasto:,.2f} (Limite: R$ {limite:,.2f})"
        )