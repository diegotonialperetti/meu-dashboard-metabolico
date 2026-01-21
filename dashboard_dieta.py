import streamlit as st
import pandas as pd
import altair as alt
from github import Github
from io import StringIO
from datetime import datetime, date

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Debug Mode", layout="wide")
st.title("🛠️ Modo de Correção de Erros")

# --- CONEXÃO GITHUB ---
def get_github_connection():
    try:
        # Tenta pegar o token
        if "github" not in st.secrets:
            st.error("🚨 ERRO: Não encontrei o token [github] nos Secrets!")
            return None
            
        token = st.secrets["github"]["token"]
        g = Github(token)
        
        # VERIFICAÇÃO 1: O Token funciona?
        try:
            user = g.get_user().login
            st.success(f"✅ Conectado ao GitHub como: {user}")
        except Exception as e:
            st.error(f"🚨 Token Inválido ou sem permissão: {e}")
            return None

        # VERIFICAÇÃO 2: O Repositório existe?
        repo_name = "diegotonialperetti/meu-dashboard-metabolico" 
        try:
            repo = g.get_repo(repo_name)
            return repo
        except Exception as e:
            st.error(f"🚨 Não achei o repositório '{repo_name}'. Erro: {e}")
            return None

    except Exception as e:
        st.error(f"🚨 Erro Geral na Conexão: {e}")
        return None

# --- CARREGAR DADOS COM DIAGNÓSTICO ---
def load_data():
    repo = get_github_connection()
    if not repo: 
        st.warning("⚠️ Sem conexão, parando carregamento.")
        return pd.DataFrame()

    try:
        # Tenta listar arquivos para ver se estamos no lugar certo
        contents_list = repo.get_contents("")
        arquivos = [f.name for f in contents_list]
        
        if "dados_dieta.csv" not in arquivos:
            st.error(f"🚨 O arquivo 'dados_dieta.csv' NÃO existe neste repositório! Arquivos encontrados: {arquivos}")
            return pd.DataFrame()

        # Tenta ler o arquivo
        try:
            contents = repo.get_contents("dados_dieta.csv")
            csv_string = contents.decoded_content.decode("utf-8")
            
            # Mostra as primeiras linhas para debug (opcional)
            # st.text(f"Primeiras linhas do arquivo:\n{csv_string[:100]}...")
            
            df = pd.read_csv(StringIO(csv_string))
            st.success(f"✅ Arquivo carregado! {len(df)} linhas encontradas.")
            
            # Tratamento de dados
            cols = ['Passos', 'Proteina', 'Sono', 'Cintura', 'Altura', 'BPM', 'Energia', 'Pressao_High', 'Pressao_Low', 'SpO2']
            for col in cols:
                if col not in df.columns: df[col] = 0.0
            
            df['Timestamp'] = pd.to_datetime(df['Data'])
            df['Data_Ref'] = df['Timestamp'].dt.date
            df['Hora'] = df['Timestamp'].dt.hour
            df['Minuto'] = df['Timestamp'].dt.minute
            
            return df.sort_values(by="Timestamp")
            
        except Exception as e:
            st.error(f"🚨 Erro ao LER o CSV (O arquivo existe, mas está corrompido?): {e}")
            return pd.DataFrame()

    except Exception as e:
        st.error(f"🚨 Erro desconhecido no load_data: {e}")
        return pd.DataFrame()

# --- INICIALIZAÇÃO ---
df_raw = load_data()

if df_raw.empty:
    st.warning("⚠️ O banco de dados retornou vazio. Veja os erros acima.")
else:
    st.write("### 🎉 Se você está vendo isso, os dados voltaram!")
    st.dataframe(df_raw.head())
