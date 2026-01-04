import logging
from typing import Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Serviço responsável por métricas, agregações e análises financeiras.
    """

    # ======================================================
    # KPIs
    # ======================================================
    def kpis_mensais(
        self,
        df: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Calcula KPIs básicos do período selecionado.
        """
        if df is None or df.empty:
            return {
                "receita": 0.0,
                "despesa": 0.0,
                "saldo": 0.0
            }

        try:
            receita = df.loc[df["type"] == "renda", "amount"].sum()
            despesa = df.loc[df["type"] == "gasto", "amount"].sum()
            saldo = receita - despesa

            return {
                "receita": float(receita),
                "despesa": float(despesa),
                "saldo": float(saldo)
            }

        except Exception:
            logger.exception("Erro ao calcular KPIs")
            return {
                "receita": 0.0,
                "despesa": 0.0,
                "saldo": 0.0
            }

    # ======================================================
    # COMPARAÇÃO TEMPORAL
    # ======================================================
    def comparacao_periodos(
        self,
        df_atual: pd.DataFrame,
        df_anterior: Optional[pd.DataFrame]
    ) -> Dict[str, float]:
        """
        Compara KPIs entre dois períodos.
        Retorna deltas absolutos.
        """
        atual = self.kpis_mensais(df_atual)
        anterior = self.kpis_mensais(df_anterior)

        return {
            "delta_receita": atual["receita"] - anterior["receita"],
            "delta_despesa": atual["despesa"] - anterior["despesa"],
            "delta_saldo": atual["saldo"] - anterior["saldo"]
        }

    # ======================================================
    # AGREGAÇÕES
    # ======================================================
    def despesas_por_categoria(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Retorna gastos agregados por categoria.
        """
        if df is None or df.empty:
            return pd.DataFrame()

        try:
            df_cat = (
                df[df["type"] == "gasto"]
                .groupby("category", as_index=False)["amount"]
                .sum()
                .sort_values("amount", ascending=False)
            )

            return df_cat

        except Exception:
            logger.exception("Erro ao agregar despesas por categoria")
            return pd.DataFrame()

    def fluxo_diario(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Retorna fluxo financeiro diário (renda vs gasto).
        """
        if df is None or df.empty:
            return pd.DataFrame()

        try:
            df_out = (
                df
                .groupby(["date", "type"], as_index=False)["amount"]
                .sum()
                .sort_values("date")
            )

            return df_out

        except Exception:
            logger.exception("Erro ao gerar fluxo diário")
            return pd.DataFrame()

    # ======================================================
    # SÉRIES TEMPORAIS
    # ======================================================
    def serie_mensal(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Retorna série temporal mensal de receita, despesa e saldo.
        """
        if df is None or df.empty:
            return pd.DataFrame()

        try:
            df_ts = df.copy()
            df_ts["date"] = pd.to_datetime(df_ts["date"], errors="coerce")
            df_ts["year_month"] = df_ts["date"].dt.to_period("M")

            resumo = (
                df_ts
                .groupby(["year_month", "type"])["amount"]
                .sum()
                .unstack(fill_value=0)
                .reset_index()
            )

            resumo["saldo"] = (
                resumo.get("renda", 0) - resumo.get("gasto", 0)
            )

            resumo["year_month"] = resumo["year_month"].astype(str)

            return resumo.sort_values("year_month")

        except Exception:
            logger.exception("Erro ao gerar série mensal")
            return pd.DataFrame()

    # ======================================================
    # INSIGHTS SIMPLES
    # ======================================================
    def insights_rapidos(
        self,
        df: pd.DataFrame
    ) -> Dict[str, Optional[str]]:
        """
        Gera insights simples baseados nos dados.
        """
        if df is None or df.empty:
            return {}

        try:
            gastos = df[df["type"] == "gasto"]

            if gastos.empty:
                return {}

            maior_categoria = (
                gastos
                .groupby("category")["amount"]
                .sum()
                .idxmax()
            )

            maior_gasto = gastos["amount"].max()

            return {
                "maior_categoria": maior_categoria,
                "maior_gasto": f"R$ {maior_gasto:,.2f}"
            }

        except Exception:
            logger.exception("Erro ao gerar insights")
            return {}
