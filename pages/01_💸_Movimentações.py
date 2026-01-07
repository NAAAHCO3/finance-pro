import streamlit as st
import pandas as pd
from datetime import date
import time
from src.database import get_db
from src.services.transaction_service import TransactionService
from src.services.account_service import AccountService
from src.services.category_service import CategoryService

# Configuração da página
st.set_page_config(page_title="Movimentações", page_icon="📝", layout="wide")

def main():
    if not st.session_state.get("logged_in"):
        st.warning("🔒 Acesso restrito. Faça login na página inicial.")
        st.stop()

    user_id = st.session_state.user_id
    st.title("📝 Movimentações")
    
    tab_lan, tab_extrato, tab_config = st.tabs(["➕ Novo Lançamento", "📄 Extrato", "⚙️ Gerenciar Cadastros"])

    with get_db() as db:
        srv_trans = TransactionService(db)
        srv_account = AccountService(db)
        srv_cat = CategoryService(db)

        # Carrega dados
        contas = srv_account.listar(user_id)
        cats_renda = srv_cat.listar_por_tipo(user_id, "renda")
        cats_gasto = srv_cat.listar_por_tipo(user_id, "gasto")

        # ==================================================
        # ABA 1: NOVO LANÇAMENTO
        # ==================================================
        with tab_lan:
            if not contas:
                st.warning("⚠️ Você precisa cadastrar uma CONTA na aba 'Gerenciar Cadastros' primeiro.")
            elif not (cats_renda or cats_gasto):
                st.warning("⚠️ Você precisa cadastrar CATEGORIAS na aba 'Gerenciar Cadastros' primeiro.")
            else:
                st.markdown("#### Registrar Movimentação")
                
                c_tipo, c_valor, c_opts = st.columns([1, 1, 2])
                
                with c_tipo:
                    tipo_ui = st.radio("Tipo:", ["Despesa 🔻", "Receita 💚"], horizontal=True)
                    tipo_db = "gasto" if "Despesa" in tipo_ui else "renda"
                
                with c_valor:
                    valor = st.number_input("Valor Total (R$)", min_value=0.01, step=10.0, format="%.2f")

                with c_opts:
                    st.write("Opções:")
                    c_chk1, c_chk2 = st.columns(2)
                    pago_agora = c_chk1.checkbox("Pago/Recebido Hoje", value=True)
                    
                    is_parcelado = False
                    if tipo_db == "gasto":
                        is_parcelado = c_chk2.checkbox("Parcelar?", value=False)

                # Parcelamento
                parcelas = 1
                if is_parcelado and tipo_db == "gasto":
                    c_parc1, c_parc2 = st.columns([1, 3])
                    parcelas = c_parc1.number_input("Nº Parcelas", 2, 60, 2)
                    if valor > 0:
                        c_parc2.info(f"💳 **{parcelas}x** de **R$ {valor/parcelas:,.2f}**")

                # Seleção de Categoria e Conta
                lista_cats = cats_gasto if tipo_db == "gasto" else cats_renda
                
                st.divider()

                with st.form("form_transacao", clear_on_submit=True):
                    c1, c2, c3 = st.columns(3)
                    dt_compra = c1.date_input("Data da Compra", value=date.today())
                    
                    if lista_cats:
                        categoria = c2.selectbox("Categoria", lista_cats, format_func=lambda x: x.name)
                    else:
                        c2.warning("Sem categorias deste tipo.")
                        categoria = None

                    conta = c3.selectbox("Conta / Carteira", contas, format_func=lambda x: x.name) if contas else None

                    dt_pagamento = dt_compra 
                    if not pago_agora:
                        dt_pagamento = st.date_input("Data do Vencimento", value=date.today())
                    
                    descricao = st.text_input("Descrição (Opcional)", placeholder="Ex: Mercado, Salário...")

                    if st.form_submit_button("✅ Salvar Lançamento", use_container_width=True, type="primary"):
                        if categoria and conta:
                            try:
                                srv_trans.registrar(
                                    user_id, tipo_db, valor, categoria.id, conta.id, 
                                    descricao, dt_compra, dt_pagamento, parcelas
                                )
                                st.toast("Lançamento salvo!", icon="✅")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")
                        else:
                            st.error("Preencha todos os campos.")

        # ==================================================
        # ABA 2: EXTRATO COMPLETO
        # ==================================================
        with tab_extrato:
            c_head, c_btn = st.columns([4,1])
            c_head.subheader("Histórico Detalhado")
            if c_btn.button("🔄 Atualizar"):
                st.rerun()
                
            df = srv_trans.df_usuario(user_id)
            
            if not df.empty:
                with st.expander("🗑️ Opções de Exclusão"):
                    c_del1, c_del2 = st.columns([3, 1])
                    del_id = c_del1.number_input("ID do Lançamento", min_value=1, step=1)
                    if c_del2.button("Apagar Lançamento", type="secondary"):
                        if srv_trans.deletar(user_id, del_id):
                            st.success(f"Lançamento {del_id} apagado.")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("ID não encontrado.")

                st.dataframe(
                    df,
                    column_order=["id", "payment_date", "description", "category", "amount", "account_name", "installment"],
                    column_config={
                        "id": st.column_config.NumberColumn("ID", width="small"),
                        "payment_date": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"),
                        "amount": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("Nenhum lançamento encontrado.")

        # ==================================================
        # ABA 3: CONFIGURAÇÕES (NOVO EDITOR COMPLETO)
        # ==================================================
        with tab_config:
            # Carrega todas transações para verificar uso (contagem)
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
                                srv_account.criar(user_id, n_acc)
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
                # Verifica uso
                if tipo_item == "Conta":
                    uso = len(df_all[df_all['account_name'] == nome]) if not df_all.empty else 0
                else:
                    uso = len(df_all[df_all['category'] == nome]) if not df_all.empty else 0
                
                # Card Visual
                with st.container(border=True):
                    c_info, c_act = st.columns([3, 2])
                    
                    with c_info:
                        st.markdown(f"**{icon} {nome}**")
                        if uso > 0:
                            st.caption(f"🔗 {uso} usos")
                        else:
                            st.caption("✨ Sem uso")

                    with c_act:
                        # Botão EDITAR (Renomear)
                        with st.popover("✏️", help="Editar nome"):
                            new_name = st.text_input("Novo nome", value=nome, key=f"ed_{tipo_item}_{item_id}")
                            if st.button("Salvar", key=f"sv_{tipo_item}_{item_id}"):
                                if service_obj.atualizar(user_id, item_id, new_name):
                                    st.rerun()
                        
                        # Botão EXCLUIR
                        btn_del = st.button("🗑️", key=f"del_{tipo_item}_{item_id}", 
                                          help="Item em uso não pode ser excluído" if uso > 0 else "Excluir")
                        
                        if btn_del:
                            # Chama o serviço que retorna (Sucesso, Mensagem)
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
                    for c in contas: render_card(c.id, c.name, "Conta", srv_account, "💳")
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