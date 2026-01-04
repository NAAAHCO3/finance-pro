import streamlit as st
import pandas as pd
from typing import Tuple


# ======================================================
# FEEDBACK / MENSAGENS
# ======================================================
def info_empty(msg: str = "Nenhum dado disponível."):
    st.info(msg)


def error(msg: str):
    st.error(msg)


def success(msg: str):
    st.success(msg)


# ======================================================
# KPIs
# ======================================================
def kpi_financeiros(receita: float, gasto: float):
    saldo = receita - gasto

    c1, c2, c3 = st.columns(3)
    c1.metric("Receitas", f"R$ {receita:,.2f}")
    c2.metric("Despesas", f"R$ {gasto:,.2f}")
    c3.metric("Saldo", f"R$ {saldo:,.2f}")


# ======================================================
# FILTRO DE PERÍODO
# ======================================================
def filtro_periodo(
    df: pd.DataFrame,
    sidebar: bool = True
) -> Tuple[pd.DataFrame, int, int]:
    """
    Aplica filtro de ano/mês ao DataFrame.

    Retorna:
        df_filtrado, ano, mes
    """
    if df is None or df.empty:
        return pd.DataFrame(), None, None

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month

    container = st.sidebar if sidebar else st

    container.markdown("### 📅 Período")

    year = container.selectbox(
        "Ano",
        sorted(df["year"].unique(), reverse=True)
    )

    month = container.selectbox(
        "Mês",
        sorted(df[df["year"] == year]["month"].unique(), reverse=True)
    )

    df_filtered = df[
        (df["year"] == year) &
        (df["month"] == month)
    ]

    return df_filtered, year, month


# ======================================================
# DATAFRAME
# ======================================================
def dataframe_safe(
    df: pd.DataFrame,
    columns: list = None,
    sort_by: str = None
):
    if df is None or df.empty:
        info_empty("Nenhum registro encontrado.")
        return

    if columns:
        df = df[columns]

    if sort_by and sort_by in df.columns:
        df = df.sort_values(sort_by, ascending=False)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


# ======================================================
# ORÇAMENTO (PROGRESS)
# ======================================================
def barra_orcamento(
    categoria: str,
    gasto: float,
    limite: float
):
    if limite <= 0:
        return

    percentual = min(gasto / limite, 1.0)

    st.write(f"**{categoria}**")
    st.progress(percentual)
    st.caption(
        f"Gasto: R$ {gasto:,.2f} / Limite: R$ {limite:,.2f}"
    )


# ======================================================
# CONFIRMAÇÃO SIMPLES
# ======================================================
def confirm_button(label: str, key: str) -> bool:
    """
    Botão de confirmação simples (evita cliques acidentais)
    """
    if f"confirm_{key}" not in st.session_state:
        st.session_state[f"confirm_{key}"] = False

    if not st.session_state[f"confirm_{key}"]:
        if st.button(label):
            st.session_state[f"confirm_{key}"] = True
        return False
    else:
        st.warning("Clique novamente para confirmar")
        if st.button("Confirmar"):
            st.session_state[f"confirm_{key}"] = False
            return True

    return False
