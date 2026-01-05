import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# Configurações da Página
st.set_page_config(page_title="Dashboard Metabólico AI", layout="wide")
st.title("📊 Seu Dashboard Metabólico Inteligente")

# Arquivo para salvar os dados (banco de dados simples)
DATA_FILE = "dados_dieta.csv"

# Função para carregar dados
def load_data():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame(columns=["Data", "Peso", "Calorias"])
    try:
        df = pd.read_csv(DATA_FILE)
        df['Data'] = pd.to_datetime(df['Data']).dt.date
        return df.sort_values(by="Data")
    except Exception as e:
        return pd.DataFrame(columns=["Data", "Peso", "Calorias"])

# Função para salvar dados
def save_data(date, peso, calorias):
    df = load_data()
    new_data = pd.DataFrame({"Data": [date], "Peso": [peso], "Calorias": [calorias]})
    
    # Se já existir registro no dia, atualiza
    if date in df['Data'].values:
        df.loc[df['Data'] == date, ['Peso', 'Calorias']] = [peso, calorias]
    else:
        df = pd.concat([df, new_data], ignore_index=True)
    
    df.to_csv(DATA_FILE, index=False)
    return df

# --- BARRA LATERAL: Entrada de Dados ---
st.sidebar.header("📝 Registro Diário")
data_input = st.sidebar.date_input("Data", datetime.now())
peso_input = st.sidebar.number_input("Peso Hoje (kg)", format="%.2f", step=0.1)
calorias_input = st.sidebar.number_input("Calorias Ingeridas", step=10)

if st.sidebar.button("Salvar Registro"):
    if peso_input > 0 and calorias_input > 0:
        save_data(data_input, peso_input, calorias_input)
        st.sidebar.success("Dados salvos com sucesso!")
    else:
        st.sidebar.error("Insira valores válidos.")

# --- LÓGICA DA INTELIGÊNCIA (CÁLCULO DE TDEE) ---
df = load_data()

if len(df) > 7: # Precisa de pelo menos uma semana para começar a "inteligência"
    # Cálculo de Médias Móveis (7 dias) para suavizar flutuações de água
    df['Media_Peso'] = df['Peso'].rolling(window=7).mean()
    df['Media_Calorias'] = df['Calorias'].rolling(window=7).mean()
    
    # Pega os dados mais recentes (últimos 14 dias para análise de tendência)
    recent_df = df.tail(14)
    
    if len(recent_df) >= 7:
        # Variação de peso na quinzena
        peso_inicial = recent_df.iloc[0]['Media_Peso']
        peso_final = recent_df.iloc[-1]['Media_Peso']
        delta_peso = peso_final - peso_inicial
        
        # Média de calorias ingeridas no período
        media_ingestao = recent_df['Media_Calorias'].mean()
        
        # Fator de conversão: 7700kcal = 1kg
        # Se delta_peso > 0, comeu acima da manutenção. Se < 0, comeu abaixo.
        # Dias decorridos
        dias = len(recent_df)
        
        # Cálculo do Gasto Calórico Diário Real (TDEE)
        # TDEE = Ingestão - (Mudança_Peso_kg * 7700 / dias)
        superavit_total = delta_peso * 7700
        superavit_diario = superavit_total / dias
        tdee_real = media_ingestao - superavit_diario
        
        status_ia = True
    else:
        status_ia = False
        tdee_real = 0
else:
    status_ia = False
    tdee_real = 0

# --- DASHBOARD PRINCIPAL ---

col1, col2, col3 = st.columns(3)

# Exibição dos Cartões
if status_ia:
    col1.metric(label="🔥 TDEE (Manutenção Real)", value=f"{int(tdee_real)} kcal", delta="Calculado por IA")
    col2.metric(label="📉 Para Secar (-0.5kg/sem)", value=f"{int(tdee_real - 500)} kcal")
    col3.metric(label="📈 Para Ganhar (+0.25kg/sem)", value=f"{int(tdee_real + 250)} kcal")
    
    st.info(f"Baseado na análise dos seus últimos {len(recent_df)} dias, seu metabolismo está gastando aprox. **{int(tdee_real)}** calorias por dia.")
else:
    col1.metric(label="Dados Insuficientes", value="--")
    st.warning("⚠️ O sistema precisa de pelo menos 7 a 14 dias de dados contínuos para calcular seu metabolismo com precisão.")

# --- GRÁFICOS ---
st.markdown("---")
st.subheader("📈 Evolução Visual")

if not df.empty:
    chart_data = df.set_index("Data")[["Peso", "Calorias"]]
    
    # Gráfico de Peso
    st.line_chart(df.set_index("Data")["Peso"])
    
    # Tabela de Histórico
    with st.expander("Ver Histórico Completo"):
        st.dataframe(df.sort_values(by="Data", ascending=False))
else:
    st.write("Comece a inserir dados na barra lateral.")