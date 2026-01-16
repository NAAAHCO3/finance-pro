import streamlit as st
import pandas as pd
from datetime import date
import time

from src.database import get_db
from src.services.transaction_service import TransactionService
from src.services.account_service import AccountService
from src.services.category_service import CategoryService

# ======================================================
# CONFIGURAÇÃO
# ======================================================
st.set_page_config(page_title="Gestão Financeira", page_icon="💸", layout="wide")

# CSS para melhorar aparência dos containers
st.markdown("""
<style>
    div[data-testid="stExpander"] {
        background-color: #1E1E2E;
        border-radius: 10px;
    }
    div.stButton > button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ======================================================
# FUNÇÕES ÚTEIS
# ======================================================
def limpar_campos(keys_to_clear):
    """Limpa os campos do formulário resetando o session_state"""
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

# ======================================================
# APP
# ======================================================
def main():
    if not st.session_state.get("logged_in"):
        st.warning("🔒 Acesso restrito. Faça login.")
        st.stop()

    user_id = st.session_state.user_id
    st.title("📝 Controle de Movimentações")

    tab_desp, tab_rec, tab_ext, tab_cad = st.tabs([
        "🔴 Nova Despesa", 
        "🟢 Nova Receita", 
        "📄 Extrato e Edição", 
        "⚙️ Cadastros"
    ])

    with get_db() as db:
        srv_trans = TransactionService(db)
        srv_acc = AccountService(db)
        srv_cat = CategoryService(db)

        # Carrega listas
        contas = srv_acc.listar(user_id)
        cats_all = srv_cat.listar_todos(user_id)
        
        cats_renda = [c for c in cats_all if c.type == 'renda']
        cats_gasto = [c for c in cats_all if c.type == 'gasto']

        if not contas:
            st.error("⚠️ Cadastre pelo menos uma CONTA na aba 'Cadastros'.")
            st.stop()

        # ==================================================
        # 1. NOVA DESPESA (SEM FORMULÁRIO - REATIVO)
        # ==================================================
        with tab_desp:
            if not cats_gasto:
                st.warning("⚠️ Cadastre categorias de GASTO.")
            else:
                st.subheader("Registrar Saída")
                with st.container(border=True):
                    # Campos com KEYS para manter o estado e não resetar
                    c1, c2 = st.columns([1, 2])
                    val_g = c1.number_input("Valor (R$)", min_value=0.01, step=10.0, format="%.2f", key="new_desp_val")
                    desc_g = c2.text_input("Descrição", placeholder="Ex: Mercado", key="new_desp_desc")

                    c3, c4, c5 = st.columns(3)
                    dt_compra = c3.date_input("Data Compra", value=date.today(), key="new_desp_dt")
                    cat_g = c4.selectbox("Categoria", cats_gasto, format_func=lambda x: x.name, key="new_desp_cat")
                    acc_g = c5.selectbox("Conta", contas, format_func=lambda x: x.name, key="new_desp_acc")

                    st.divider()

                    # Opções reativas
                    co1, co2 = st.columns(2)
                    pago_agora = co1.checkbox("Pago Hoje?", value=True, key="new_desp_pago")
                    parcelado = co2.checkbox("Parcelar?", value=False, key="new_desp_parc")

                    # Lógica condicional imediata
                    dt_venc = dt_compra
                    qtd_parc = 1

                    if not pago_agora:
                        dt_venc = co1.date_input("Vencimento", value=dt_compra, key="new_desp_venc")
                    
                    if parcelado:
                        qtd_parc = co2.number_input("Nº Parcelas", 2, 60, 2, key="new_desp_qtd")
                        if val_g > 0:
                            co2.info(f"💳 {qtd_parc}x de R$ {val_g/qtd_parc:,.2f}")

                    st.write("")
                    
                    # Botão normal (não é form_submit_button)
                    if st.button("🔴 Salvar Despesa", type="primary"):
                        if not desc_g:
                            st.error("Descrição obrigatória.")
                        else:
                            try:
                                srv_trans.registrar(
                                    user_id, "gasto", val_g, cat_g.id, acc_g.id, 
                                    desc_g, dt_compra, dt_venc, int(qtd_parc)
                                )
                                st.toast("Despesa salva!", icon="💸")
                                
                                # Limpa campos resetando as keys
                                limpar_campos(["new_desp_val", "new_desp_desc", "new_desp_pago", "new_desp_parc"])
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")

        # ==================================================
        # 2. NOVA RECEITA (SEM FORMULÁRIO - REATIVO)
        # ==================================================
        with tab_rec:
            if not cats_renda:
                st.warning("⚠️ Cadastre categorias de RECEITA.")
            else:
                st.subheader("Registrar Entrada")
                with st.container(border=True):
                    # Campos diretos (sem st.form)
                    r1, r2 = st.columns([1, 2])
                    val_r = r1.number_input("Valor (R$)", min_value=0.01, step=100.0, format="%.2f", key="new_rec_val")
                    desc_r = r2.text_input("Descrição", placeholder="Ex: Salário", key="new_rec_desc")

                    r3, r4, r5 = st.columns(3)
                    dt_r = r3.date_input("Data Recebimento", value=date.today(), key="new_rec_dt")
                    cat_r = r4.selectbox("Categoria", cats_renda, format_func=lambda x: x.name, key="new_rec_cat")
                    acc_r = r5.selectbox("Conta", contas, format_func=lambda x: x.name, key="new_rec_acc")

                    st.write("")
                    
                    if st.button("🟢 Salvar Receita", type="primary"):
                        if not desc_r:
                            st.error("Descrição obrigatória.")
                        else:
                            try:
                                srv_trans.registrar(
                                    user_id, "renda", val_r, cat_r.id, acc_r.id, 
                                    desc_r, dt_r, dt_r, 1
                                )
                                st.toast("Receita salva!", icon="💰")
                                
                                # Limpa campos
                                limpar_campos(["new_rec_val", "new_rec_desc"])
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro: {e}")

        # ==================================================
        # 3. EXTRATO E EDIÇÃO (SEM FORMULÁRIO)
        # ==================================================
        with tab_ext:
            df = srv_trans.df_usuario(user_id)
            if df.empty:
                st.info("Sem lançamentos.")
            else:
                c_sel, c_edit = st.columns([1, 2])
                with c_sel:
                    # Selectbox para escolher o item
                    opcoes = df.apply(lambda x: f"{'🔴' if x['type']=='gasto' else '🟢'} {x['description']} | R$ {x['amount']:.2f}", axis=1).tolist()
                    escolha = st.selectbox("Selecione para editar:", opcoes)
                    
                    try:
                        idx_sel = opcoes.index(escolha)
                        row = df.iloc[idx_sel]
                        id_sel = int(row["id"])
                    except: st.stop()

                with c_edit:
                    with st.container(border=True):
                        st.markdown(f"**Editando ID {id_sel}**")
                        
                        # Edição direta (sem st.form)
                        ce1, ce2 = st.columns(2)
                        
                        # Usamos 'value' para pré-popular com os dados do banco
                        # O key é fixo + ID para garantir unicidade se mudar de item
                        k_suffix = f"_{id_sel}"
                        
                        n_desc = ce1.text_input("Descrição", value=row["description"], key=f"ed_desc{k_suffix}")
                        n_val = ce2.number_input("Valor", value=float(row["amount"]), min_value=0.01, key=f"ed_val{k_suffix}")
                        
                        ce3, ce4, ce5 = st.columns(3)
                        n_dt = ce3.date_input("Data", value=pd.to_datetime(row["payment_date"]).date(), key=f"ed_dt{k_suffix}")
                        
                        # Índices para selectbox
                        try: ix_c = next(i for i,c in enumerate(cats_all) if c.id == row["category_id"])
                        except: ix_c = 0
                        try: ix_a = next(i for i,a in enumerate(contas) if a.id == row["account_id"])
                        except: ix_a = 0

                        n_cat = ce4.selectbox("Categoria", cats_all, format_func=lambda x:x.name, index=ix_c, key=f"ed_cat{k_suffix}")
                        n_acc = ce5.selectbox("Conta", contas, format_func=lambda x:x.name, index=ix_a, key=f"ed_acc{k_suffix}")

                        st.write("")
                        col_b1, col_b2 = st.columns(2)
                        
                        if col_b1.button("💾 Salvar Alterações", type="primary", key=f"btn_save{k_suffix}"):
                            srv_trans.atualizar(user_id, id_sel, n_val, n_desc, n_dt, n_cat.id, n_acc.id)
                            st.toast("Atualizado!")
                            time.sleep(0.5)
                            st.rerun()

                        if col_b2.button("🗑️ Excluir Item", key=f"btn_del{k_suffix}"):
                            srv_trans.deletar(user_id, id_sel)
                            st.success("Excluído.")
                            time.sleep(0.5)
                            st.rerun()

                st.divider()
                st.dataframe(df[["payment_date", "description", "category", "amount", "account_name", "type"]], use_container_width=True, hide_index=True)

        # ==================================================
        # 4. CADASTROS (SEM FORMULÁRIO)
        # ==================================================
        with tab_cad:
            st.subheader("Cadastros Básicos")
            c1, c2 = st.columns(2)
            
            with c1:
                with st.container(border=True):
                    st.write("**Nova Conta**")
                    nome_acc = st.text_input("Nome da Conta", key="new_acc_name")
                    if st.button("Criar Conta"):
                        if nome_acc: 
                            srv_acc.criar(user_id, nome_acc)
                            limpar_campos(["new_acc_name"])
                            st.rerun()
            
            with c2:
                with st.container(border=True):
                    st.write("**Nova Categoria**")
                    nome_cat = st.text_input("Nome da Categoria", key="new_cat_name")
                    tipo_cat = st.radio("Tipo", ["gasto", "renda"], horizontal=True, key="new_cat_type")
                    if st.button("Criar Categoria"):
                        if nome_cat:
                            srv_cat.adicionar(user_id, nome_cat, tipo_cat)
                            limpar_campos(["new_cat_name"])
                            st.rerun()
            
            st.divider()
            
            # Listagem e Deleção
            df_all = srv_trans.df_usuario(user_id)
            
            def card_del(item_id, nome, tipo, srv):
                uso = len(df_all[df_all['account_name' if tipo=="Conta" else 'category'] == nome])
                c_a, c_b = st.columns([4, 1])
                c_a.text(f"{nome} ({uso} usos)")
                if c_b.button("🗑️", key=f"del_cad_{tipo}_{item_id}", disabled=(uso>0)):
                    srv.deletar(user_id, item_id)
                    st.rerun()

            co1, co2, co3 = st.columns(3)
            with co1:
                st.caption("Contas")
                for c in contas: card_del(c.id, c.name, "Conta", srv_acc)
            with co2:
                st.caption("Gastos")
                for c in cats_gasto: card_del(c.id, c.name, "Cat", srv_cat)
            with co3:
                st.caption("Receitas")
                for c in cats_renda: card_del(c.id, c.name, "Cat", srv_cat)
            
            st.divider()
            with st.expander("🚨 Zona de Perigo"):
                if st.checkbox("Liberar exclusão total"):
                    if st.button("🔥 APAGAR TODOS OS DADOS", type="primary"):
                        srv_trans.limpar_todos(user_id)
                        st.success("Limpo.")
                        time.sleep(1)
                        st.rerun()

if __name__ == "__main__":
    main()