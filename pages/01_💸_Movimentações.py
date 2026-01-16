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
    
    # Nova estrutura de abas incluindo Edição
    tab_new, tab_manager, tab_settings = st.tabs(["➕ Novo Lançamento", "✏️ Extrato e Edição", "⚙️ Gerenciar Cadastros"])

    with get_db() as db:
        srv_trans = TransactionService(db)
        srv_acc = AccountService(db)
        srv_cat = CategoryService(db)

        # Carregamento de dados
        contas = srv_acc.listar(user_id)
        # Carregamos TODAS as categorias para facilitar a edição (lookup por ID)
        cats_all = srv_cat.listar_todos(user_id)
        
        # Filtros para o formulário de cadastro
        cats_renda = [c for c in cats_all if c.type == 'renda']
        cats_gasto = [c for c in cats_all if c.type == 'gasto']

        # ==================================================
        # ABA 1: NOVO LANÇAMENTO (CORRIGIDO)
        # ==================================================
        with tab_new:
            if not contas:
                st.warning("⚠️ Cadastre pelo menos uma CONTA na aba 'Gerenciar Cadastros'.")
            elif not cats_all:
                st.warning("⚠️ Cadastre CATEGORIAS na aba 'Gerenciar Cadastros'.")
            else:
                st.markdown("#### Registrar Movimentação")
                
                # Seleção de Tipo e Valor
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

                # Opções de Parcelamento
                parcelas = 1
                if is_parcelado and tipo_db == "gasto":
                    c_parc1, c_parc2 = st.columns([1, 3])
                    parcelas = c_parc1.number_input("Nº Parcelas", 2, 60, 2)
                    if valor > 0:
                        c_parc2.info(f"💳 **{parcelas}x** de **R$ {valor/parcelas:,.2f}**")

                st.divider()

                # Formulário Principal
                with st.form("form_transacao", clear_on_submit=True):
                    c1, c2, c3 = st.columns(3)
                    dt_compra = c1.date_input("Data da Compra", value=date.today())
                    
                    # Filtra categorias pelo tipo selecionado
                    lista_cats = cats_gasto if tipo_db == "gasto" else cats_renda
                    
                    if lista_cats:
                        # O format_func exibe o nome, mas o objeto 'cat_sel' terá o ID
                        cat_sel = c2.selectbox("Categoria", lista_cats, format_func=lambda x: x.name)
                    else:
                        c2.warning("Sem categorias deste tipo.")
                        cat_sel = None

                    acc_sel = c3.selectbox("Conta", contas, format_func=lambda x: x.name) if contas else None
                    
                    dt_pagamento = dt_compra 
                    if not pago_agora:
                        dt_pagamento = st.date_input("Data do Vencimento", value=date.today())
                    
                    descricao = st.text_input("Descrição", placeholder="Ex: Mercado, Salário...")

                    if st.form_submit_button("✅ Salvar Lançamento", use_container_width=True, type="primary"):
                        if cat_sel and acc_sel:
                            try:
                                # CORREÇÃO IMPORTANTE: Passando IDs explicitamente
                                srv_trans.registrar(
                                    user_id=user_id,
                                    tipo=tipo_db,
                                    valor_total=valor,
                                    category_id=cat_sel.id,
                                    account_id=acc_sel.id,
                                    descricao=descricao,
                                    data_compra=dt_compra,
                                    data_pagamento=dt_pagamento,
                                    parcelas=int(parcelas)
                                )
                                st.toast("Lançamento salvo com sucesso!", icon="✅")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao salvar: {e}")
                        else:
                            st.error("Preencha todos os campos obrigatórios.")

        # ==================================================
        # ABA 2: EXTRATO E EDIÇÃO (NOVA FUNCIONALIDADE)
        # ==================================================
        with tab_manager:
            df = srv_trans.df_usuario(user_id)
            
            if df.empty:
                st.info("Nenhum lançamento encontrado.")
            else:
                st.subheader("📋 Gestão de Lançamentos")
                
                # Layout: Coluna de Seleção (Esq) e Coluna de Edição (Dir)
                col_sel, col_edit = st.columns([1, 2])
                
                with col_sel:
                    st.markdown("##### Selecione para Editar:")
                    # Cria lista formatada para o selectbox
                    opcoes = df.apply(lambda x: f"ID {x['id']} | {x['description']} | R$ {x['amount']:.2f}", axis=1).tolist()
                    escolha = st.selectbox("Buscar Lançamento:", options=opcoes)
                    
                    # Extrai o ID da string selecionada "ID 123 | Desc..."
                    id_escolhido = int(escolha.split(" |")[0].replace("ID ", ""))
                    
                    # Filtra o dataframe para pegar os dados originais
                    linha_atual = df[df["id"] == id_escolhido].iloc[0]

                with col_edit:
                    with st.container(border=True):
                        st.markdown(f"**Editando ID: {id_escolhido}**")
                        
                        with st.form("form_editar"):
                            ce1, ce2 = st.columns(2)
                            novo_desc = ce1.text_input("Descrição", value=linha_atual["description"])
                            novo_valor = ce2.number_input("Valor (R$)", value=float(linha_atual["amount"]), min_value=0.01)
                            
                            ce3, ce4, ce5 = st.columns(3)
                            # Converte string de data para objeto date se necessário
                            data_atual_pg = pd.to_datetime(linha_atual["payment_date"]).date()
                            nova_dt = ce3.date_input("Vencimento", value=data_atual_pg)
                            
                            # Lógica para encontrar o índice correto no selectbox
                            # Se a categoria foi deletada, volta para índice 0
                            try:
                                idx_cat = next(i for i, c in enumerate(cats_all) if c.id == linha_atual["category_id"])
                            except StopIteration:
                                idx_cat = 0
                            
                            try:
                                idx_acc = next(i for i, a in enumerate(contas) if a.id == linha_atual["account_id"])
                            except StopIteration:
                                idx_acc = 0

                            nova_cat = ce4.selectbox("Categoria", cats_all, format_func=lambda x: x.name, index=idx_cat)
                            nova_acc = ce5.selectbox("Conta", contas, format_func=lambda x: x.name, index=idx_acc)
                            
                            st.write("")
                            c_btn_save, c_btn_del = st.columns(2)
                            
                            submit_save = c_btn_save.form_submit_button("💾 Salvar Alterações", type="primary", use_container_width=True)
                            submit_del = c_btn_del.form_submit_button("🗑️ Excluir Definitivamente", type="secondary", use_container_width=True)

                            if submit_save:
                                if srv_trans.atualizar(
                                    user_id, id_escolhido, novo_valor, novo_desc, nova_dt, nova_cat.id, nova_acc.id
                                ):
                                    st.toast("Lançamento atualizado!", icon="🔄")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error("Erro ao atualizar.")
                            
                            if submit_del:
                                if srv_trans.deletar(user_id, id_escolhido):
                                    st.success("Lançamento excluído com sucesso.")
                                    time.sleep(0.5)
                                    st.rerun()
                                else:
                                    st.error("Erro ao excluir.")

                st.divider()
                st.markdown("##### Histórico Completo")
                # Tabela de visualização rápida
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
        # ABA 3: GERENCIAR CADASTROS (CARDS)
        # ==================================================
        with tab_config:
            # Carrega DF completo para contar usos
            df_all = srv_trans.df_usuario(user_id)

            st.markdown("### 🛠️ Gerenciar Cadastros")
            st.caption("Crie, renomeie ou exclua suas contas e categorias.")

            # --- ÁREA DE CRIAÇÃO ---
            with st.expander("➕ Cadastrar Novo Item", expanded=False):
                cc1, cc2 = st.columns(2)
                
                # Criar Conta
                with cc1:
                    with st.form("new_acc"):
                        n_acc = st.text_input("Nova Conta", placeholder="Ex: Nubank")
                        if st.form_submit_button("Criar Conta"):
                            try:
                                srv_acc.criar(user_id, n_acc)
                                st.toast("Conta criada!", icon="🏦")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e: st.error(str(e))
                
                # Criar Categoria
                with cc2:
                    with st.form("new_cat"):
                        n_cat = st.text_input("Nova Categoria", placeholder="Ex: Viagem")
                        t_cat = st.radio("Tipo", ["gasto", "renda"], horizontal=True)
                        if st.form_submit_button("Criar Categoria"):
                            try:
                                srv_cat.adicionar(user_id, n_cat, t_cat)
                                st.toast("Categoria criada!", icon="🏷️")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e: st.error(str(e))

            st.divider()

            # --- HELPER PARA RENDERIZAR CARDS ---
            def render_card(item_id, nome, tipo_item, service_obj, icon):
                # Verifica uso para impedir exclusão se necessário
                if tipo_item == "Conta":
                    uso = len(df_all[df_all['account_name'] == nome]) if not df_all.empty else 0
                else:
                    uso = len(df_all[df_all['category'] == nome]) if not df_all.empty else 0
                
                with st.container(border=True):
                    c_info, c_act = st.columns([3, 2])
                    
                    with c_info:
                        st.markdown(f"**{icon} {nome}**")
                        if uso > 0:
                            st.caption(f"🔗 {uso} lançamentos")
                        else:
                            st.caption("✨ Sem uso")

                    with c_act:
                        # Botão EDITAR (Renomear)
                        with st.popover("✏️", help="Renomear"):
                            new_name = st.text_input("Novo nome", value=nome, key=f"ed_{tipo_item}_{item_id}")
                            if st.button("Salvar", key=f"sv_{tipo_item}_{item_id}"):
                                if service_obj.atualizar(user_id, item_id, new_name):
                                    st.rerun()
                        
                        # Botão EXCLUIR
                        btn_del = st.button("🗑️", key=f"del_{tipo_item}_{item_id}", 
                                          help="Item em uso não pode ser excluído" if uso > 0 else "Excluir")
                        
                        if btn_del:
                            ok, msg = service_obj.deletar(user_id, item_id)
                            if ok:
                                st.toast(msg, icon="🗑️")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error(msg)

            # --- RENDERIZAÇÃO DAS LISTAS ---
            col_a, col_g, col_r = st.columns(3)

            with col_a:
                st.markdown("##### 🏦 Contas")
                if contas:
                    for c in contas: render_card(c.id, c.name, "Conta", srv_acc, "💳")
                else: st.info("Vazio")

            with col_g:
                st.markdown("##### 🔴 Gastos")
                if cats_gasto:
                    for c in cats_gasto: render_card(c.id, c.name, "CatGasto", srv_cat, "🛒")
                else: st.info("Vazio")

            with col_r:
                st.markdown("##### 🟢 Receitas")
                if cats_renda:
                    for c in cats_renda: render_card(c.id, c.name, "CatRenda", srv_cat, "💰")
                else: st.info("Vazio")

if __name__ == "__main__":
    main()