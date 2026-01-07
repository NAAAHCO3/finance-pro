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
from src.services.export_service import ExportService
from src.services.category_service import CategoryService # Novo serviço adicionado

# Cria tabelas se não existirem
Base.metadata.create_all(bind=engine)

# ======================================================
# CONFIGURAÇÃO DA PÁGINA
# ======================================================
st.set_page_config(
    page_title="Finance Pro - Gestão de Gastos",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- FUNÇÃO DE CSS CONDICIONAL (MODO CLARO/ESCURO) ---
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
    # Login sempre usa modo escuro para consistência visual
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
                    if not username or not password:
                        st.warning("⚠️ Preencha usuário e senha.")
                    else:
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
                    if not new_user or not new_pass:
                        st.warning("⚠️ Por favor, digite um usuário e uma senha.")
                    else:
                        with get_db() as db:
                            # Gera e-mail único para evitar travamento do banco
                            email_unico = f"{new_user.strip().lower()}@finance.pro"
                            if create_user(db, new_user, email_unico, new_pass):
                                st.success("✅ Conta criada! Faça login.")
                            else:
                                st.error("❌ Esse usuário já existe.")

# ======================================================
# DASHBOARD PRINCIPAL
# ======================================================
def dashboard_screen():
    user_id = st.session_state.user_id

    # --- Sidebar: Configurações ---
    with st.sidebar:
        st.markdown(f"### 👤 {st.session_state.username}")
        
        # 1. TOGGLE DE TEMA
        st.caption("Aparência")
        modo_escuro = st.toggle("🌙 Modo Escuro", value=True)
        
        st.markdown("---")
        
        # 2. EDITOR DE CATEGORIAS
        with st.expander("📝 Editor de Categorias"):
            with get_db() as db:
                cat_service = CategoryService(db)
                
                # Adicionar Nova
                st.write("**Nova Categoria:**")
                with st.form("add_cat_form"):
                    nova_cat = st.text_input("Nome", placeholder="Ex: Viagem")
                    tipo_cat = st.selectbox("Tipo", ["gasto", "renda"])
                    
                    if st.form_submit_button("➕ Adicionar", use_container_width=True):
                        if nova_cat:
                            if cat_service.adicionar(user_id, nova_cat, tipo_cat):
                                st.success("Criada!")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.warning("Já existe.")
                
                st.divider()
                
                # Listar / Excluir
                st.write("**Seu Menu:**")
                cats_user = cat_service.listar_todos(user_id)
                
                if cats_user:
                    for c in cats_user:
                        c1, c2 = st.columns([3, 1])
                        c1.text(f"{c.name} ({c.type})")
                        if c2.button("🗑️", key=f"del_{c.id}"):
                            cat_service.deletar(user_id, c.name)
                            st.rerun()
                else:
                    st.caption("Nenhuma categoria personalizada.")

        st.markdown("---")
        if st.button("🚪 Sair", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # --- APLICA O CSS BASEADO NO TOGGLE ---
    load_css(modo_escuro)
    
    # Cores dinâmicas para gráficos (Texto Branco no Escuro / Preto no Claro)
    text_color = "white" if modo_escuro else "black"
    grid_color = "#333" if modo_escuro else "#ddd"
    
    # --- Header ---
    hora = pd.Timestamp.now().hour
    saudacao = "Bom dia" if 5 <= hora < 12 else "Boa tarde" if 12 <= hora < 18 else "Boa noite"
    st.title(f"{saudacao}, {st.session_state.username}!")

    with get_db() as db:
        srv_trans = TransactionService(db)
        srv_budget = BudgetService(db)
        srv_ml = MLService(db)
        srv_cat = CategoryService(db)

        # 1. Carregar Dados Totais
        df = srv_trans.df_usuario(user_id)

        # Se não houver dados
        if df.empty:
            st.info("👋 Bem-vindo! Comece adicionando categorias no menu lateral e registre sua primeira movimentação abaixo.")

        # =================================================
        # ÁREA DE "ADICIONAR TRANSAÇÃO" (EXPANDER)
        # =================================================
        with st.expander("💰 Registrar Nova Movimentação", expanded=False):
            with st.form("form_add_transaction"):
                c1, c2, c3 = st.columns(3)
                
                # --- CARREGA CATEGORIAS DO BANCO + PADRÃO ---
                cats_user_objs = srv_cat.listar_todos(user_id)
                cats_nomes = [c.name for c in cats_user_objs]
                cats_padrao = srv_cat.listar_padrao()
                
                # Combina e ordena (Set remove duplicadas)
                lista_final = sorted(list(set(cats_nomes + cats_padrao)))
                
                tipo = c1.selectbox("Tipo", ["gasto", "renda"])
                valor = c2.number_input("Valor", min_value=0.01, step=10.0)
                
                # O Selectbox envia o NOME (String)
                categoria = c3.selectbox("Categoria", lista_final)
                
                desc = st.text_input("Descrição (Opcional)")
                data_mov = st.date_input("Data", date.today())
                
                if st.form_submit_button("Salvar Registro", use_container_width=True, type="primary"):
                    # Passamos o nome da categoria. O Service resolve o ID.
                    srv_trans.registrar(
                        user_id=user_id, 
                        tipo=tipo, 
                        valor_total=valor, 
                        categoria_nome=categoria, 
                        conta_nome="Carteira", 
                        descricao=desc, 
                        data_compra=data_mov
                    )
                    st.success("Registrado!")
                    time.sleep(0.5)
                    st.rerun()

        # =================================================
        # DASHBOARD DE ANÁLISE
        # =================================================
        
        if not df.empty:
            # Filtros de Data
            with st.container():
                col_date1, col_date2, _ = st.columns([1, 1, 4])
                
                # Garante conversão de data
                if "date" in df.columns:
                    df["date"] = pd.to_datetime(df["date"])

                with col_date1:
                    anos = sorted(df["date"].dt.year.unique(), reverse=True)
                    ano_sel = st.selectbox("Ano", anos, key="year_sel")
                with col_date2:
                    meses_disp = sorted(df[df["date"].dt.year == ano_sel]["date"].dt.month.unique(), reverse=True)
                    mes_map = {1:"Jan", 2:"Fev", 3:"Mar", 4:"Abr", 5:"Mai", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Set", 10:"Out", 11:"Nov", 12:"Dez"}
                    if not meses_disp: meses_disp = [date.today().month]
                    mes_sel = st.selectbox("Mês", meses_disp, format_func=lambda x: mes_map.get(x, str(x)), key="month_sel")

            df_filtrado = df[(df["date"].dt.year == ano_sel) & (df["date"].dt.month == mes_sel)]
            
            # KPIs Cards
            receita = df_filtrado[df_filtrado["type"] == "renda"]["amount"].sum()
            gasto = df_filtrado[df_filtrado["type"] == "gasto"]["amount"].sum()
            saldo = receita - gasto

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Receitas", f"R$ {receita:,.2f}", delta="Mensal")
            col2.metric("Despesas", f"R$ {gasto:,.2f}", delta="-Saídas", delta_color="inverse")
            col3.metric("Saldo", f"R$ {saldo:,.2f}", delta="Residuo", delta_color="off")
            
            # KPI 4: ML Projeção
            hoje = date.today()
            if (hoje.year == ano_sel) and (hoje.month == mes_sel):
                resultado_ml = srv_ml.calcular_projecao_inteligente(user_id, df_filtrado)
                val_proj = resultado_ml["valor"] if isinstance(resultado_ml, dict) else resultado_ml
                metodo_proj = resultado_ml["metodo"] if isinstance(resultado_ml, dict) else "Estimativa"
                
                col4.metric("Projeção Fim do Mês", f"R$ {val_proj:,.2f}", delta=f"Base: {metodo_proj}", delta_color="off")
            else:
                col4.metric("Status", "Mês Fechado", delta="Finalizado", delta_color="off")

            st.markdown("---")

            # Gráficos
            c_chart1, c_chart2 = st.columns([1, 2])
            with c_chart1:
                st.subheader("Gastos por Categoria")
                df_gasto = df_filtrado[df_filtrado["type"] == "gasto"]
                if not df_gasto.empty:
                    # Se tiver muitas categorias, usa Barras Horizontais
                    if len(df_gasto) > 5:
                        df_gasto = df_gasto.sort_values(by="amount", ascending=True)
                        fig = px.bar(df_gasto, x="amount", y="category", orientation='h', text="amount", color="category", color_discrete_sequence=px.colors.qualitative.Pastel)
                        fig.update_traces(texttemplate='R$ %{x:.2s}', textposition='auto')
                        fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=350,
                            xaxis=dict(showgrid=False, showticklabels=False, color=text_color),
                            yaxis=dict(showgrid=False, color=text_color),
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color=text_color))
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        # Donut Chart
                        fig_pizza = go.Figure(data=[go.Pie(labels=df_gasto['category'], values=df_gasto['amount'], hole=.65, textinfo='percent', textposition='outside', marker=dict(colors=px.colors.qualitative.Pastel))])
                        fig_pizza.update_layout(showlegend=True, legend=dict(orientation="h", y=-0.1),
                            annotations=[dict(text=f'R$ {gasto:,.0f}', x=0.5, y=0.5, font_size=20, showarrow=False, font_color=text_color)],
                            margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=350,
                            font=dict(color=text_color))
                        st.plotly_chart(fig_pizza, use_container_width=True)
                else:
                    st.info("Sem gastos registrados.")

            with c_chart2:
                st.subheader("Balanço Diário")
                df_diario = df_filtrado.groupby([df_filtrado["date"].dt.day, "type"])["amount"].sum().reset_index()
                df_diario.columns = ["Dia", "Tipo", "Valor"]
                if not df_diario.empty:
                    fig_bar = px.bar(df_diario, x="Dia", y="Valor", color="Tipo", barmode="group", color_discrete_map={"renda": "#2ecc71", "gasto": "#e74c3c"})
                    fig_bar.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=350,
                        xaxis=dict(showgrid=False, color=text_color, tickmode='linear'),
                        yaxis=dict(showgrid=True, gridcolor=grid_color, color=text_color),
                        legend=dict(orientation="h", y=1.1, title="", font=dict(color=text_color)),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.info("Sem movimentações.")

            # Radar IA
            st.subheader("🕵️‍♂️ Radar Financeiro (IA)")
            anomalias = srv_ml.detectar_anomalias(df_filtrado)
            if not anomalias.empty:
                st.caption("O sistema detectou transações fora do padrão.")
                for _, row in anomalias.iterrows():
                    with st.expander(f"🔴 {row['category']} - R$ {row['amount']:,.2f}", expanded=True):
                        st.write(f"**Data:** {row['date'].strftime('%d/%m/%Y')}")
                        st.write(f"**Descrição:** {row['description'] or '-'}")
                        st.caption("Valor atípico.")
            else:
                if not df_filtrado.empty:
                    st.success("Nenhuma anomalia detectada.", icon="🛡️")

            st.markdown("---")

            # Listas
            c_ext, c_orc = st.columns([2, 1])
            with c_ext:
                st.subheader("⏱️ Últimas Movimentações")
                if not df_filtrado.empty:
                    for _, r in df_filtrado.sort_values("date", ascending=False).head(5).iterrows():
                        icon = "🔻" if r["type"]=="gasto" else "💚"
                        val_fmt = f":red[R$ {r['amount']:,.2f}]" if r["type"]=="gasto" else f":green[R$ {r['amount']:,.2f}]"
                        st.markdown(f"**{icon} {r['category']}** | {r['description']} | {val_fmt}")
                        st.divider()
            with c_orc:
                st.subheader("🎯 Orçamentos")
                alerts = srv_budget.alertas(user_id, df_filtrado)
                if alerts:
                    for a in alerts: st.error(a)
                else:
                    st.info("Dentro da meta.")

def main():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.username = None

    if st.session_state.logged_in:
        dashboard_screen()
    else:
        login_screen()

if __name__ == "__main__":
    main()