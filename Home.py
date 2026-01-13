import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
import time

from src.database import engine, Base, get_db
from src.auth import create_user, get_user_by_username, verify_password
import src.models

from src.services.transaction_service import TransactionService
from src.services.budget_service import BudgetService
from src.services.ml_service import MLService

# Cria tabelas se não existirem
Base.metadata.create_all(bind=engine)

# ======================================================
# CONFIGURAÇÃO DA PÁGINA
# ======================================================
st.set_page_config(
    page_title="Finance Pro - Dashboard",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

def load_css(dark_mode=True):
    if dark_mode:
        try:
            with open("src/ui/styles.css") as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
        except FileNotFoundError:
            pass

# ======================================================
# TELA DE LOGIN
# ======================================================
def login_screen():
    load_css(True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<h1 style='text-align: center; margin-bottom: 2rem;'>💳 Finance Pro</h1>", unsafe_allow_html=True)
        
        tab_login, tab_reg = st.tabs(["Acessar", "Registrar"])
        
        with tab_login:
            with st.form("login_form"):
                username = st.text_input("Usuário")
                password = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar", use_container_width=True, type="primary"):
                    with get_db() as db:
                        user = get_user_by_username(db, username)
                        if user and verify_password(password, user.password_hash):
                            st.session_state.logged_in = True
                            st.session_state.user_id = user.id
                            st.session_state.username = user.username
                            st.rerun()
                        else:
                            st.error("❌ Credenciais inválidas.")
        
        with tab_reg:
            with st.form("register_form"):
                new_user = st.text_input("Usuário")
                new_pass = st.text_input("Senha", type="password")
                if st.form_submit_button("Criar Conta", use_container_width=True):
                    if new_user and new_pass:
                        with get_db() as db:
                            email_unico = f"{new_user.strip().lower()}@finance.pro"
                            if create_user(db, new_user, email_unico, new_pass):
                                st.success("✅ Conta criada! Faça login.")
                            else:
                                st.error("❌ Esse usuário já existe.")
                    else:
                        st.warning("⚠️ Preencha todos os campos.")

# ======================================================
# DASHBOARD DE ANÁLISE (APENAS LEITURA)
# ======================================================
def dashboard_screen():
    user_id = st.session_state.user_id

    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.caption("Visão Geral")
        modo_escuro = st.toggle("🌙 Modo Escuro", value=True)
        st.markdown("---")
        st.info("💡 Para lançamentos e cadastros, acesse Movimentações no menu lateral.")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    load_css(modo_escuro)
    text_color = "white" if modo_escuro else "black"
    grid_color = "#333" if modo_escuro else "#ddd"

    hora = pd.Timestamp.now().hour
    saudacao = "Bom dia" if 5 <= hora < 12 else "Boa tarde" if 12 <= hora < 17 else "Boa noite"
    st.title(f"{saudacao}, {st.session_state.username}!")

    with get_db() as db:
        srv_trans = TransactionService(db)
        srv_budget = BudgetService(db)
        srv_ml = MLService(db)

        # 1. Carregar Dados
        df = srv_trans.df_usuario(user_id)

        if df.empty:
            st.info("👋 Olá! Você ainda não tem dados. Vá na página 📝 Movimentações (no menu lateral) para começar.")
            return

        # ==============================================================================
        # MUDANÇA CRÍTICA: Filtros agora usam 'payment_date' (Data do Pagamento/Vencimento)
        # Isso garante que parcelas apareçam no mês correto, não no mês da compra.
        # ==============================================================================
        if "payment_date" in df.columns: 
            df["payment_date"] = pd.to_datetime(df["payment_date"])
        
        with st.container():
            col_date1, col_date2, _ = st.columns([1, 1, 4])
            with col_date1:
                anos = sorted(df["payment_date"].dt.year.unique(), reverse=True)
                ano_sel = st.selectbox("Ano (Vencimento)", anos, key="year_sel")
            with col_date2:
                meses_disp = sorted(df[df["payment_date"].dt.year == ano_sel]["payment_date"].dt.month.unique(), reverse=True)
                mes_map = {1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez"}
                if not meses_disp: meses_disp = [date.today().month]
                mes_sel = st.selectbox("Mês", meses_disp, format_func=lambda x: mes_map.get(x, str(x)), key="month_sel")

        # Filtra DataFrame pelo Fluxo de Caixa (Vencimento)
        df_filtrado = df[(df["payment_date"].dt.year == ano_sel) & (df["payment_date"].dt.month == mes_sel)]

        # --- CÁLCULO DAS ESTATÍSTICAS NOVAS ---
        stats = srv_ml.analisar_padrao_gastos(df_filtrado)

        # 3. KPIs
        receita = df_filtrado[df_filtrado["type"] == "renda"]["amount"].sum()
        gasto = df_filtrado[df_filtrado["type"] == "gasto"]["amount"].sum()
        saldo = receita - gasto

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Receitas", f"R$ {receita:,.2f}")
        c2.metric("Despesas", f"R$ {gasto:,.2f}", delta="-Saídas", delta_color="inverse")
        c3.metric("Saldo", f"R$ {saldo:,.2f}")

        # KPI 4: Estatística Real (Substitui Projeção IA)
        media_dia = stats.get("media_diaria", 0.0)
        c4.metric("Média Diária", f"R$ {media_dia:,.2f}", 
                  delta="Gasto Real", delta_color="off", 
                  help="Média gasta apenas nos dias em que você movimentou a conta.")

        st.markdown("---")

        # 4. Gráficos
        c_chart1, c_chart2 = st.columns([1, 2])
        
        with c_chart1:
            st.subheader("Por Categoria")
            df_gasto = df_filtrado[df_filtrado["type"] == "gasto"]
            if not df_gasto.empty:
                # Agrupa e ordena para melhor visualização
                df_view = df_gasto.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=True)
                
                fig = px.bar(df_view, x="amount", y="category", orientation='h', text="amount", 
                             color="category", color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_traces(texttemplate='R$ %{x:.2s}', textposition='auto', showlegend=False)
                fig.update_layout(height=350, margin=dict(t=10, b=10, l=10, r=10), 
                                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", 
                                font=dict(color=text_color), xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showgrid=False))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem dados.")

        with c_chart2:
            st.subheader("Fluxo Diário")
            # Agrupa por Data de Pagamento (Vencimento)
            df_diario = df_filtrado.groupby([df_filtrado["payment_date"].dt.day, "type"])["amount"].sum().reset_index()
            df_diario.columns = ["Dia", "Tipo", "Valor"]
            
            if not df_diario.empty:
                fig = px.bar(df_diario, x="Dia", y="Valor", color="Tipo", barmode="group", 
                             color_discrete_map={"renda": "#2ecc71", "gasto": "#e74c3c"})
                fig.update_layout(height=350, margin=dict(t=10, b=10, l=10, r=10), 
                                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", 
                                font=dict(color=text_color), xaxis=dict(showgrid=False, color=text_color), 
                                yaxis=dict(showgrid=True, gridcolor=grid_color, color=text_color), 
                                legend=dict(orientation="h", y=1.1, title=""))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem dados.")

        # 5. NOVO: Radar Estatístico (Pareto) CURVA ABC
        st.subheader("📊 Raio-X Financeiro")
        
        df_pareto = stats.get("pareto", pd.DataFrame())
        
        if not df_pareto.empty:
            c_abc, c_detalhe = st.columns([2, 1])
            
            with c_abc:
                # Mostra apenas as categorias "A" (80% dos gastos)
                classe_a = df_pareto[df_pareto["class"] == "A (Prioridade Alta)"]
                if not classe_a.empty:
                    pct_a = classe_a["percent"].sum()
                    st.warning(f"🚨 **Atenção:** Estas categorias representam **{pct_a:.1f}%** dos seus gastos totais.")
                    st.dataframe(
                        classe_a[["category", "amount", "percent"]],
                        column_config={
                            "category": "Categoria Principal",
                            "amount": st.column_config.NumberColumn("Valor Gasto", format="R$ %.2f"),
                            "percent": st.column_config.NumberColumn("% do Total", format="%.1f%%"),
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                else:
                    st.info("Seus gastos estão bem distribuídos.")

            with c_detalhe:
                maior = stats.get("maior_gasto", 0)
                dias = stats.get("dias_com_gasto", 0)
                st.info(f"**Maior Gasto Único:**\nR$ {maior:,.2f}")
                st.info(f"**Frequência:**\n{dias} dias ativos neste mês")
        else:
            if not df_filtrado.empty:
                st.success("Tudo certo com seus dados estatísticos.", icon="✅")

def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if st.session_state.logged_in:
        dashboard_screen()
    else:
        login_screen()

if __name__ == "__main__":
    main()