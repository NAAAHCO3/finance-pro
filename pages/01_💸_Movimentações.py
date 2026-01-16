import streamlit as st
import pandas as pd
from datetime import date
import time

from src.database import get_db
from src.services.transaction_service import TransactionService
from src.services.account_service import AccountService
from src.services.category_service import CategoryService

# ======================================================
# CONFIG
# ======================================================
st.set_page_config(
    page_title="Gestão Financeira",
    page_icon="📝",
    layout="wide"
)

# ======================================================
# HELPERS
# ======================================================
def require_login():
    if not st.session_state.get("logged_in"):
        st.warning("🔒 Acesso restrito. Faça login.")
        st.stop()

def brl(v):
    return f"R$ {v:,.2f}"

# ======================================================
# APP
# ======================================================
def main():
    require_login()
    user_id = st.session_state.user_id

    st.title("📝 Controle Financeiro")

    tab_desp, tab_rec, tab_ext, tab_cfg = st.tabs([
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
            st.error("⚠️ Cadastre pelo menos uma conta.")
            return

        # ==================================================
        # 🔴 DESPESA (CORRIGIDO)
        # ==================================================
        with tab_desp:
            st.subheader("💸 Registrar Despesa")

            if not cats_gasto:
                st.warning("Cadastre categorias de GASTO.")
                return

            # 👉 CONTROLES DINÂMICOS (FORA DO FORM)
            cflag1, cflag2 = st.columns(2)
            pago = cflag1.checkbox("Pago hoje?", value=True, key="gasto_pago")
            parcelado = cflag2.checkbox("Compra parcelada?", key="gasto_parcelado")

            # 👉 FORMULÁRIO
            with st.form("form_despesa", clear_on_submit=True):
                c1, c2 = st.columns([1, 2])
                valor = c1.number_input("Valor (R$)", min_value=0.01, step=10.0, format="%.2f")
                desc = c2.text_input("Descrição")

                c3, c4, c5 = st.columns(3)
                data_compra = c3.date_input("Data da Compra", value=date.today())
                cat = c4.selectbox("Categoria", cats_gasto, format_func=lambda x: x.name)
                acc = c5.selectbox("Conta", contas, format_func=lambda x: x.name)

                parcelas = 1
                data_pagamento = data_compra

                if not pago:
                    data_pagamento = st.date_input("Data de Vencimento", value=data_compra)

                if parcelado:
                    parcelas = st.number_input(
                        "Número de Parcelas",
                        min_value=2,
                        max_value=60,
                        value=2
                    )
                    if valor > 0:
                        st.caption(f"💳 {parcelas}x de {brl(valor / parcelas)}")

                if st.form_submit_button("🔴 Salvar Despesa", type="primary", use_container_width=True):
                    srv_trans.registrar(
                        user_id=user_id,
                        tipo="gasto",
                        valor_total=valor,
                        category_id=cat.id,
                        account_id=acc.id,
                        descricao=desc,
                        data_compra=data_compra,
                        data_pagamento=data_pagamento,
                        parcelas=int(parcelas)
                    )
                    st.toast("Despesa registrada!", icon="💸")
                    time.sleep(0.4)
                    st.rerun()

        # ==================================================
        # 🟢 RECEITA (sem checkbox → ok)
        # ==================================================
        with tab_rec:
            st.subheader("💰 Registrar Receita")

            if not cats_renda:
                st.warning("Cadastre categorias de RECEITA.")
                return

            with st.form("form_receita", clear_on_submit=True):
                c1, c2 = st.columns([1, 2])
                valor = c1.number_input("Valor (R$)", min_value=0.01, step=100.0, format="%.2f")
                desc = c2.text_input("Descrição")

                c3, c4, c5 = st.columns(3)
                data = c3.date_input("Data do Recebimento", value=date.today())
                cat = c4.selectbox("Categoria", cats_renda, format_func=lambda x: x.name)
                acc = c5.selectbox("Conta", contas, format_func=lambda x: x.name)

                if st.form_submit_button("🟢 Salvar Receita", type="primary", use_container_width=True):
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
                    time.sleep(0.4)
                    st.rerun()

        # ==================================================
        # 📄 EXTRATO
        # ==================================================
        with tab_ext:
            df = srv_trans.df_usuario(user_id)

            if df.empty:
                st.info("Nenhum lançamento.")
                return

            escolha = st.selectbox(
                "Selecione um lançamento",
                df.to_dict("records"),
                format_func=lambda x: f"{'🔴' if x['type']=='gasto' else '🟢'} {x['description']} | {brl(x['amount'])}"
            )

            with st.form("editar"):
                c1, c2 = st.columns(2)
                desc = c1.text_input("Descrição", escolha["description"])
                val = c2.number_input("Valor", min_value=0.01, value=float(escolha["amount"]))

                c3, c4, c5 = st.columns(3)
                data = c3.date_input("Data", pd.to_datetime(escolha["payment_date"]).date())
                cat = c4.selectbox("Categoria", categorias, format_func=lambda x: x.name)
                acc = c5.selectbox("Conta", contas, format_func=lambda x: x.name)

                cb1, cb2 = st.columns(2)

                if cb1.form_submit_button("Salvar", type="primary", use_container_width=True):
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

                if cb2.form_submit_button("Excluir", use_container_width=True):
                    srv_trans.deletar(user_id, escolha["id"])
                    st.success("Excluído.")
                    st.rerun()

            st.divider()
            st.dataframe(df, use_container_width=True)

        # ==================================================
        # ⚙️ CADASTROS
        # ==================================================
        with tab_cfg:
            c1, c2 = st.columns(2)

            with c1:
                with st.form("nova_conta"):
                    nome = st.text_input("Nova Conta")
                    if st.form_submit_button("Criar"):
                        srv_acc.criar(user_id, nome)
                        st.rerun()

            with c2:
                with st.form("nova_categoria"):
                    nome = st.text_input("Nova Categoria")
                    tipo = st.radio("Tipo", ["gasto", "renda"], horizontal=True)
                    if st.form_submit_button("Criar"):
                        srv_cat.adicionar(user_id, nome, tipo)
                        st.rerun()

if __name__ == "__main__":
    main()
