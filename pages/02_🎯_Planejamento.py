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
        st.warning("🔒 Login necessário.")
        st.stop()

    user_id = st.session_state.user_id
    st.title("🎯 Planejamento Mensal")

    with get_db() as db:
        srv_budget = BudgetService(db)
        srv_cat = CategoryService(db)
        srv_trans = TransactionService(db)

        # 1. FILTRO DE DATA (NOVO)
        st.sidebar.header("📅 Filtro")
        hoje = date.today()
        # Cria lista de meses para seleção (ex: últimos 12 meses + próximos 12)
        # Simplificação: Seleção de Ano e Mês
        col_y, col_m = st.sidebar.columns(2)
        ano_sel = col_y.number_input("Ano", min_value=2020, max_value=2030, value=hoje.year)
        mes_sel = col_m.selectbox("Mês", range(1, 13), index=hoje.month-1)

        # 2. DEFINIR METAS (Topo)
        with st.expander("🛠️ Definir/Alterar Metas", expanded=False):
            cats = srv_cat.listar_por_tipo(user_id, "gasto")
            if not cats:
                st.warning("Cadastre categorias de gasto primeiro.")
            else:
                with st.form("meta_form"):
                    c_cat, c_val = st.columns([2, 1])
                    cat_obj = c_cat.selectbox("Categoria", cats, format_func=lambda x: x.name)
                    val_obj = c_val.number_input("Limite (R$)", min_value=1.0, step=50.0)
                    if st.form_submit_button("Salvar Meta"):
                        srv_budget.definir_orcamento(user_id, cat_obj.id, val_obj)
                        st.toast("Meta salva!")
                        st.rerun()

        # 3. VISUALIZAÇÃO
        st.divider()
        st.subheader(f"Progresso em {mes_sel}/{ano_sel}")

        orcamentos = srv_budget.listar(user_id)
        if not orcamentos:
            st.info("Nenhuma meta definida.")
            return

        # Pega transações e FILTRA pelo mês selecionado
        df = srv_trans.df_usuario(user_id)
        
        # Filtro de Data usando a nova coluna payment_date (Caixa) ou date (Competência)
        # Geralmente orçamento é Caixa (quando eu pago).
        if not df.empty:
            df["payment_date"] = pd.to_datetime(df["payment_date"])
            mask = (df["payment_date"].dt.year == ano_sel) & (df["payment_date"].dt.month == mes_sel)
            df_filtrado = df[mask]
        else:
            df_filtrado = pd.DataFrame(columns=["category", "amount", "type"])

        orcamentos.sort(key=lambda x: x.category.name)

        # Grid de cards
        for orc in orcamentos:
            nome_cat = orc.category.name
            limite = orc.limit_amount
            
            # Soma gastos APENAS do mês filtrado
            gasto_atual = 0.0
            if not df_filtrado.empty:
                gasto_atual = df_filtrado[
                    (df_filtrado["category"] == nome_cat) & 
                    (df_filtrado["type"] == "gasto")
                ]["amount"].sum()

            percentual = min(gasto_atual / limite, 1.0) if limite > 0 else 0
            
            # Cores
            cor = "green"
            if percentual > 0.75: cor = "orange"
            if percentual >= 1.0: cor = "red"

            with st.container():
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{nome_cat}**")
                c1.progress(percentual)
                c2.write(f"**{gasto_atual:.0f}** / {limite:.0f}")
                
                if percentual >= 1.0:
                    st.caption(f":red[Estourou R$ {gasto_atual - limite:.2f}]")
                else:
                    st.caption(f"Resta: R$ {limite - gasto_atual:.2f}")

if __name__ == "__main__":
    main()