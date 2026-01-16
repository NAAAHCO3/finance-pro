
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

# ======================================================
# INIT DB
# ======================================================
Base.metadata.create_all(bind=engine)

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(
    page_title="Finance Pro - Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ======================================================
# CSS
# ======================================================
def inject_custom_css():
    st.markdown("""
    <style>
        div[data-testid="stMetric"] {
            background-color: #1E1E2E;
            border: 1px solid #333;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        div[data-testid="stMetric"]:hover {
            border-color: #6C5CE7;
        }
    </style>
    """, unsafe_allow_html=True)

# ======================================================
# LOGIN
# ======================================================
def login_screen():
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<h1 style='text-align:center'>💳 Finance Pro</h1>", unsafe_allow_html=True)
        tab_login, tab_reg = st.tabs(["Acessar", "Registrar"])

        with tab_login:
            with st.form("login"):
                u = st.text_input("Usuário")
                p = st.text_input("Senha", type="password")
                if st.form_submit_button("Entrar", type="primary", use_container_width=True):
                    with get_db() as db:
                        user = get_user_by_username(db, u)
                        if user and verify_password(p, user.password_hash):
                            st.session_state.logged_in = True
                            st.session_state.user_id = user.id
                            st.session_state.username = user.username
                            st.rerun()
                        else:
                            st.error("Credenciais inválidas")

        with tab_reg:
            with st.form("reg"):
                u = st.text_input("Usuário")
                p = st.text_input("Senha", type="password")
                if st.form_submit_button("Criar Conta"):
                    with get_db() as db:
                        email = f"{u.lower()}@finance.pro"
                        if create_user(db, u, email, p):
                            st.success("Conta criada!")
                        else:
                            st.error("Usuário já existe")

# ======================================================
# DASHBOARD
# ======================================================
def dashboard_screen():
    inject_custom_css()
    user_id = st.session_state.user_id

    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.title("📊 Dashboard Financeiro")

    with get_db() as db:
        srv_trans = TransactionService(db)
        srv_ml = MLService(db)

        df = srv_trans.df_usuario(user_id)
        if df.empty:
            st.info("Cadastre movimentações para visualizar o dashboard.")
            return

        df["payment_date"] = pd.to_datetime(df["payment_date"])

        # =========================
        # FILTROS
        # =========================
        anos = sorted(df["payment_date"].dt.year.unique(), reverse=True)
        col_y, col_m, _ = st.columns([1, 1, 4])

        ano = col_y.selectbox("Ano", anos)
        meses = sorted(df[df["payment_date"].dt.year == ano]["payment_date"].dt.month.unique())
        mes = col_m.selectbox("Mês", meses, index=len(meses)-1)

        df_mes = df[(df["payment_date"].dt.year == ano) & (df["payment_date"].dt.month == mes)]
        df_ano = df[df["payment_date"].dt.year == ano]

        # =========================
        # KPIs
        # =========================
        receita = df_mes[df_mes["type"] == "renda"]["amount"].sum()
        gasto = df_mes[df_mes["type"] == "gasto"]["amount"].sum()
        saldo = receita - gasto
        media = srv_ml.analisar_padrao_gastos(df_mes).get("media_diaria", 0)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 Saldo", f"R$ {saldo:,.2f}")
        c2.metric("📉 Gastos", f"R$ {gasto:,.2f}")
        c3.metric("📈 Receitas", f"R$ {receita:,.2f}")
        c4.metric("📊 Média Diária", f"R$ {media:,.2f}")

        st.divider()

        # =========================
        # GRÁFICO ANUAL
        # =========================
        st.subheader(f"📈 Evolução Anual ({ano})")

        df_evo = (
            df_ano
            .assign(mes=df_ano["payment_date"].dt.month)
            .groupby(["mes", "type"])["amount"]
            .sum()
            .reset_index()
        )

        fig_ano = px.line(
            df_evo,
            x="mes",
            y="amount",
            color="type",
            markers=True,
            template="plotly_dark",
            labels={"mes": "Mês", "amount": "Valor"}
        )
        st.plotly_chart(fig_ano, use_container_width=True)

        # =========================
        # GRÁFICOS MENSAIS
        # =========================
        col_g, col_r = st.columns(2)

        with col_g:
            st.subheader("📉 Gastos Diários")
            df_g = df_mes[df_mes["type"] == "gasto"]
            if not df_g.empty:
                df_d = df_g.groupby(df_g["payment_date"].dt.date)["amount"].sum().reset_index()
                fig_d = px.line(df_d, x="payment_date", y="amount", markers=True, template="plotly_dark")
                st.plotly_chart(fig_d, use_container_width=True)
            else:
                st.caption("Sem gastos")

        with col_r:
            st.subheader("📊 Receitas do Mês")
            df_r = df_mes[df_mes["type"] == "renda"]
            if not df_r.empty:
                fig_r = px.bar(df_r, x="payment_date", y="amount", template="plotly_dark")
                st.plotly_chart(fig_r, use_container_width=True)
            else:
                st.caption("Sem receitas")

        # =========================
        # CATEGORIAS + ATIVIDADES
        # =========================
        col_c, col_l = st.columns([2, 1])

        with col_c:
            st.subheader("Categorias de Gasto")
            if not df_g.empty:
                df_cat = df_g.groupby("category")["amount"].sum().reset_index()
                fig_cat = px.bar(df_cat, x="amount", y="category", orientation="h", template="plotly_dark")
                st.plotly_chart(fig_cat, use_container_width=True)

        with col_l:
            st.subheader("Últimas Atividades")
            for _, r in df_mes.sort_values("payment_date", ascending=False).head(5).iterrows():
                cor = "#FF5252" if r["type"] == "gasto" else "#00E676"
                st.markdown(
                    f"""
                    <div style="background:#262730;padding:8px;border-left:3px solid {cor};margin-bottom:6px">
                        <b>{r['description']}</b><br>
                        <span style="color:{cor}">R$ {r['amount']:,.2f}</span> · {r['category']}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

# ======================================================
# MAIN
# ======================================================
def main():
    if not st.session_state.get("logged_in"):
        login_screen()
    else:
        dashboard_screen()

if __name__ == "__main__":
    main()
