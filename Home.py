import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
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
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======================================================
# ESTILOS CSS (NEON / DARK)
# ======================================================
def inject_custom_css():
    st.markdown("""
    <style>
        /* Fundo Geral e Sidebar já são escuros pelo tema do Streamlit, 
           mas vamos reforçar os Cards */
        
        /* Estilo dos Cards de Métricas (KPIs) */
        div[data-testid="stMetric"] {
            background-color: #1E1E2E; /* Cor de fundo do card */
            border: 1px solid #333;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            transition: transform 0.2s;
        }
        div[data-testid="stMetric"]:hover {
            transform: scale(1.02);
            border-color: #6C5CE7; /* Borda roxa neon ao passar o mouse */
        }
        
        /* Cores dos Textos das Métricas */
        div[data-testid="stMetricLabel"] {
            color: #A6A6A6 !important;
            font-size: 0.9rem;
        }
        div[data-testid="stMetricValue"] {
            color: #FFFFFF !important;
            font-weight: bold;
        }
        
        /* Ajuste de tabelas */
        div[data-testid="stDataFrame"] {
            background-color: #1E1E2E;
            border-radius: 10px;
            padding: 10px;
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
# DASHBOARD DE ANÁLISE (MODERNO)
# ======================================================
def dashboard_screen():
    # Injeta o CSS Neon
    inject_custom_css()
    
    user_id = st.session_state.user_id

    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        st.caption("Menu Principal")
        st.markdown("---")
        st.info("💡 Acesse **Movimentações** no menu lateral para editar ou adicionar lançamentos.")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.title(f"Dashboard Financeiro")
    st.caption(f"Visão geral das finanças de {st.session_state.username}")

    with get_db() as db:
        srv_trans = TransactionService(db)
        srv_stats = MLService(db)

        # 1. Carregar Dados
        df = srv_trans.df_usuario(user_id)

        if df.empty:
            st.info("👋 Olá! Você ainda não tem dados. Vá na página **📝 Movimentações** para começar.")
            return

        # ==============================================================================
        # FILTROS (Baseados em Vencimento/Fluxo de Caixa)
        # ==============================================================================
        if "payment_date" in df.columns: 
            df["payment_date"] = pd.to_datetime(df["payment_date"])
        
        with st.container():
            col_date1, col_date2, _ = st.columns([1, 1, 4])
            with col_date1:
                anos = sorted(df["payment_date"].dt.year.unique(), reverse=True)
                ano_sel = st.selectbox("Ano", anos, key="year_sel")
            with col_date2:
                meses_disp = sorted(df[df["payment_date"].dt.year == ano_sel]["payment_date"].dt.month.unique(), reverse=True)
                mes_map = {1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez"}
                if not meses_disp: meses_disp = [date.today().month]
                mes_sel = st.selectbox("Mês", meses_disp, format_func=lambda x: mes_map.get(x, str(x)), key="month_sel")

        # Filtra DataFrame pelo Mês Selecionado
        df_filtrado = df[(df["payment_date"].dt.year == ano_sel) & (df["payment_date"].dt.month == mes_sel)]
        # Filtra DataFrame pelo Ano Inteiro (para gráfico de evolução)
        df_ano = df[df["payment_date"].dt.year == ano_sel]

        # --- ESTATÍSTICAS (Usando MLService atualizado) ---
        stats = srv_stats.analisar_padrao_gastos(df_filtrado)

        # 3. KPIs SUPERIORES
        receita = df_filtrado[df_filtrado["type"] == "renda"]["amount"].sum()
        gasto = df_filtrado[df_filtrado["type"] == "gasto"]["amount"].sum()
        saldo = receita - gasto
        media_dia = stats.get("media_diaria", 0.0)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 Saldo do Mês", f"R$ {saldo:,.2f}")
        c2.metric("📉 Despesas", f"R$ {gasto:,.2f}", delta="-Saídas", delta_color="inverse")
        c3.metric("📈 Receitas", f"R$ {receita:,.2f}")
        c4.metric("📊 Média Diária", f"R$ {media_dia:,.2f}", delta="Ritmo Real", delta_color="off")

        st.markdown("---")

        # 4. GRÁFICOS VISUAIS (LAYOUT 2 COLUNAS)
        col_main, col_side = st.columns([2, 1])

        with col_main:
            st.subheader(f"Evolução em {ano_sel}")
            
            # Prepara dados para o gráfico de barras anual
            df_gasto_ano = df_ano[df_ano["type"] == "gasto"].copy()
            if not df_gasto_ano.empty:
                df_gasto_ano["mes_num"] = df_gasto_ano["payment_date"].dt.month
                df_gasto_ano["mes_nome"] = df_gasto_ano["payment_date"].dt.strftime("%b")
                
                df_bar = df_gasto_ano.groupby(["mes_num", "mes_nome"])["amount"].sum().reset_index().sort_values("mes_num")
                
                # Gráfico Neon de Barras
                fig_bar = px.bar(
                    df_bar, x="mes_nome", y="amount",
                    color="amount",
                    color_continuous_scale=["#4facfe", "#00f2fe"], # Gradiente Azul Neon
                    template="plotly_dark"
                )
                fig_bar.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    xaxis_title="", yaxis_title="", showlegend=False,
                    margin=dict(t=10, b=10, l=10, r=10),
                    height=350
                )
                fig_bar.update_traces(marker_line_width=0, opacity=0.9, texttemplate="R$ %{y:.2s}")
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Sem dados anuais.")

            # Detalhamento por Categoria (Barras Horizontais)
            st.subheader("Onde você gastou este mês?")
            df_gasto_mes = df_filtrado[df_filtrado["type"] == "gasto"]
            if not df_gasto_mes.empty:
                df_cat = df_gasto_mes.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=True)
                
                fig_h = px.bar(
                    df_cat, x="amount", y="category", orientation='h',
                    color="amount", 
                    color_continuous_scale="Viridis", # Gradiente Moderno
                    template="plotly_dark"
                )
                fig_h.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    xaxis_title="", yaxis_title="",
                    height=300, margin=dict(t=0, b=0, l=0, r=0)
                )
                fig_h.update_traces(texttemplate='R$ %{x:.2s}', textposition='auto')
                st.plotly_chart(fig_h, use_container_width=True)
            else:
                st.info("Sem gastos neste mês.")

        with col_side:
            st.subheader("Composição")
            
            # Gráfico de Rosca (Donut Chart)
            if not df_gasto_mes.empty:
                df_cat_donut = df_gasto_mes.groupby("category")["amount"].sum().reset_index()
                
                fig_donut = go.Figure(data=[go.Pie(
                    labels=df_cat_donut['category'], 
                    values=df_cat_donut['amount'], 
                    hole=.7, # Buraco no meio para virar Rosca
                    marker=dict(colors=px.colors.qualitative.Pastel)
                )])
                
                fig_donut.update_layout(
                    template="plotly_dark",
                    showlegend=True,
                    legend=dict(orientation="h", y=-0.2),
                    margin=dict(t=20, b=0, l=20, r=20),
                    height=350,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    # Texto no centro da rosca
                    annotations=[dict(text=f'Gastos', x=0.5, y=0.5, font_size=16, showarrow=False)]
                )
                st.plotly_chart(fig_donut, use_container_width=True)
            else:
                st.caption("Sem dados.")

            # Lista de Últimas Transações
            st.subheader("Últimas Atividades")
            recents = df_filtrado.sort_values("payment_date", ascending=False).head(5)
            
            if not recents.empty:
                for _, r in recents.iterrows():
                    # Formata visualmente
                    cor_valor = "#FF5252" if r["type"] == "gasto" else "#69F0AE"
                    sinal = "-" if r["type"] == "gasto" else "+"
                    
                    st.markdown(
                        f"""
                        <div style="background-color: #262730; padding: 10px; border-radius: 5px; margin-bottom: 8px; border-left: 3px solid {cor_valor}">
                            <div style="display: flex; justify-content: space-between;">
                                <span style="font-weight: bold; font-size: 0.9rem;">{r['description']}</span>
                                <span style="color: {cor_valor}; font-weight: bold;">{sinal}R$ {r['amount']:,.2f}</span>
                            </div>
                            <div style="font-size: 0.8rem; color: #aaa;">
                                {r['category']} • {r['payment_date'].strftime('%d/%m')}
                            </div>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
            else:
                st.caption("Nenhuma atividade recente.")

def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if st.session_state.logged_in:
        dashboard_screen()
    else:
        login_screen()

if __name__ == "__main__":
    main()