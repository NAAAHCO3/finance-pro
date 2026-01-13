import logging
import pandas as pd
import numpy as np
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MLService:
    """
    Serviço de Estatística Descritiva (Substitui o antigo ML preditivo).
    Foca em "O que aconteceu" (Fatos) em vez de "O que vai acontecer" (Adivinhação).
    """
    def __init__(self, db=None):
        self.db = db

    def analisar_padrao_gastos(self, df_mes: pd.DataFrame) -> Dict[str, Any]:
        """
        Gera um relatório estatístico concreto sobre o mês atual:
        1. Média diária real (intensidade do gasto).
        2. Maior gasto único (pico).
        3. Frequência (quantos dias o usuário abriu a carteira).
        4. Curva ABC (Pareto): Quais categorias levam 80% do dinheiro.
        """
        try:
            # Payload vazio padrão
            stats_padrao = {
                "media_diaria": 0.0,
                "maior_gasto": 0.0,
                "dias_com_gasto": 0,
                "pareto": pd.DataFrame()
            }

            if df_mes.empty:
                return stats_padrao

            # Filtra apenas saídas (gastos)
            # Garantimos que 'amount' é numérico para evitar erros de soma
            df_gasto = df_mes[df_mes["type"] == "gasto"].copy()
            
            if df_gasto.empty:
                return stats_padrao

            # ======================================================
            # 1. ESTATÍSTICAS BÁSICAS (KPIs)
            # ======================================================
            total_gasto = df_gasto["amount"].sum()
            
            # Conta dias únicos que tiveram saída de dinheiro (Payment Date)
            if "payment_date" in df_gasto.columns:
                dias_com_gasto = df_gasto["payment_date"].dt.day.nunique()
            else:
                dias_com_gasto = 1 # Fallback
            
            # Média de Intensidade: Quando gasta, gasta quanto em média por dia?
            media_por_dia_ativo = total_gasto / max(dias_com_gasto, 1)
            
            maior_gasto_unico = df_gasto["amount"].max()

            # ======================================================
            # 2. ANÁLISE DE PARETO (CURVA ABC - 80/20)
            # ======================================================
            # Agrupa por categoria
            pareto = df_gasto.groupby("category")["amount"].sum().reset_index()
            
            # Ordena do maior para o menor (Essencial para Pareto)
            pareto = pareto.sort_values(by="amount", ascending=False)
            
            # Calcula % individual e acumulada
            pareto["percent"] = (pareto["amount"] / total_gasto) * 100
            pareto["cumulative"] = pareto["percent"].cumsum()
            
            # Classificação ABC
            # A: Vitais (acumulam até 80% do valor)
            # B: Importantes (acumulam de 80% a 95%)
            # C: Triviais (o resto)
            def classificar_abc(row):
                if row["cumulative"] <= 80: return "A (Prioridade Alta)"
                elif row["cumulative"] <= 95: return "B (Média)"
                else: return "C (Baixa)"
            
            pareto["class"] = pareto.apply(classificar_abc, axis=1)

            return {
                "media_diaria": float(media_por_dia_ativo),
                "maior_gasto": float(maior_gasto_unico),
                "dias_com_gasto": int(dias_com_gasto),
                "pareto": pareto  # DataFrame com colunas: category, amount, percent, cumulative, class
            }

        except Exception as e:
            logger.error(f"Erro na análise estatística: {e}")
            return {
                "media_diaria": 0.0,
                "maior_gasto": 0.0,
                "dias_com_gasto": 0,
                "pareto": pd.DataFrame()
            }