import streamlit as st
import pandas as pd
from datetime import date
import time

from src.database import get_db
from src.services.transaction_service import TransactionService
from src.services.account_service import AccountService
from src.services.category_service import CategoryService

# =============================
# CONFIGURAÇÃO DA PÁGINA
# =============================
st.set_page_config(
    page_title="Gestão Financeira",
    page_icon="📝",
    layout="wide"
)

# =============================
# HELPERS
# =============================
def require_login():
    if not st.session_state.get("logged_in"):
        st.warning("🔒 Acesso restrito. Faça login na página inicial.")
        st.stop()

def currency(val: float) -> str:
    return f"R$ {val:,.2f}"

# =============================
# APP
# =============================
def main():
    require_login()
    user_id = st.session_state.user_id

    st.title("📝 Controle Financeiro")

    tabs = st.tabs([
        "🔴 Nova Despesa",
        "🟢 Nova Receita",
        "📄 Extrato",
        "⚙️ Cadastros"
    ])

    with get_db() as db:
        srv_trans = TransactionService(db)
        srv_acc = AccountService(db)
        srv_cat = CategoryService(db)

        contas = srv_acc.listar(user_id)
        categorias = srv_cat.listar_todos(user_id)

        cats_gasto = [c for c in categorias if c.type == "gasto"]
        cats_renda = [c for c in categorias if c.type == "renda"]

        if not contas:
            st.error("⚠️ Cadastre pelo menos uma conta antes de continuar.")
            return

        # ======================================================
        # ABA 1 — DESPESA
        # ======================================================
        with tabs[0]:
            if not cats_gasto:
                st.warning("Cadastre categorias de GASTO.")
                return

            with st.form("form_despesa", clear_on_submit=True):
                st.subheader("💸 Registrar Despesa")

                c1, c2 = st.columns([1, 2])
                valor = c1.number_input("Valor", min_value=0.01, step=10.0, format="%.2f")
                desc = c2.text_input("Descrição")

                c3, c4, c5 = st.columns(3)
                data = c3.date_input("Data", value=date.today())
                cat = c4.selectbox("Categoria", cats_gasto, format_func=lambda x: x.name)
                acc = c5.selectbox("Conta", contas, format_func=lambda x: x.name)

                c6, c7 = st.columns(2)
                pago = c6.checkbox("Pago hoje?", value=True)
                parcelado = c7.checkbox("Parcelado?")

                venc = data
                parcelas = 1

                if not pago:
                    venc = c6.date_input("Vencimento", value=data)

                if parcelado:
                    parcelas = c7.number_input("Parcelas", min_value=2, max_value=60, value=2)
                    c7.caption(f"{parcelas}x de {currency(valor / parcelas)}")

                if st.form_submit_button("Salvar Despesa", type="primary", use_container_width=True):
                    srv_trans.registrar(
                        user_id=user_id,
                        tipo="gasto",
                        valor_total=valor,
                        category_id=cat.id,
                        account_id=acc.id,
                        descricao=desc,
                        data_compra=data,
                        data_pagamento=venc,
                        parcelas=int(parcelas)
                    )
                    st.toast("Despesa registrada!", icon="💸")
                    time.sleep(0.5)
                    st.rerun()

        # ======================================================
        # ABA 2 — RECEITA
        # ======================================================
        with tabs[1]:
            if not cats_renda:
                st.warning("Cadastre categorias de RECEITA.")
                return

            with st.form("form_receita", clear_on_submit=True):
                st.subheader("💰 Registrar Receita")

                c1, c2 = st.columns([1, 2])
                valor = c1.number_input("Valor", min_value=0.01, step=100.0, format="%.2f")
                desc = c2.text_input("Descrição")

                c3, c4, c5 = st.columns(3)
                data = c3.date_input("Data", value=date.today())
                cat = c4.selectbox("Categoria", cats_renda, format_func=lambda x: x.name)
                acc = c5.selectbox("Conta", contas, format_func=lambda x: x.name)

                if st.form_submit_button("Salvar Receita", type="primary", use_container_width=True):
                    srv_trans.registrar(
                        user_id=user_id,
                        tipo="renda",
                        valor_total=valor,
                        category_id=cat.id,
                        account_id=acc.id,
                        descricao=desc,
                        data_compra=data,
                        data_pagamento=data,
                        parcelas=1
                    )
                    st.toast("Receita registrada!", icon="💰")
                    time.sleep(0.5)
                    st.rerun()

        # ======================================================
        # ABA 3 — EXTRATO / EDIÇÃO
        # ======================================================
        with tabs[2]:
            df = srv_trans.df_usuario(user_id)

            if df.empty:
                st.info("Nenhuma movimentação.")
                return

            st.subheader("📄 Extrato")

            escolha = st.selectbox(
                "Selecione um lançamento",
                df.to_dict("records"),
                format_func=lambda x: f"{'🔴' if x['type']=='gasto' else '🟢'} {x['description']} | {currency(x['amount'])}"
            )

            with st.form("editar"):
                c1, c2 = st.columns(2)
                desc = c1.text_input("Descrição", escolha["description"])
                val = c2.number_input("Valor", min_value=0.01, value=float(escolha["amount"]))

                c3, c4, c5 = st.columns(3)
                data = c3.date_input("Data", pd.to_datetime(escolha["payment_date"]).date())
                cat = c4.selectbox("Categoria", categorias, index=0, format_func=lambda x: x.name)
                acc = c5.selectbox("Conta", contas, index=0, format_func=lambda x: x.name)

                c6, c7 = st.columns(2)

                if c6.form_submit_button("Salvar", type="primary", use_container_width=True):
                    srv_trans.atualizar(
                        user_id,
                        escolha["id"],
                        val,
                        desc,
                        data,
                        cat.id,
                        acc.id
                    )
                    st.toast("Atualizado!", icon="🔄")
                    st.rerun()

                if c7.form_submit_button("Excluir", use_container_width=True):
                    srv_trans.deletar(user_id, escolha["id"])
                    st.success("Excluído.")
                    st.rerun()

            st.divider()
            st.dataframe(df, use_container_width=True)

        # ======================================================
        # ABA 4 — CADASTROS
        # ======================================================
        with tabs[3]:
            st.subheader("⚙️ Cadastros")

            col1, col2 = st.columns(2)

            with col1:
                with st.form("nova_conta"):
                    nome = st.text_input("Nova Conta")
                    if st.form_submit_button("Criar"):
                        srv_acc.criar(user_id, nome)
                        st.rerun()

            with col2:
                with st.form("nova_categoria"):
                    nome = st.text_input("Nova Categoria")
                    tipo = st.radio("Tipo", ["gasto", "renda"], horizontal=True)
                    if st.form_submit_button("Criar"):
                        srv_cat.adicionar(user_id, nome, tipo)
                        st.rerun()


if __name__ == "__main__":
    main()
