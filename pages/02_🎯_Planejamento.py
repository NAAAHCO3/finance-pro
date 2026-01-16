import streamlit as st
import pandas as pd
from datetime import date

from src.database import get_db
from src.services.budget_service import BudgetService
from src.services.category_service import CategoryService
from src.services.transaction_service import TransactionService

st.set_page_config(page_title="Planejamento", page_icon="🎯", layout="wide")

def main():
    if not st.session_state.get("logged_in"):
        st.warning("Faça login.")
        return

    user_id = st.session_state.user_id
    hoje = date.today()

    st.title("🎯 Planejamento Mensal")

    with get_db() as db:
        srv_budget = BudgetService(db)
        srv_cat = CategoryService(db)
        srv_trans = TransactionService(db)

        st.sidebar.header("📅 Período")
        ano = st.sidebar.number_input("Ano", value=hoje.year, min_value=2020, max_value=2030)
        mes = st.sidebar.selectbox("Mês", range(1, 13), index=hoje.month - 1)

        with st.expander("➕ Definir Meta"):
            cats = srv_cat.listar_por_tipo(user_id, "gasto")
            if cats:
                with st.form("meta"):
                    cat = st.selectbox("Categoria", cats, format_func=lambda x: x.name)
                    limite = st.number_input("Limite", min_value=1.0, step=50.0)
                    if st.form_submit_button("Salvar"):
                        srv_budget.definir_orcamento(user_id, cat.id, limite)
                        st.toast("Meta salva!")
                        st.rerun()
            else:
                st.info("Cadastre categorias de gasto.")

        st.divider()
        st.subheader(f"📊 Progresso — {mes}/{ano}")

        orcamentos = srv_budget.listar(user_id)
        if not orcamentos:
            st.info("Nenhuma meta definida.")
            return

        df = srv_trans.df_usuario(user_id)
        if not df.empty:
            df["payment_date"] = pd.to_datetime(df["payment_date"])
            df = df[
                (df["payment_date"].dt.year == ano) &
                (df["payment_date"].dt.month == mes) &
                (df["type"] == "gasto")
            ]

        for o in sorted(orcamentos, key=lambda x: x.category.name):
            gasto = df[df["category"] == o.category.name]["amount"].sum() if not df.empty else 0
            pct = min(gasto / o.limit_amount, 1)

            st.markdown(f"**{o.category.name}**")
            st.progress(pct)
            st.caption(f"Gasto: R$ {gasto:.2f} / Limite: R$ {o.limit_amount:.2f}")

if __name__ == "__main__":
    main()
