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
    st.title("📝 Controle Financeiro")
    
    # ESTRUTURA PROFISSIONAL: Abas separadas por contexto
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

        # Carregamento de dados
        contas = srv_acc.listar(user_id)
        cats_all = srv_cat.listar_todos(user_id)
        
        # Filtros de Categorias
        cats_renda = [c for c in cats_all if c.type == 'renda']
        cats_gasto = [c for c in cats_all if c.type == 'gasto']

        # Verificar pré-requisitos
        if not contas:
            st.error("⚠️ Você precisa cadastrar pelo menos uma CONTA na aba 'Cadastros'.")
            st.stop()

        # ==================================================
        # ABA 1: NOVA DESPESA (Focado em Gastos)
        # ==================================================
        with tab_despesa:
            if not cats_gasto:
                st.warning("⚠️ Cadastre categorias de GASTO na aba 'Cadastros'.")
            else:
                with st.container(border=True):
                    st.markdown("### 💸 Registrar Saída")
                    
                    with st.form("form_despesa", clear_on_submit=True):
                        # Linha 1: Valores e Detalhes Básicos
                        c1, c2 = st.columns([1, 2])
                        valor = c1.number_input("Valor da Despesa (R$)", min_value=0.01, step=10.0, format="%.2f", key="val_gasto")
                        desc = c2.text_input("Descrição", placeholder="Ex: Supermercado, Aluguel...", key="desc_gasto")

                        # Linha 2: Datas e Contas
                        c3, c4, c5 = st.columns(3)
                        dt_compra = c3.date_input("Data da Compra", value=date.today(), key="dt_c_gasto")
                        
                        # Selectbox com KEY única para evitar conflito
                        cat_sel = c4.selectbox("Categoria", cats_gasto, format_func=lambda x: x.name, key="sel_cat_gasto")
                        acc_sel = c5.selectbox("Conta de Saída", contas, format_func=lambda x: x.name, key="sel_acc_gasto")

                        st.markdown("---")
                        
                        # Linha 3: Pagamento e Parcelamento
                        c6, c7 = st.columns([1, 2])
                        pago_agora = c6.checkbox("Pago Hoje?", value=True, key="chk_pago_gasto")
                        parcelado = c7.checkbox("Parcelar essa compra?", value=False, key="chk_parc_gasto")

                        dt_pagamento = dt_compra
                        parcelas = 1

                        if not pago_agora:
                            dt_pagamento = c6.date_input("Data do Vencimento", value=date.today(), key="dt_venc_gasto")
                        
                        if parcelado:
                            parcelas = c7.number_input("Nº Parcelas", min_value=2, max_value=60, value=2, key="num_parc_gasto")
                            if valor > 0:
                                c7.caption(f"💳 {parcelas}x de R$ {valor/parcelas:,.2f}")

                        # Botão de Envio
                        if st.form_submit_button("🔴 Salvar Despesa", use_container_width=True, type="primary"):
                            try:
                                srv_trans.registrar(
                                    user_id=user_id,
                                    tipo="gasto",
                                    valor_total=valor,
                                    category_id=cat_sel.id, # ID garantido
                                    account_id=acc_sel.id,
                                    descricao=desc,
                                    data_compra=dt_compra,
                                    data_pagamento=dt_pagamento,
                                    parcelas=int(parcelas)
                                )
                                st.toast("Despesa salva com sucesso!", icon="💸")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao salvar: {e}")

        # ==================================================
        # ABA 2: NOVA RECEITA (Simplificado e Profissional)
        # ==================================================
        with tab_receita:
            if not cats_renda:
                st.warning("⚠️ Cadastre categorias de RECEITA na aba 'Cadastros'.")
            else:
                with st.container(border=True):
                    st.markdown("### 💰 Registrar Entrada")
                    
                    with st.form("form_receita", clear_on_submit=True):
                        c1, c2 = st.columns([1, 2])
                        valor_r = c1.number_input("Valor Recebido (R$)", min_value=0.01, step=100.0, format="%.2f", key="val_renda")
                        desc_r = c2.text_input("Descrição", placeholder="Ex: Salário, Freelance...", key="desc_renda")

                        c3, c4, c5 = st.columns(3)
                        # Label correta para receita
                        dt_rec = c3.date_input("Data do Recebimento", value=date.today(), key="dt_renda")
                        
                        cat_r_sel = c4.selectbox("Categoria", cats_renda, format_func=lambda x: x.name, key="sel_cat_renda")
                        acc_r_sel = c5.selectbox("Conta de Entrada", contas, format_func=lambda x: x.name, key="sel_acc_renda")

                        if st.form_submit_button("🟢 Salvar Receita", use_container_width=True, type="primary"):
                            try:
                                srv_trans.registrar(
                                    user_id=user_id,
                                    tipo="renda",
                                    valor_total=valor_r,
                                    category_id=cat_r_sel.id,
                                    account_id=acc_r_sel.id,
                                    descricao=desc_r,
                                    data_compra=dt_rec,    # Data de competência
                                    data_pagamento=dt_rec, # Data de caixa (mesma para receita simples)
                                    parcelas=1
                                )
                                st.toast("Receita salva com sucesso!", icon="💰")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao salvar: {e}")

        # ==================================================
        # ABA 3: EXTRATO E EDIÇÃO
        # ==================================================
        with tab_extrato:
            df = srv_trans.df_usuario(user_id)
            
            if df.empty:
                st.info("Nenhum lançamento registrado.")
            else:
                st.subheader("📋 Gestão de Lançamentos")
                
                col_sel, col_edit = st.columns([1, 2])
                
                with col_sel:
                    st.markdown("##### Buscar:")
                    # Lista inteligente com Ícone indicando tipo
                    opcoes = df.apply(lambda x: f"{'🔴' if x['type']=='gasto' else '🟢'} ID {x['id']} | {x['description']} | {x['amount']:.2f}", axis=1).tolist()
                    escolha = st.selectbox("Selecione o item:", options=opcoes)
                    
                    # Extração segura do ID
                    try:
                        id_escolhido = int(escolha.split("ID ")[1].split(" |")[0])
                        linha_atual = df[df["id"] == id_escolhido].iloc[0]
                    except:
                        st.stop()

                with col_edit:
                    with st.container(border=True):
                        st.markdown(f"**Editando ID {id_escolhido}**")
                        with st.form("form_editar"):
                            ce1, ce2 = st.columns(2)
                            n_desc = ce1.text_input("Descrição", value=linha_atual["description"])
                            n_val = ce2.number_input("Valor", value=float(linha_atual["amount"]), min_value=0.01)
                            
                            ce3, ce4, ce5 = st.columns(3)
                            n_dt = ce3.date_input("Data Efetiva", value=pd.to_datetime(linha_atual["payment_date"]).date())
                            
                            # Recuperação inteligente dos índices (previne erro se categoria foi deletada)
                            try:
                                idx_cat = next(i for i, c in enumerate(cats_all) if c.id == linha_atual["category_id"])
                            except StopIteration: idx_cat = 0
                            
                            try:
                                idx_acc = next(i for i, a in enumerate(contas) if a.id == linha_atual["account_id"])
                            except StopIteration: idx_acc = 0

                            n_cat = ce4.selectbox("Categoria", cats_all, format_func=lambda x: x.name, index=idx_cat)
                            n_acc = ce5.selectbox("Conta", contas, format_func=lambda x: x.name, index=idx_acc)
                            
                            st.write("")
                            c_btn1, c_btn2 = st.columns(2)
                            
                            if c_btn1.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True):
                                if srv_trans.atualizar(user_id, id_escolhido, n_val, n_desc, n_dt, n_cat.id, n_acc.id):
                                    st.toast("Atualizado!", icon="🔄")
                                    time.sleep(0.5)
                                    st.rerun()
                            
                            if c_btn2.form_submit_button("🗑️ Excluir", type="secondary", use_container_width=True):
                                if srv_trans.deletar(user_id, id_escolhido):
                                    st.success("Item apagado.")
                                    time.sleep(0.5)
                                    st.rerun()

                st.divider()
                st.dataframe(
                    df[["id", "payment_date", "description", "category", "amount", "account_name", "type"]],
                    column_config={
                        "id": st.column_config.NumberColumn("ID", width="small"),
                        "payment_date": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                        "amount": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                        "type": "Tipo"
                    },
                    hide_index=True,
                    use_container_width=True
                )

        # ==================================================
        # ABA 4: CONFIGURAÇÕES E RESET
        # ==================================================
        with tab_cadastros:
            st.subheader("🛠️ Gerenciar Contas e Categorias")
            
            # Formulários de Criação
            c_acc, c_cat = st.columns(2)
            with c_acc:
                with st.container(border=True):
                    st.markdown("#### 🏦 Nova Conta")
                    with st.form("new_acc"):
                        n = st.text_input("Nome", placeholder="Ex: Nubank, Carteira...")
                        if st.form_submit_button("Criar"):
                            try: srv_acc.criar(user_id, n); st.rerun()
                            except: st.error("Erro")
            
            with c_cat:
                with st.container(border=True):
                    st.markdown("#### 🏷️ Nova Categoria")
                    with st.form("new_cat"):
                        n = st.text_input("Nome", placeholder="Ex: Mercado, Luz...")
                        t = st.radio("Tipo", ["gasto", "renda"], horizontal=True)
                        if st.form_submit_button("Criar"):
                            try: srv_cat.adicionar(user_id, n, t); st.rerun()
                            except: st.error("Erro")

            st.markdown("---")
            
            # Listagem Visual (Cards)
            df_all = srv_trans.df_usuario(user_id)
            
            def render_card(item_id, nome, tipo_item, service_obj, icon):
                # Conta uso real para bloquear exclusão indevida
                if tipo_item == "Conta":
                    uso = len(df_all[df_all['account_name'] == nome]) if not df_all.empty else 0
                else:
                    uso = len(df_all[df_all['category'] == nome]) if not df_all.empty else 0
                
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    c1.markdown(f"**{icon} {nome}**")
                    if c2.button("🗑️", key=f"del_{tipo_item}_{item_id}", disabled=(uso > 0), help="Excluir (apenas se não houver uso)"):
                        service_obj.deletar(user_id, item_id)
                        st.rerun()

            col_a, col_g, col_r = st.columns(3)
            with col_a: 
                st.caption("Suas Contas")
                for c in contas: render_card(c.id, c.name, "Conta", srv_acc, "💳")
            with col_g:
                st.caption("Categorias de Gasto")
                for c in cats_gasto: render_card(c.id, c.name, "Cat", srv_cat, "🛒")
            with col_r:
                st.caption("Categorias de Receita")
                for c in cats_renda: render_card(c.id, c.name, "Cat", srv_cat, "💰")

            st.markdown("---")
            
            # ZONA DE PERIGO
            with st.expander("🚨 Resetar Dados"):
                st.warning("Atenção: Isso apagará TODOS os lançamentos financeiros, mantendo apenas seus cadastros de contas e categorias.")
                check = st.checkbox("Confirmar exclusão total de lançamentos.")
                
                if st.button("💣 LIMPAR TUDO", type="primary", disabled=not check):
                    if srv_trans.limpar_todos(user_id):
                        st.success("Base de dados limpa!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Erro ao processar.")

if __name__ == "__main__":
    main()