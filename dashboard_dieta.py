import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dashboard Metabólico AI", layout="wide")
st.title("📊 Seu Dashboard Metabólico (Nuvem)")

# --- CONEXÃO COM GOOGLE SHEETS ---
def conectar_google_sheets():
    # O Streamlit busca as credenciais que colocamos em "Secrets"
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # Converte o formato do secrets para o formato que o gspread entende
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    
    client = gspread.authorize(creds)
    # Abre a planilha pelo nome exato
    sheet = client.open("DadosDieta").sheet1 
    return sheet

# --- FUNÇÕES DE DADOS ---
def load_data():
    try:
        sheet = conectar_google_sheets()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        
        # Se a planilha estiver vazia ou com colunas erradas
        if df.empty or 'Data' not in df.columns:
            return pd.DataFrame(columns=["Data", "Peso", "Calorias"])
            
        df['Data'] = pd.to_datetime(df['Data']).dt.date
        return df.sort_values(by="Data")
    except Exception as e:
        # st.error(f"Erro ao carregar dados: {e}") # Debug silencioso para não assustar no começo
        return pd.DataFrame(columns=["Data", "Peso", "Calorias"])

def save_data(date, peso, calorias):
    sheet = conectar_google_sheets()
    date_str = date.strftime("%Y-%m-%d")
    
    # Adiciona nova linha no Google Sheets
    sheet.append_row([date_str, peso, calorias])

# --- BARRA LATERAL ---
st.sidebar.header("📝 Registro Diário")
data_input = st.sidebar.date_input("Data", datetime.now())
peso_input = st.sidebar.number_input("Peso Hoje (kg)", format="%.2f", step=0.1)
calorias_input = st.sidebar.number_input("Calorias Ingeridas", step=10)

if st.sidebar.button("Salvar no Google Sheets"):
    if peso_input > 0 and calorias_input > 0:
        with st.spinner("Conectando com o Google..."):
            save_data(data_input, peso_input, calorias_input)
        st.sidebar.success("✅ Salvo na Planilha!")
        
        # Espera 2 segundos e recarrega para mostrar o dado novo
        import time
        time.sleep(1)
        st.rerun()
    else:
        st.sidebar.error("Preencha valores válidos!")

# --- LÓGICA TDEE ---
df = load_data()

# Verifica se tem dados suficientes
if not df.empty and len(df) > 7:
    # Conversão numérica para evitar erros
    df['Peso'] = pd.to_numeric(df['Peso'])
    df['Calorias'] = pd.to_numeric(df['Calorias'])

    df['Media_Peso'] = df['Peso'].rolling(window=7).mean()
    df['Media_Calorias'] = df['Calorias'].rolling(window=7).mean()
    
    recent_df = df.tail(14)
    
    if len(recent_df) >= 7:
        peso_inicial = recent_df.iloc[0]['Media_Peso']
        peso_final = recent_df.iloc[-1]['Media_Peso']
        delta_peso = peso_final - peso_inicial
        media_ingestao = recent_df['Media_Calorias'].mean()
        
        dias = len(recent_df)
        superavit_diario = (delta_peso * 7700) / dias
        tdee_real = media_ingestao - superavit_diario
        status_ia = True
    else:
        status_ia = False
        tdee_real = 0
else:
    status_ia = False
    tdee_real = 0

# --- EXIBIÇÃO ---
col1, col2, col3 = st.columns(3)

if status_ia:
    col1.metric("🔥 TDEE Real (Manutenção)", f"{int(tdee_real)} kcal")
    col2.metric("📉 Para Secar (-0.5kg/sem)", f"{int(tdee_real - 500)} kcal")
    col3.metric("📈 Para Ganhar (+0.25kg/sem)", f"{int(tdee_real + 250)} kcal")
    st.info(f"Análise baseada nos últimos {len(recent_df)} dias de dados.")
else:
    col1.metric("Coletando Dados...", "--")
    st.warning("⚠️ Continue registrando! O sistema precisa de 7 a 14 dias para calibrar.")

st.markdown("---")
if not df.empty:
    st.subheader("📈 Evolução")
    st.line_chart(df.set_index("Data")["Peso"])
    with st.expander("Ver Dados Brutos"):
        st.dataframe(df)
