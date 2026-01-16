import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date

from src.database import engine, Base, get_db
from src.auth import create_user, get_user_by_username, verify_password
import src.models
from src.services.transaction_service import TransactionService
from src.services.ml_service import MLService

# Cria tabelas se não existirem
Base.metadata.create_all(bind=engine)

# ======================================================
# CONFIGURAÇÃO DA PÁGINA
# ======================================================
st.set_page_config(
    page_title="Finance Pro - Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======================================================
# ESTILO CSS (NEON/DARK - Baseado na imagem)
# ======================================================
def inject_custom_css():
    st.markdown("""
    <style>
        /* Cards de KPI */
        div[data-testid="stMetric"] {
            background-color: #1E1E2E;
            border: 1px solid #2B2D42;
            padding: 15px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            transition: all 0.3s ease;
        }
        div[data-testid="stMetric"]:hover {
            border-color: #00F2FE; /* Cyan Neon */
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0, 242, 254, 0.1);
        }
        div[data-testid="stMetricLabel"] {
            color: #8D99AE !important;
            font-size: 0.9rem;
        }
        div[data-testid="stMetricValue"] {
            color: #EDF2F4 !important;
            font-weight: 700;
        }
        
        /* Ajuste de tabelas e containers */
        div[data-testid="stDataFrame"] {
            background-color: #1E1E2E;
            border-radius: 10px;
            padding: 10px;
        }
        
        /* Títulos */
        h1, h2, h3 {
            color: #EDF2F4;
            font-family: 'Segoe UI', sans-serif;
        }
    </style>
    """, unsafe_allow_html=True)

# ======================================================
# TELA DE LOGIN
# ======================================================
def login_screen():
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
                    with get_db() as db:
                        email = f"{new_user.lower()}@finance.pro"
                        if create_user(db, new_user, email, new_pass):
                            st.success("Conta criada! Faça login.")
                        else:
                            st.error("Usuário já existe.")

# ======================================================
# DASHBOARD
# ======================================================
def dashboard_screen():
    inject_custom_css()
    user_id = st.session_state.user_id

    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.markdown("---")
        st.info("💡 Use o menu lateral para navegar entre **Movimentações** e **Planejamento**.")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.title("📊 Dashboard")
    
    with get_db() as db:
        srv_trans = TransactionService(db)
        srv_stats = MLService(db)

        # 1. Carregar Dados
        df = srv_trans.df_usuario(user_id)

        if df.empty:
            st.info("👋 Olá! Vá em **Movimentações** para registrar seus primeiros gastos.")
            return

        # Filtros de Data
        if "payment_date" in df.columns: 
            df["payment_date"] = pd.to_datetime(df["payment_date"])
        
        with st.container():
            col_date1, col_date2, _ = st.columns([1, 1, 4])
            with col_date1:
                anos = sorted(df["payment_date"].dt.year.unique(), reverse=True)
                ano_sel = st.selectbox("Ano", anos)
            with col_date2:
                meses_disp = sorted(df[df["payment_date"].dt.year == ano_sel]["payment_date"].dt.month.unique(), reverse=True)
                mes_map = {1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez"}
                if not meses_disp: meses_disp = [date.today().month]
                mes_sel = st.selectbox("Mês", meses_disp, format_func=lambda x: mes_map.get(x, str(x)))

        # Dataframes filtrados
        df_mes = df[(df["payment_date"].dt.year == ano_sel) & (df["payment_date"].dt.month == mes_sel)]
        df_ano = df[df["payment_date"].dt.year == ano_sel]

        # KPIs
        receita = df_mes[df_mes["type"] == "renda"]["amount"].sum()
        gasto = df_mes[df_mes["type"] == "gasto"]["amount"].sum()
        saldo = receita - gasto
        
        # Estatísticas (ML Service)
        stats = srv_stats.analisar_padrao_gastos(df_mes)
        media_dia = stats.get("media_diaria", 0.0)

        # Cards
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 Saldo Mensal", f"R$ {saldo:,.2f}")
        c2.metric("📉 Despesas", f"R$ {gasto:,.2f}", delta="-Saídas", delta_color="inverse")
        c3.metric("📈 Receitas", f"R$ {receita:,.2f}")
        c4.metric("📊 Média/Dia", f"R$ {media_dia:,.2f}", help="Média gasta nos dias ativos")

        st.markdown("---")

        # Layout Principal (2 Colunas)
        col_main, col_side = st.columns([2, 1])

        with col_main:
            # GRÁFICO 1: EVOLUÇÃO (Barras Modernas estilo Neon)
            st.subheader(f"Evolução Anual ({ano_sel})")
            
            if not df_ano.empty:
                df_evo = df_ano[df_ano["type"] == "gasto"].copy()
                df_evo["mes_nome"] = df_evo["payment_date"].dt.strftime("%b")
                df_evo["mes_num"] = df_evo["payment_date"].dt.month
                
                df_grouped = df_evo.groupby(["mes_num", "mes_nome"])["amount"].sum().reset_index().sort_values("mes_num")
                
                fig_bar = px.bar(
                    df_grouped, x="mes_nome", y="amount",
                    text="amount",
                    color="amount",
                    color_continuous_scale=["#4facfe", "#00f2fe"], # Gradiente Cyan/Azul
                    template="plotly_dark"
                )
                fig_bar.update_traces(texttemplate='R$ %{y:.0f}', textposition='outside', marker_line_width=0, opacity=0.9)
                fig_bar.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    xaxis_title="", yaxis_title="", showlegend=False,
                    coloraxis_showscale=False,
                    margin=dict(t=20, b=20, l=10, r=10),
                    height=320
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Sem dados anuais.")

            # GRÁFICO 2: BARRAS HORIZONTAIS (Categorias)
            st.subheader("Onde você gastou este mês?")
            df_gasto_mes = df_mes[df_mes["type"] == "gasto"]
            if not df_gasto_mes.empty:
                df_cat = df_gasto_mes.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=True)
                
                fig_h = px.bar(
                    df_cat, x="amount", y="category", orientation='h',
                    color="amount", color_continuous_scale="Viridis",
                    template="plotly_dark", text="amount"
                )
                fig_h.update_traces(texttemplate='R$ %{x:.0f}', textposition='inside')
                fig_h.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    xaxis_title="", yaxis_title="",
                    height=300, margin=dict(t=0, b=0, l=0, r=0),
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig_h, use_container_width=True)
            else:
                st.info("Sem gastos neste mês.")

        with col_side:
            # GRÁFICO 3: DONUT (Composição)
            st.subheader("Composição")
            if not df_gasto_mes.empty:
                df_pie = df_gasto_mes.groupby("category")["amount"].sum().reset_index()
                
                fig_donut = go.Figure(data=[go.Pie(
                    labels=df_pie['category'], 
                    values=df_pie['amount'], 
                    hole=.65,
                    marker=dict(colors=px.colors.qualitative.Pastel)
                )])
                
                fig_donut.update_layout(
                    template="plotly_dark",
                    showlegend=True,
                    legend=dict(orientation="h", y=-0.1),
                    margin=dict(t=0, b=0, l=0, r=0),
                    height=300,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    annotations=[dict(text='Gastos', x=0.5, y=0.5, font_size=16, showarrow=False, font_color="white")]
                )
                st.plotly_chart(fig_donut, use_container_width=True)
            else:
                st.caption("Sem dados.")

            # LISTA: ÚLTIMAS ATIVIDADES
            st.subheader("Últimas Atividades")
            recents = df_mes.sort_values("payment_date", ascending=False).head(5)
            
            if not recents.empty:
                for _, r in recents.iterrows():
                    cor_valor = "#FF5252" if r["type"] == "gasto" else "#00E676"
                    sinal = "-" if r["type"] == "gasto" else "+"
                    
                    st.markdown(
                        f"""
                        <div style="background-color: #262730; padding: 12px; border-radius: 8px; margin-bottom: 8px; border-left: 4px solid {cor_valor}; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-weight: 600; color: #EEE; font-size: 0.95rem;">{r['description']}</span>
                                <span style="color: {cor_valor}; font-weight: bold;">{sinal}R$ {r['amount']:,.2f}</span>
                            </div>
                            <div style="font-size: 0.8rem; color: #AAA; margin-top: 4px;">
                                {r['category']} • {r['payment_date'].strftime('%d/%m')}
                            </div>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
            else:
                st.caption("Nenhuma atividade.")

def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if st.session_state.logged_in:
        dashboard_screen()
    else:
        login_screen()

if __name__ == "__main__":
    main()