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
        st.warning("🔒 Faça login.")
        return

    user_id = st.session_state.user_id
    hoje = date.today()

    st.title("🎯 Planejamento de Orçamento")
    
    # CSS Customizado
    st.markdown("""
    <style>
        .stProgress > div > div > div > div {
            background-image: linear-gradient(to right, #00E676, #FFE082, #FF5252);
        }
        div[data-testid="stMetric"] {
            background-color: #1E1E2E;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

    with get_db() as db:
        srv_budget = BudgetService(db)
        srv_cat = CategoryService(db)
        srv_trans = TransactionService(db)

        # Filtros laterais
        st.sidebar.header("📅 Período")
        ano = st.sidebar.number_input("Ano", value=hoje.year, min_value=2020, max_value=2030)
        mes = st.sidebar.selectbox("Mês", range(1, 13), index=hoje.month - 1)

        # Configurar Meta
        with st.expander("➕ Definir Nova Meta"):
            cats = srv_cat.listar_por_tipo(user_id, "gasto")
            if cats:
                c1, c2, c3 = st.columns([2, 1, 1])
                cat_sel = c1.selectbox("Categoria", cats, format_func=lambda x: x.name)
                limite = c2.number_input("Limite (R$)", min_value=50.0, step=50.0)
                
                if c3.button("Salvar Meta", type="primary", use_container_width=True):
                    srv_budget.definir_orcamento(user_id, cat_sel.id, limite)
                    st.toast("Meta definida!")
                    st.rerun()
            else:
                st.info("Cadastre categorias de gasto primeiro.")

        st.divider()

        # Dados
        orcamentos = srv_budget.listar(user_id)
        if not orcamentos:
            st.info("🎯 Nenhuma meta definida para este mês.")
            return

        df = srv_trans.df_usuario(user_id)
        if not df.empty:
            df["payment_date"] = pd.to_datetime(df["payment_date"])
            df = df[
                (df["payment_date"].dt.year == ano) &
                (df["payment_date"].dt.month == mes) &
                (df["type"] == "gasto")
            ]

        st.subheader(f"📊 Acompanhamento ({mes}/{ano})")
        
        # Grid de Metas
        cols = st.columns(3)
        for i, o in enumerate(sorted(orcamentos, key=lambda x: x.category.name)):
            with cols[i % 3]:
                # Cálculo
                gasto = df[df["category"] == o.category.name]["amount"].sum() if not df.empty else 0.0
                restante = o.limit_amount - gasto
                pct = min(gasto / o.limit_amount, 1.0)
                
                # Container Visual
                with st.container(border=True):
                    st.markdown(f"**{o.category.name}**")
                    
                    # Barra de progresso customizada (cor baseada na % via CSS ou lógica simples)
                    st.progress(pct)
                    
                    c_a, c_b = st.columns(2)
                    c_a.caption(f"Gasto: R$ {gasto:.2f}")
                    c_b.caption(f"Meta: R$ {o.limit_amount:.2f}")
                    
                    if restante < 0:
                        st.error(f"Estourou: R$ {abs(restante):.2f}")
                    else:
                        st.success(f"Restam: R$ {restante:.2f}")

if __name__ == "__main__":
    main()