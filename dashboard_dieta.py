import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
from datetime import datetime

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Dashboard Metabólico", layout="wide")
st.title("📊 Dashboard - Salvando no GitHub")

# --- CONEXÃO COM GITHUB ---
def get_github_connection():
    try:
        # Pega o token dos segredos
        token = st.secrets["github"]["token"]
        g = Github(token)
        # Pega o repositório atual automaticamente (usuário/repo)
        # Como estamos rodando dentro do repo, precisamos saber o nome dele.
        # Substitua 'diegotonialperetti/meu-dashboard-metabolico' pelo SEU se for diferente
        repo_name = "diegotonialperetti/meu-dashboard-metabolico" 
        repo = g.get_repo(repo_name)
        return repo
    except Exception as e:
        st.error(f"Erro na conexão com GitHub: {e}")
        return None

# --- FUNÇÕES DE DADOS ---
def load_data():
    try:
        repo = get_github_connection()
        if not repo: return pd.DataFrame(columns=["Data", "Peso", "Calorias"])

        # Tenta ler o arquivo dados.csv do repositório
        try:
            contents = repo.get_contents("dados_dieta.csv")
            csv_string = contents.decoded_content.decode("utf-8")
            df = pd.read_csv(StringIO(csv_string))
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df.sort_values(by="Data")
        except:
            # Se o arquivo não existir, retorna vazio
            return pd.DataFrame(columns=["Data", "Peso", "Calorias"])
            
    except Exception as e:
        return pd.DataFrame(columns=["Data", "Peso", "Calorias"])

def save_data(date, peso, calorias):
    repo = get_github_connection()
    if not repo: return

    date_str = date.strftime("%Y-%m-%d")
    new_line = f"{date_str},{peso},{calorias}\n"

    try:
        # Tenta pegar o arquivo existente
        contents = repo.get_contents("dados_dieta.csv")
        current_data = contents.decoded_content.decode("utf-8")
        
        # Adiciona a nova linha
        updated_data = current_data + new_line
        
        # Atualiza o arquivo no GitHub
        repo.update_file("dados_dieta.csv", f"Adicionando registro {date_str}", updated_data, contents.sha)
        
    except:
        # Se o arquivo não existe, cria um novo com cabeçalho
        header = "Data,Peso,Calorias\n"
        repo.create_file("dados_dieta.csv", "Criando arquivo de dados", header + new_line)

# --- INTERFACE ---
st.sidebar.header("📝 Novo Registro")
data_input = st.sidebar.date_input("Data", datetime.now())
peso_input = st.sidebar.number_input("Peso (kg)", format="%.2f", step=0.1)
calorias_input = st.sidebar.number_input("Calorias", step=10)

if st.sidebar.button("💾 Salvar no GitHub"):
    with st.spinner("Salvando..."):
        save_data(data_input, peso_input, calorias_input)
    st.success("Salvo! Atualize a página em instantes.")
    import time
    time.sleep(2)
    st.rerun()

# --- EXIBIÇÃO ---
df = load_data()

# Lógica IA Simples
tdee_real = 0
status_ia = False

if not df.empty and len(df) > 7:
    df['Media_Peso'] = df['Peso'].rolling(window=7).mean()
    df['Media_Calorias'] = df['Calorias'].rolling(window=7).mean()
    recent = df.tail(14)
    if len(recent) >= 7:
        delta_peso = recent.iloc[-1]['Media_Peso'] - recent.iloc[0]['Media_Peso']
        media_kcal = recent['Media_Calorias'].mean()
        superavit = (delta_peso * 7700) / len(recent)
        tdee_real = media_kcal - superavit
        status_ia = True

col1, col2, col3 = st.columns(3)
if status_ia:
    col1.metric("🔥 Gasto Real", f"{int(tdee_real)}")
    col2.metric("📉 Secar", f"{int(tdee_real - 500)}")
    col3.metric("📈 Ganhar", f"{int(tdee_real + 250)}")
else:
    col1.metric("Status", "Coletando dados...")

if not df.empty:
    st.line_chart(df.set_index("Data")["Peso"])
    st.dataframe(df)
