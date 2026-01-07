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
    
    tab_lan, tab_extrato, tab_config = st.tabs([
        "➕ Novo Lançamento", 
        "📄 Extrato Detalhado", 
        "⚙️ Configurações"
    ])

    with get_db() as db:
        srv_trans = TransactionService(db)
        srv_account = AccountService(db)
        srv_cat = CategoryService(db)

        contas = srv_account.listar(user_id)
        cats_renda = srv_cat.listar_por_tipo(user_id, "renda")
        cats_gasto = srv_cat.listar_por_tipo(user_id, "gasto")

        # ==================================================
        # ABA 1: NOVO LANÇAMENTO (UX Reativa)
        # ==================================================
        with tab_lan:
            if not contas:
                st.info("⚠️ Cadastre uma conta na aba 'Configurações' primeiro.")
            elif not (cats_renda or cats_gasto):
                st.info("⚠️ Cadastre categorias na aba 'Configurações' primeiro.")
            else:
                st.markdown("#### Registrar Movimentação")
                
                # --- ZONA REATIVA (FORA DO FORMULÁRIO) ---
                c_tipo, c_valor, c_opts = st.columns([1, 1, 2])
                
                with c_tipo:
                    tipo_ui = st.radio("Tipo:", ["Despesa 🔻", "Receita 💚"], horizontal=True)
                    tipo_db = "gasto" if "Despesa" in tipo_ui else "renda"
                
                with c_valor:
                    valor = st.number_input("Valor Total (R$)", min_value=0.01, step=0.01, format="%.2f")

                with c_opts:
                    st.write("Opções:")
                    c_chk1, c_chk2 = st.columns(2)
                    
                    label_pago = "Pago / Recebido Hoje" if tipo_db == "gasto" else "Recebido Hoje"
                    pago_agora = c_chk1.checkbox(label_pago, value=True)
                    
                    is_parcelado = False
                    if tipo_db == "gasto":
                        is_parcelado = c_chk2.checkbox("Parcelar?", value=False)

                # Parcelamento Reativo
                parcelas = 1
                if is_parcelado and tipo_db == "gasto":
                    c_parc1, c_parc2 = st.columns([1, 3])
                    with c_parc1:
                        parcelas = st.number_input("Nº Parcelas", min_value=2, max_value=60, value=2, step=1)
                    with c_parc2:
                        st.write("") 
                        st.write("") 
                        if valor > 0:
                            valor_parc = valor / parcelas
                            st.info(f"💳 **{parcelas}x** de **R$ {valor_parc:,.2f}**")

                # Definição de Listas
                lista_cats = cats_gasto if tipo_db == "gasto" else cats_renda
                aviso_vazio = "⚠️ Nenhuma categoria cadastrada para este tipo."

                st.divider()

                # --- FORMULÁRIO DE ENVIO ---
                with st.form("form_transacao", clear_on_submit=True):
                    c1, c2, c3 = st.columns(3)
                    
                    with c1:
                        dt_compra = st.date_input("Data da Compra", value=date.today())

                    with c2:
                        if not lista_cats:
                            st.warning(aviso_vazio)
                            categoria = None
                        else:
                            categoria = st.selectbox(
                                "Categoria", 
                                lista_cats, 
                                format_func=lambda x: x.name, 
                                key=f"sel_{tipo_db}"
                            )
                    
                    with c3:
                        conta = st.selectbox("Conta / Carteira", contas, format_func=lambda x: x.name)

                    # Data de Pagamento
                    dt_pagamento = dt_compra 
                    if not pago_agora:
                        dt_pagamento = st.date_input(
                            "Data do Vencimento / Pagamento Real", 
                            value=date.today(),
                            help="Data futura quando o dinheiro sairá da conta"
                        )
                    
                    descricao = st.text_input("Descrição (Opcional)", placeholder="Ex: Mercado, Almoço...")

                    submitted = st.form_submit_button("✅ Salvar Lançamento", use_container_width=True, type="primary")

                    if submitted:
                        if categoria and conta:
                            try:
                                srv_trans.registrar(
                                    user_id=user_id,
                                    tipo=tipo_db,
                                    valor_total=valor,
                                    category_id=categoria.id,
                                    account_id=conta.id,
                                    descricao=descricao,
                                    data_compra=dt_compra,
                                    data_pagamento=dt_pagamento,
                                    parcelas=int(parcelas)
                                )
                                st.toast("Lançamento salvo!", icon="✅")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao salvar: {e}")
                        else:
                            st.error("Preencha todos os campos obrigatórios.")

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
                with st.expander("🗑️ Excluir Lançamento"):
                    col_del, col_btn_del = st.columns([3, 1])
                    del_id = col_del.number_input("ID para excluir", min_value=1, step=1)
                    if col_btn_del.button("Excluir", use_container_width=True):
                        if srv_trans.deletar(user_id, del_id):
                            st.success(f"ID {del_id} removido.")
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
                        "description": "Descrição",
                        "category": "Categoria",
                        "amount": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                        "account_name": "Conta",
                        "installment": st.column_config.TextColumn("Parc.")
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("Nenhum lançamento encontrado.")

        # ==================================================
        # ABA 3: CONFIGURAÇÕES (AGORA COM EDITOR COMPLETO)
        # ==================================================
        with tab_config:
            st.markdown("### 🛠️ Gerenciar Cadastros")
            
            c_conta, c_cat = st.columns(2)
            
            # --- FORMULÁRIO DE CRIAÇÃO ---
            with c_conta:
                st.markdown("#### 🏦 Nova Conta")
                with st.form("add_conta"):
                    nome_conta = st.text_input("Nome", placeholder="Nubank, Carteira...")
                    if st.form_submit_button("Salvar Conta"):
                        if nome_conta:
                            try:
                                srv_account.criar(user_id, nome_conta)
                                st.toast("Conta criada!")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e: st.error(str(e))
            
            with c_cat:
                st.markdown("#### 🏷️ Nova Categoria")
                with st.form("add_cat"):
                    nome_cat = st.text_input("Nome", placeholder="Salário, Mercado...")
                    tipo_cat = st.radio("Tipo", ["gasto", "renda"], horizontal=True)
                    
                    if st.form_submit_button("Salvar Categoria"):
                        if nome_cat:
                            try:
                                srv_cat.adicionar(user_id, nome_cat, tipo_cat)
                                st.toast("Categoria criada!")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e: st.error(str(e))

            st.divider()

            # --- LISTAGEM E EXCLUSÃO (IMPLEMENTADO AQUI) ---
            st.markdown("#### 📋 Itens Cadastrados (Gerenciar)")
            
            col_contas, col_gastos, col_rendas = st.columns(3)
            
            with col_contas:
                st.caption("🏦 Contas")
                if contas:
                    for c in contas:
                        st.text(f"• {c.name}")
                else:
                    st.info("Nenhuma conta.")

            with col_gastos:
                st.caption("🔴 Gastos")
                if cats_gasto:
                    for c in cats_gasto:
                        # Layout em colunas para alinhar texto e botão
                        c_txt, c_btn = st.columns([0.8, 0.2])
                        c_txt.text(f"{c.name}")
                        if c_btn.button("🗑️", key=f"del_g_{c.id}"):
                            srv_cat.deletar(user_id, c.name)
                            st.rerun()
                else:
                    st.info("Nenhuma.")

            with col_rendas:
                st.caption("🟢 Receitas")
                if cats_renda:
                    for c in cats_renda:
                        c_txt, c_btn = st.columns([0.8, 0.2])
                        c_txt.text(f"{c.name}")
                        if c_btn.button("🗑️", key=f"del_r_{c.id}"):
                            srv_cat.deletar(user_id, c.name)
                            st.rerun()
                else:
                    st.info("Nenhuma.")

if __name__ == "__main__":
    main()