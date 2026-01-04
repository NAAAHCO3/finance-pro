💰 Finance DS — Personal Finance Analytics Platform

Plataforma de controle financeiro pessoal multiusuário, com análises avançadas, dashboards interativos e previsão de gastos usando Machine Learning — construída com Streamlit + Python, 100% gratuita e sem dependência de serviços pagos.

🚀 Funcionalidades
🔐 Autenticação

Cadastro e login de usuários

Senhas criptografadas (bcrypt)

Isolamento total de dados por usuário

📊 Dashboard Inteligente

KPIs mensais (Receita, Despesa, Saldo)

Comparação automática com mês anterior

Gráficos interativos (Plotly)

Filtro por mês e ano (time slicing)

📝 Lançamentos

Registro de receitas e despesas

Contas e categorias personalizadas

Histórico detalhado por período

🎯 Orçamentos

Definição de limites mensais por categoria

Barra de progresso por orçamento

Alerta visual ao estourar limite

🤖 Machine Learning

Previsão de próximo gasto por categoria

Regressão linear simples

Usa histórico completo do usuário

Proteções contra dados insuficientes

🧱 Arquitetura do Projeto
finance-ds/
│
├── app.py                     # Entry point (Streamlit)
├── requirements.txt
├── README.md
│
├── data/
│   └── finance.db             # SQLite (gerado automaticamente)
│
├── src/
│   ├── core/
│   │   ├── settings.py        # Configurações globais
│   │   └── security.py        # Hash e verificação de senha
│   │
│   ├── database.py            # Engine, Base, sessão DB
│   │
│   ├── auth.py                # Login e criação de usuário
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── transaction.py
│   │   └── budget.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── transaction_service.py
│   │   ├── account_service.py
│   │   ├── category_service.py
│   │   ├── budget_service.py
│   │   ├── ml_service.py
│   │   └── export_service.py
│   │
│   ├── analytics/
│   │   └── analytics_service.py
│   │
│   ├── ui/
│   │   └── helpers.py
│   │
│   └── pages/
│       ├── dashboard.py
│       ├── lancamentos.py
│       └── orcamentos.py

🛠️ Como rodar localmente (do zero)
1️⃣ Criar ambiente virtual (opcional, recomendado)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

2️⃣ Instalar dependências
pip install -r requirements.txt

3️⃣ Rodar a aplicação
streamlit run app.py


A aplicação abrirá automaticamente no navegador.

🗄️ Banco de Dados

Banco: SQLite

Local: data/finance.db

Criado automaticamente ao rodar o app

Um único banco, múltiplos usuários

Dados sempre filtrados por user_id

💸 Custo do Projeto
Item	Custo
Python	R$ 0
SQLite	R$ 0
Streamlit	R$ 0
Machine Learning	R$ 0
Deploy (Streamlit Cloud)	R$ 0

✅ Custo total: ZERO

📌 Próximos passos (Roadmap sugerido)

📤 Exportação CSV / Excel por período

🔔 Alertas automáticos de orçamento

📈 Modelos ML mais avançados (ARIMA, Prophet)

☁️ Deploy no Streamlit Cloud

🔑 Recuperação de senha

🧪 Testes automatizados

👨‍💻 Perfil do Projeto

Este projeto foi pensado para:

Analistas de Dados

Cientistas de Dados iniciantes

Pessoas que querem controle financeiro real

Aprender arquitetura limpa + ML aplicado