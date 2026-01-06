import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
from datetime import datetime

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Dashboard Metabólico", layout="wide")
st.title("🏃‍♂️ Dashboard Fitness & Nutrição")

# --- CONEXÃO COM GITHUB ---
def get_github_connection():
    try:
        token = st.secrets["github"]["token"]
        g = Github(token)
        repo_name = "diegotonialperetti/meu-dashboard-metabolico" # Seu repositório
        repo = g.get_repo(repo_name)
        return repo
    except Exception as e:
        st.error(f"Erro na conexão com GitHub: {e}")
        return None

# --- FUNÇÕES DE DADOS ---
def load_data():
    try:
        repo = get_github_connection()
        if not repo: return pd.DataFrame(columns=["Data", "Peso", "Calorias", "Passos"])

        try:
            contents = repo.get_contents("dados_dieta.csv")
            csv_string = contents.decoded_content.decode("utf-8")
            df = pd.read_csv(StringIO(csv_string))
            
            # Tratamento para arquivos antigos (sem a coluna Passos)
            if 'Passos' not in df.columns:
                df['Passos'] = 0
            
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df.sort_values(by="Data")
        except:
            return pd.DataFrame(columns=["Data", "Peso", "Calorias", "Passos"])
            
    except Exception as e:
        return pd.DataFrame(columns=["Data", "Peso", "Calorias", "Passos"])

def save_data(date, peso, calorias, passos):
    repo = get_github_connection()
    if not repo: return

    date_str = date.strftime("%Y-%m-%d")
    # Nova linha agora inclui passos
    new_line = f"{date_str},{peso},{calorias},{passos}\n"

    try:
        contents = repo.get_contents("dados_dieta.csv")
        current_data = contents.decoded_content.decode("utf-8")
        
        # Se o arquivo antigo não tiver cabeçalho de Passos, a gente recria o cabeçalho
        if "Passos" not in current_data.split('\n')[0]:
            lines = current_data.split('\n')
            # Adiciona ,Passos no cabeçalho
            lines[0] = lines[0].strip() + ",Passos"
            # Adiciona ,0 nas linhas de dados antigas
            for i in range(1, len(lines)):
                if lines[i].strip(): # Se a linha não for vazia
                    lines[i] = lines[i].strip() + ",0"
            current_data = '\n'.join(lines) + '\n'

        updated_data = current_data + new_line
        repo.update_file("dados_dieta.csv", f"Registro: {date_str}", updated_data, contents.sha)
        
    except:
        header = "Data,Peso,Calorias,Passos\n"
        repo.create_file("dados_dieta.csv", "Criando arquivo", header + new_line)

# --- BARRA LATERAL ---
st.sidebar.header("📝 Novo Registro")
data_input = st.sidebar.date_input("Data", datetime.now())
peso_input = st.sidebar.number_input("Peso (kg)", format="%.2f", step=0.1)
calorias_input = st.sidebar.number_input("Calorias Ingeridas", step=10)
passos_input = st.sidebar.number_input("Passos do Dia", step=100, value=0)

if st.sidebar.button("💾 Salvar Dados"):
    with st.spinner("Salvando na nuvem..."):
        save_data(data_input, peso_input, calorias_input, passos_input)
    st.success("Salvo! Atualizando...")
    import time
    time.sleep(2)
    st.rerun()

# --- LÓGICA E VISUALIZAÇÃO ---
df = load_data()

# Lógica IA Adaptativa
tdee_real = 0
status_ia = False

if not df.empty and len(df) > 7:
    # Conversões para garantir números
    df['Peso'] = pd.to_numeric(df['Peso'])
    df['Calorias'] = pd.to_numeric(df['Calorias'])
    df['Passos'] = pd.to_numeric(df['Passos'])

    df['Media_Peso'] = df['Peso'].rolling(window=7).mean()
    df['Media_Calorias'] = df['Calorias'].rolling(window=7).mean()
    
    recent = df.tail(14)
    if len(recent) >= 7:
        delta_peso = recent.iloc[-1]['Media_Peso'] - recent.iloc[0]['Media_Peso']
        media_kcal = recent['Media_Calorias'].mean()
        
        # Cálculo Matemático
        superavit = (delta_peso * 7700) / len(recent)
        tdee_real = media_kcal - superavit
        status_ia = True
    else:
        status_ia = False
else:
    status_ia = False

# --- MÉTRICAS ---
col1, col2, col3, col4 = st.columns(4)

if status_ia:
    col1.metric("🔥 Gasto Real (TDEE)", f"{int(tdee_real)} kcal", help="Quanto você gasta por dia somando tudo")
    col2.metric("🎯 Meta Secar", f"{int(tdee_real - 500)} kcal", "-0.5kg/sem")
    
    # Estimativa de gasto só dos passos (Aprox 0.04 kcal por passo)
    media_passos_sem = int(df.tail(7)['Passos'].mean())
    kcal_passos = int(media_passos_sem * 0.04)
    
    col3.metric("👣 Média Passos (7d)", f"{media_passos_sem}", help="Média da última semana")
    col4.metric("⚡ Gasto da Caminhada", f"~{kcal_passos} kcal", help="Estimativa do gasto só com os passos")
else:
    col1.metric("Status", "Coletando dados...")
    st.info("Continue registrando! O sistema precisa de 7 dias para começar a calcular.")

st.markdown("---")

# --- GRÁFICOS ---
if not df.empty:
    tab1, tab2 = st.tabs(["📉 Peso vs Calorias", "👣 Impacto dos Passos"])
    
    with tab1:
        st.subheader("Evolução do Peso")
        # Gráfico simples de linha
        st.line_chart(df.set_index("Data")["Peso"])
    
    with tab2:
        st.subheader("Você anda mais, o peso cai?")
        # Gráfico de barras para passos
        st.bar_chart(df.set_index("Data")["Passos"])
        
    with st.expander("Ver Tabela de Dados"):
        st.dataframe(df.sort_values(by="Data", ascending=False))
