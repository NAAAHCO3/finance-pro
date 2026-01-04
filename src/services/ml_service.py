import logging
import pandas as pd
import numpy as np
from datetime import date, timedelta
from calendar import monthrange
from sqlalchemy import func
from sklearn.ensemble import IsolationForest 
from src.models.transaction import Transaction

logger = logging.getLogger(__name__)

class MLService:
    """
    Serviço de Inteligência Financeira 4.0.
    Correção do 'Efeito Aluguel' (projeções exageradas no início do mês).
    """

    def __init__(self, db=None):
        self.db = db

    # ======================================================
    # 1. DETECÇÃO DE ANOMALIAS (Scikit-Learn)
    # ======================================================
    def detectar_anomalias(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or len(df) < 5: # Reduzido minimo para testar
            return pd.DataFrame()

        try:
            df_analise = df[df["type"] == "gasto"].copy()
            if df_analise.empty: return pd.DataFrame()

            # Treina modelo (Isolation Forest)
            # contamination='auto' deixa o algoritmo decidir o quão rigoroso ser
            model = IsolationForest(contamination='auto', random_state=42)
            X = df_analise[["amount"]].values
            
            df_analise["anomaly_score"] = model.fit_predict(X)
            
            # Retorna apenas outliers (-1)
            return df_analise[df_analise["anomaly_score"] == -1]
        except Exception:
            return pd.DataFrame()

    # ======================================================
    # 2. PROJEÇÃO INTELIGENTE (CORRIGIDA)
    # ======================================================
    def calcular_projecao_inteligente(self, user_id: int, df_mes_atual: pd.DataFrame) -> dict:
        """
        Retorna um dicionário com:
        - 'valor': O valor projetado (float)
        - 'metodo': Explicação de qual lógica foi usada (str)
        """
        try:
            hoje = date.today()
            _, dias_no_mes = monthrange(hoje.year, hoje.month)
            dias_passados = hoje.day
            dias_restantes = dias_no_mes - dias_passados

            # 1. Gasto Realizado (Fato)
            gasto_atual = 0.0
            if not df_mes_atual.empty:
                gasto_atual = df_mes_atual[df_mes_atual["type"] == "gasto"]["amount"].sum()

            # Se o mês acabou, a projeção é o real
            if dias_restantes <= 0:
                return {"valor": float(gasto_atual), "metodo": "Mês Fechado"}

            # 2. Busca Ritmo Histórico (Ideal)
            media_historica = self._calcular_media_diaria_historica(user_id)

            if media_historica > 0:
                # CENÁRIO 1: Usuário Veterano (Usa média real dos meses anteriores)
                projecao = gasto_atual + (media_historica * dias_restantes)
                return {"valor": float(projecao), "metodo": "Baseado no seu Histórico"}
            
            else:
                # CENÁRIO 2: Usuário Novo (Cold Start) - AQUI ESTAVA O ERRO
                # Antes fazíamos regra de três. Agora aplicamos "Amortecimento".
                
                if dias_passados > 0:
                    media_atual = gasto_atual / dias_passados
                else:
                    media_atual = 0

                # Lógica: O ritmo de gastos do resto do mês será bem menor que o do início
                # Assumimos um "Custo de Vida Base" mínimo ou 30% da média atual (o que for maior)
                
                # Ex: Se gastou 1000 em 4 dias (média 250), projetamos 
                # que gastará 250 * 0.3 = R$ 75/dia no resto do mês.
                fator_amortecimento = 0.3 
                media_projetada = max(media_atual * fator_amortecimento, 30.0) # Piso de R$30/dia

                projecao = gasto_atual + (media_projetada * dias_restantes)
                
                return {"valor": float(projecao), "metodo": "Estimativa Conservadora (Novo Usuário)"}

        except Exception:
            logger.exception("Erro na projeção")
            return {"valor": 0.0, "metodo": "Erro de Cálculo"}

    def _calcular_media_diaria_historica(self, user_id: int) -> float:
        if self.db is None: return 0.0
        try:
            # Pega histórico de 3 meses atrás até o dia 1 deste mês
            inicio_mes_atual = date.today().replace(day=1)
            data_limite = inicio_mes_atual - timedelta(days=90)
            
            res = (
                self.db.query(func.sum(Transaction.amount), func.count(Transaction.id))
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.type == "gasto",
                    Transaction.payment_date < inicio_mes_atual, # Estritamente anterior a este mês
                    Transaction.payment_date >= data_limite
                )
                .first()
            )
            
            total_gasto = res[0] or 0.0
            
            if total_gasto == 0:
                return 0.0

            # Média simples: total gasto / 90 dias
            return total_gasto / 90.0
        except:
            return 0.0