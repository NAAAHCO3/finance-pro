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
        st.warning("🔒 Acesso restrito. Faça login na página inicial.")
        st.stop()

    user_id = st.session_state.user_id
    st.title("📝 Controle de Lançamentos")
    
    # CORREÇÃO: Variável 'tab_config' nomeada corretamente para evitar NameError
    tab_new, tab_manager, tab_config = st.tabs(["➕ Novo Lançamento", "✏️ Extrato e Edição", "⚙️ Gerenciar Cadastros"])

    with get_db() as db:
        srv_trans = TransactionService(db)
        srv_acc = AccountService(db)
        srv_cat = CategoryService(db)

        contas = srv_acc.listar(user_id)
        cats_all = srv_cat.listar_todos(user_id)
        
        cats_renda = [c for c in cats_all if c.type == 'renda']
        cats_gasto = [c for c in cats_all if c.type == 'gasto']

        # ==================================================
        # ABA 1: NOVO LANÇAMENTO
        # ==================================================
        with tab_new:
            if not contas or not cats_all:
                st.warning("⚠️ Cadastre CONTA e CATEGORIAS na aba 'Gerenciar Cadastros' primeiro.")
            else:
                st.markdown("#### Registrar Movimentação")
                c_tipo, c_valor, c_opts = st.columns([1, 1, 2])
                with c_tipo:
                    tipo_ui = st.radio("Tipo:", ["Despesa 🔻", "Receita 💚"], horizontal=True)
                    tipo_db = "gasto" if "Despesa" in tipo_ui else "renda"
                
                with c_valor:
                    valor = st.number_input("Valor (R$)", min_value=0.01, step=10.0, format="%.2f")

                with c_opts:
                    st.write("Opções:")
                    c_chk1, c_chk2 = st.columns(2)
                    pago_agora = c_chk1.checkbox("Pago/Recebido Hoje", value=True)
                    is_parcelado = False
                    if tipo_db == "gasto":
                        is_parcelado = c_chk2.checkbox("Parcelar?", value=False)

                parcelas = 1
                if is_parcelado and tipo_db == "gasto":
                    c_parc1, c_parc2 = st.columns([1, 3])
                    parcelas = c_parc1.number_input("Nº Parcelas", 2, 60, 2)
                    if valor > 0:
                        c_parc2.info(f"💳 {parcelas}x de R$ {valor/parcelas:,.2f}")

                st.divider()

                with st.form("form_transacao", clear_on_submit=True):
                    c1, c2, c3 = st.columns(3)
                    dt_compra = c1.date_input("Data da Compra", value=date.today())
                    lista_cats = cats_gasto if tipo_db == "gasto" else cats_renda
                    
                    if lista_cats:
                        cat_sel = c2.selectbox("Categoria", lista_cats, format_func=lambda x: x.name)
                    else:
                        c2.warning("Sem categorias.")
                        cat_sel = None

                    acc_sel = c3.selectbox("Conta", contas, format_func=lambda x: x.name) if contas else None
                    
                    dt_pagamento = dt_compra 
                    if not pago_agora:
                        dt_pagamento = st.date_input("Data do Vencimento", value=date.today())
                    
                    descricao = st.text_input("Descrição", placeholder="Ex: Mercado...")

                    if st.form_submit_button("✅ Salvar", use_container_width=True, type="primary"):
                        if cat_sel and acc_sel:
                            try:
                                srv_trans.registrar(user_id, tipo_db, valor, cat_sel.id, acc_sel.id, descricao, dt_compra, dt_pagamento, int(parcelas))
                                st.toast("Salvo!", icon="✅")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e: st.error(f"Erro: {e}")
                        else:
                            st.error("Preencha todos os campos.")

        # ==================================================
        # ABA 2: EXTRATO E EDIÇÃO
        # ==================================================
        with tab_manager:
            df = srv_trans.df_usuario(user_id)
            
            if df.empty:
                st.info("Nenhum lançamento encontrado.")
            else:
                col_sel, col_edit = st.columns([1, 2])
                with col_sel:
                    st.markdown("##### Selecionar para Editar:")
                    opcoes = df.apply(lambda x: f"ID {x['id']} | {x['description']} | R$ {x['amount']:.2f}", axis=1).tolist()
                    escolha = st.selectbox("Buscar:", options=opcoes)
                    id_escolhido = int(escolha.split(" |")[0].replace("ID ", ""))
                    linha_atual = df[df["id"] == id_escolhido].iloc[0]

                with col_edit:
                    with st.container(border=True):
                        st.markdown(f"**Editando ID {id_escolhido}**")
                        with st.form("form_editar"):
                            ce1, ce2 = st.columns(2)
                            n_desc = ce1.text_input("Descrição", value=linha_atual["description"])
                            n_val = ce2.number_input("Valor", value=float(linha_atual["amount"]), min_value=0.01)
                            
                            ce3, ce4, ce5 = st.columns(3)
                            n_dt = ce3.date_input("Vencimento", value=pd.to_datetime(linha_atual["payment_date"]).date())
                            
                            # Recupera índices
                            try:
                                idx_cat = next(i for i, c in enumerate(cats_all) if c.id == linha_atual["category_id"])
                            except StopIteration: idx_cat = 0
                            
                            try:
                                idx_acc = next(i for i, a in enumerate(contas) if a.id == linha_atual["account_id"])
                            except StopIteration: idx_acc = 0

                            n_cat = ce4.selectbox("Categoria", cats_all, format_func=lambda x: x.name, index=idx_cat)
                            n_acc = ce5.selectbox("Conta", contas, format_func=lambda x: x.name, index=idx_acc)
                            
                            st.write("")
                            c_btn_save, c_btn_del = st.columns(2)
                            
                            if c_btn_save.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True):
                                if srv_trans.atualizar(user_id, id_escolhido, n_val, n_desc, n_dt, n_cat.id, n_acc.id):
                                    st.toast("Atualizado!", icon="🔄")
                                    time.sleep(0.5)
                                    st.rerun()
                            
                            if c_btn_del.form_submit_button("🗑️ Excluir", type="secondary", use_container_width=True):
                                if srv_trans.deletar(user_id, id_escolhido):
                                    st.success("Apagado.")
                                    time.sleep(0.5)
                                    st.rerun()

                st.divider()
                st.dataframe(df[["id", "payment_date", "description", "category", "amount", "type"]], use_container_width=True, hide_index=True)

        # ==================================================
        # ABA 3: CONFIGURAÇÕES E RESET
        # ==================================================
        with tab_config:
            # 1. Cadastros
            c_acc, c_cat = st.columns(2)
            with c_acc:
                with st.container(border=True):
                    st.write("**Nova Conta**")
                    with st.form("new_acc"):
                        n = st.text_input("Nome")
                        if st.form_submit_button("Criar"):
                            try: srv_acc.criar(user_id, n); st.rerun()
                            except: st.error("Erro")
            
            with c_cat:
                with st.container(border=True):
                    st.write("**Nova Categoria**")
                    with st.form("new_cat"):
                        n = st.text_input("Nome")
                        t = st.radio("Tipo", ["gasto", "renda"], horizontal=True)
                        if st.form_submit_button("Criar"):
                            try: srv_cat.adicionar(user_id, n, t); st.rerun()
                            except: st.error("Erro")

            st.markdown("---")
            
            # 2. Listagem (Cards)
            df_all = srv_trans.df_usuario(user_id)
            
            def render_card(item_id, nome, tipo_item, service_obj, icon):
                if tipo_item == "Conta":
                    uso = len(df_all[df_all['account_name'] == nome]) if not df_all.empty else 0
                else:
                    uso = len(df_all[df_all['category'] == nome]) if not df_all.empty else 0
                
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.write(f"**{icon} {nome}** ({uso} usos)")
                    # Só permite excluir se não tiver uso
                    if c2.button("🗑️", key=f"del_{tipo_item}_{item_id}", disabled=(uso > 0)):
                        service_obj.deletar(user_id, item_id)
                        st.rerun()

            c1, c2, c3 = st.columns(3)
            with c1: 
                st.caption("Contas")
                for c in contas: render_card(c.id, c.name, "Conta", srv_acc, "💳")
            with c2:
                st.caption("Gastos")
                for c in cats_gasto: render_card(c.id, c.name, "Cat", srv_cat, "🛒")
            with c3:
                st.caption("Receitas")
                for c in cats_renda: render_card(c.id, c.name, "Cat", srv_cat, "💰")

            st.markdown("---")
            
            # 3. ZONA DE PERIGO (RESETAR TUDO)
            with st.expander("🚨 Zona de Perigo"):
                st.warning("Isso apagará TODOS os seus lançamentos. Contas e Categorias serão mantidas.")
                check = st.checkbox("Eu entendo que essa ação é irreversível.")
                
                if st.button("💣 LIMPAR TUDO", type="primary", disabled=not check):
                    # Chama o método que criamos no TransactionService
                    if srv_trans.limpar_todos(user_id):
                        st.success("Todos os lançamentos foram apagados!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Erro ao limpar dados.")

if __name__ == "__main__":
    main()