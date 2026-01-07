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
        st.info("💡 Para lançamentos e cadastros, acesse **Movimentações** no menu lateral.")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    load_css(modo_escuro)
    text_color = "white" if modo_escuro else "black"
    grid_color = "#333" if modo_escuro else "#ddd"

    hora = pd.Timestamp.now().hour
    saudacao = "Bom dia" if 5 <= hora < 12 else "Boa tarde" if 12 <= hora < 18 else "Boa noite"
    st.title(f"{saudacao}, {st.session_state.username}!")

    with get_db() as db:
        srv_trans = TransactionService(db)
        srv_budget = BudgetService(db)
        srv_ml = MLService(db)

        # 1. Carregar Dados
        df = srv_trans.df_usuario(user_id)

        if df.empty:
            st.info("👋 Olá! Você ainda não tem dados. Vá na página **📝 Movimentações** (no menu lateral) para começar.")
            return

        # 2. Filtros de Data
        if "date" in df.columns: df["date"] = pd.to_datetime(df["date"])
        
        with st.container():
            col_date1, col_date2, _ = st.columns([1, 1, 4])
            with col_date1:
                anos = sorted(df["date"].dt.year.unique(), reverse=True)
                ano_sel = st.selectbox("Ano", anos, key="year_sel")
            with col_date2:
                meses_disp = sorted(df[df["date"].dt.year == ano_sel]["date"].dt.month.unique(), reverse=True)
                mes_map = {1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez"}
                if not meses_disp: meses_disp = [date.today().month]
                mes_sel = st.selectbox("Mês", meses_disp, format_func=lambda x: mes_map.get(x, str(x)), key="month_sel")

        df_filtrado = df[(df["date"].dt.year == ano_sel) & (df["date"].dt.month == mes_sel)]

        # 3. KPIs
        receita = df_filtrado[df_filtrado["type"] == "renda"]["amount"].sum()
        gasto = df_filtrado[df_filtrado["type"] == "gasto"]["amount"].sum()
        saldo = receita - gasto

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Receitas", f"R$ {receita:,.2f}")
        c2.metric("Despesas", f"R$ {gasto:,.2f}", delta="-Saídas", delta_color="inverse")
        c3.metric("Saldo", f"R$ {saldo:,.2f}")

        # Projeção ML
        hoje = date.today()
        if (hoje.year == ano_sel) and (hoje.month == mes_sel):
            resultado_ml = srv_ml.calcular_projecao_inteligente(user_id, df_filtrado)
            val = resultado_ml["valor"] if isinstance(resultado_ml, dict) else resultado_ml
            c4.metric("Projeção Fim Mês", f"R$ {val:,.2f}", delta="Estimativa IA", delta_color="off")
        else:
            c4.metric("Status", "Fechado", delta="Finalizado", delta_color="off")

        st.markdown("---")

        # 4. Gráficos
        c_chart1, c_chart2 = st.columns([1, 2])
        
        with c_chart1:
            st.subheader("Por Categoria")
            df_gasto = df_filtrado[df_filtrado["type"] == "gasto"]
            if not df_gasto.empty:
                if len(df_gasto) > 5:
                    fig = px.bar(df_gasto.sort_values("amount"), x="amount", y="category", orientation='h', text="amount", color="category", color_discrete_sequence=px.colors.qualitative.Pastel)
                    fig.update_traces(texttemplate='R$ %{x:.2s}', textposition='auto', showlegend=False)
                else:
                    fig = go.Figure(data=[go.Pie(labels=df_gasto['category'], values=df_gasto['amount'], hole=.6, textinfo='percent', marker=dict(colors=px.colors.qualitative.Pastel))])
                    fig.update_layout(showlegend=True, annotations=[dict(text=f'R$ {gasto:,.0f}', x=0.5, y=0.5, font_size=20, showarrow=False, font_color=text_color)])
                
                fig.update_layout(height=350, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=text_color), xaxis=dict(showgrid=False, showticklabels=False), yaxis=dict(showgrid=False))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem dados.")

        with c_chart2:
            st.subheader("Fluxo Diário")
            df_diario = df_filtrado.groupby([df_filtrado["date"].dt.day, "type"])["amount"].sum().reset_index()
            df_diario.columns = ["Dia", "Tipo", "Valor"]
            if not df_diario.empty:
                fig = px.bar(df_diario, x="Dia", y="Valor", color="Tipo", barmode="group", color_discrete_map={"renda": "#2ecc71", "gasto": "#e74c3c"})
                fig.update_layout(height=350, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color=text_color), xaxis=dict(showgrid=False, color=text_color), yaxis=dict(showgrid=True, gridcolor=grid_color, color=text_color), legend=dict(orientation="h", y=1.1, title=""))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Sem dados.")

        # 5. Radar IA
        st.subheader("🕵️‍♂️ Radar Financeiro (IA)")
        anomalias = srv_ml.detectar_anomalias(df_filtrado)
        if not anomalias.empty:
            for _, row in anomalias.iterrows():
                st.error(f"Atípico: {row['category']} - R$ {row['amount']:,.2f} ({row['date'].strftime('%d/%m')})")
        else:
            if not df_filtrado.empty: st.success("Nenhuma anomalia detectada.", icon="🛡️")

def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if st.session_state.logged_in:
        dashboard_screen()
    else:
        login_screen()

if __name__ == "__main__":
    main()