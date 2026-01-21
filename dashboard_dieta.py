import streamlit as st
import pandas as pd
from github import Github
from io import StringIO

st.title("🕵️‍♂️ Teste de Conexão GitHub")

# 1. Testar o Token
try:
    token = st.secrets["github"]["token"]
    st.write(f"✅ Token encontrado: `{token[:4]}...`")
except:
    st.error("🚨 ERRO: Não encontrei o token nos Secrets!")
    st.stop()

# 2. Testar Conexão com a Conta
try:
    g = Github(token)
    user = g.get_user().login
    st.write(f"✅ Conectado como usuário: **{user}**")
except Exception as e:
    st.error(f"🚨 ERRO ao logar no GitHub: {e}")
    st.info("Dica: Verifique se o Token está correto e não expirou.")
    st.stop()

# 3. Testar Acesso ao Repositório
repo_name = "diegotonialperetti/meu-dashboard-metabolico"
try:
    repo = g.get_repo(repo_name)
    st.write(f"✅ Repositório encontrado: `{repo_name}`")
except Exception as e:
    st.error(f"🚨 ERRO ao acessar o repositório: {e}")
    st.info("Dica: Se o repo for PRIVADO, o Token precisa ter a caixinha 'repo' marcada lá no GitHub.")
    st.stop()

# 4. Testar Leitura do Arquivo
file_path = "dados_dieta.csv"
try:
    contents = repo.get_contents(file_path)
    st.write(f"✅ Arquivo `{file_path}` localizado!")
    
    # Tentar ler o conteúdo
    csv_string = contents.decoded_content.decode("utf-8")
    st.text_area("Conteúdo Bruto do CSV (Primeiras 5 linhas):", csv_string[:300])
    
    # Tentar converter para Pandas
    df = pd.read_csv(StringIO(csv_string))
    st.success(f"🎉 SUCESSO! O Pandas leu {len(df)} linhas.")
    st.dataframe(df)
    
except Exception as e:
    st.error(f"🚨 ERRO ao ler o arquivo: {e}")
    st.info("Dica: Verifique se o arquivo 'dados_dieta.csv' existe mesmo na raiz do repositório.")
