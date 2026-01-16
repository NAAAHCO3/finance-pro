import streamlit as st
import pandas as pd
from datetime import date
import time
from src.database import get_db
from src.services.transaction_service import TransactionService
from src.services.account_service import AccountService
from src.services.category_service import CategoryService

st.set_page_config(page_title="Gestão Financeira", page_icon="📝", layout="wide")

def main():
    if not st.session_state.get("logged_in"):
        st.warning("🔒 Acesso restrito. Faça login.")
        st.stop()

    user_id = st.session_state.user_id
    st.title("📝 Controle Financeiro")
    
    # CSS Customizado para esta página
    st.markdown("""
    <style>
        div[data-testid="stExpander"] {
            background-color: #1E1E2E;
            border-radius: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

    # Abas
    tab_despesa, tab_receita, tab_extrato, tab_cadastros = st.tabs([
        "🔴 Nova Despesa", 
        "🟢 Nova Receita", 
        "📄 Extrato e Edição", 
        "⚙️ Cadastros"
    ])

    with get_db() as db:
        srv_trans = TransactionService(db)
        srv_acc = AccountService(db)
        srv_cat = CategoryService(db)

        contas = srv_acc.listar(user_id)
        cats_all = srv_cat.listar_todos(user_id)
        
        cats_renda = [c for c in cats_all if c.type == 'renda']
        cats_gasto = [c for c in cats_all if c.type == 'gasto']

        if not contas:
            st.error("⚠️ Cadastre pelo menos uma CONTA na aba 'Cadastros'.")
            st.stop()

        # ==================================================
        # 1. NOVA DESPESA (REATIVO: SEM st.form)
        # ==================================================
        with tab_despesa:
            if not cats_gasto:
                st.warning("⚠️ Cadastre categorias de GASTO.")
            else:
                with st.container(border=True):
                    st.subheader("💸 Registrar Saída")
                    
                    # Layout Reativo
                    c1, c2 = st.columns([1, 2])
                    valor = c1.number_input("Valor (R$)", min_value=0.01, step=10.0, format="%.2f", key="v_gasto")
                    desc = c2.text_input("Descrição", placeholder="Ex: Supermercado...", key="d_gasto")

                    c3, c4, c5 = st.columns(3)
                    dt_compra = c3.date_input("Data Compra", value=date.today(), key="dt_gasto")
                    cat_sel = c4.selectbox("Categoria", cats_gasto, format_func=lambda x: x.name, key="cat_gasto")
                    acc_sel = c5.selectbox("Conta", contas, format_func=lambda x: x.name, key="acc_gasto")
                    
                    st.divider()

                    # Opções Reativas (Sem Form)
                    col_opts1, col_opts2 = st.columns(2)
                    pago_agora = col_opts1.checkbox("Pago Hoje?", value=True, key="chk_pago")
                    parcelado = col_opts2.checkbox("Parcelar?", value=False, key="chk_parc")

                    dt_pagamento = dt_compra
                    parcelas = 1

                    # Campos Condicionais (Aparecem instantaneamente)
                    if not pago_agora:
                        dt_pagamento = col_opts1.date_input("Vencimento", value=date.today(), key="dt_venc")
                    
                    if parcelado:
                        parcelas = col_opts2.number_input("Nº Parcelas", 2, 60, 2, key="n_parc")
                        if valor > 0:
                            col_opts2.info(f"💳 {parcelas}x de R$ {valor/parcelas:,.2f}")

                    st.write("")
                    # Botão Enviar
                    if st.button("🔴 Confirmar Despesa", type="primary", use_container_width=True):
                        if not desc:
                            st.error("Descrição obrigatória.")
                        else:
                            try:
                                srv_trans.registrar(
                                    user_id, "gasto", valor, cat_sel.id, acc_sel.id, 
                                    desc, dt_compra, dt_pagamento, int(parcelas)
                                )
                                st.toast("Despesa Salva!", icon="💸")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")

        # ==================================================
        # 2. NOVA RECEITA
        # ==================================================
        with tab_receita:
            if not cats_renda:
                st.warning("⚠️ Cadastre categorias de RECEITA.")
            else:
                with st.container(border=True):
                    st.subheader("💰 Registrar Entrada")
                    
                    c1, c2 = st.columns([1, 2])
                    valor_r = c1.number_input("Valor (R$)", min_value=0.01, step=100.0, format="%.2f", key="v_renda")
                    desc_r = c2.text_input("Descrição", placeholder="Ex: Salário...", key="d_renda")

                    c3, c4, c5 = st.columns(3)
                    dt_rec = c3.date_input("Data Recebimento", value=date.today(), key="dt_renda")
                    cat_r = c4.selectbox("Categoria", cats_renda, format_func=lambda x: x.name, key="cat_renda")
                    acc_r = c5.selectbox("Conta", contas, format_func=lambda x: x.name, key="acc_renda")

                    st.write("")
                    if st.button("🟢 Confirmar Receita", type="primary", use_container_width=True):
                        if not desc_r:
                            st.error("Descrição obrigatória.")
                        else:
                            srv_trans.registrar(
                                user_id, "renda", valor_r, cat_r.id, acc_r.id, 
                                desc_r, dt_rec, dt_rec, 1
                            )
                            st.toast("Receita Salva!", icon="💰")
                            time.sleep(0.5)
                            st.rerun()

        # ==================================================
        # 3. EXTRATO E EDIÇÃO
        # ==================================================
        with tab_extrato:
            df = srv_trans.df_usuario(user_id)
            if df.empty:
                st.info("Sem lançamentos.")
            else:
                st.subheader("📋 Histórico e Edição")
                c_sel, c_edit = st.columns([1, 2])

                with c_sel:
                    # Selectbox formatado
                    opcoes = df.apply(lambda x: f"{'🔴' if x['type']=='gasto' else '🟢'} {x['description']} | R$ {x['amount']:.2f}", axis=1).tolist()
                    escolha = st.selectbox("Selecione para editar:", opcoes)
                    
                    # Recupera ID
                    try:
                        idx_sel = opcoes.index(escolha)
                        linha_atual = df.iloc[idx_sel]
                        id_escolhido = int(linha_atual["id"])
                    except: st.stop()

                with c_edit:
                    with st.container(border=True):
                        st.write(f"**Editando ID: {id_escolhido}**")
                        with st.form("edit_form"):
                            ce1, ce2 = st.columns(2)
                            n_desc = ce1.text_input("Descrição", linha_atual["description"])
                            # CORREÇÃO AQUI: Especificando value=... explicitamente
                            n_val = ce2.number_input("Valor", value=float(linha_atual["amount"]), min_value=0.01)
                            
                            ce3, ce4, ce5 = st.columns(3)
                            n_dt = ce3.date_input("Data", pd.to_datetime(linha_atual["payment_date"]).date())
                            
                            # Índices seguros
                            try: ix_c = next(i for i,c in enumerate(cats_all) if c.id == linha_atual["category_id"])
                            except: ix_c = 0
                            try: ix_a = next(i for i,a in enumerate(contas) if a.id == linha_atual["account_id"])
                            except: ix_a = 0

                            n_cat = ce4.selectbox("Categoria", cats_all, format_func=lambda x:x.name, index=ix_c)
                            n_acc = ce5.selectbox("Conta", contas, format_func=lambda x:x.name, index=ix_a)

                            save = st.form_submit_button("💾 Salvar", type="primary", use_container_width=True)
                            if save:
                                srv_trans.atualizar(user_id, id_escolhido, n_val, n_desc, n_dt, n_cat.id, n_acc.id)
                                st.toast("Atualizado!")
                                st.rerun()

                        if st.button("🗑️ Excluir Item", key="bt_del_item", use_container_width=True):
                            srv_trans.deletar(user_id, id_escolhido)
                            st.success("Excluído.")
                            time.sleep(0.5)
                            st.rerun()

                st.dataframe(df[["payment_date", "description", "category", "amount", "account_name", "type"]], use_container_width=True, hide_index=True)

        # ==================================================
        # 4. CADASTROS
        # ==================================================
        with tab_cadastros:
            st.subheader("🛠️ Cadastros Básicos")
            c1, c2 = st.columns(2)
            with c1:
                with st.container(border=True):
                    st.write("**Nova Conta**")
                    nome_acc = st.text_input("Nome da Conta", key="n_acc_new")
                    if st.button("Criar Conta"):
                        if nome_acc: 
                            srv_acc.criar(user_id, nome_acc)
                            st.rerun()
            with c2:
                with st.container(border=True):
                    st.write("**Nova Categoria**")
                    nome_cat = st.text_input("Nome da Categoria", key="n_cat_new")
                    tipo_cat = st.radio("Tipo", ["gasto", "renda"], horizontal=True, key="t_cat_new")
                    if st.button("Criar Categoria"):
                        if nome_cat:
                            srv_cat.adicionar(user_id, nome_cat, tipo_cat)
                            st.rerun()
            
            st.markdown("---")
            with st.expander("🚨 ZONA DE PERIGO (Limpar Tudo)"):
                st.warning("Isso apaga TODOS os lançamentos. Não afeta cadastros.")
                confirma = st.checkbox("Tenho certeza.")
                if st.button("💣 LIMPAR DADOS", type="primary", disabled=not confirma):
                    srv_trans.limpar_todos(user_id)
                    st.success("Dados limpos.")
                    time.sleep(1)
                    st.rerun()

if __name__ == "__main__":
    main()