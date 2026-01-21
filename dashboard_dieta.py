import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from github import Github
from io import StringIO
from datetime import datetime, date, time

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Biohacker Circadiano", layout="wide")
st.title("🧬 Biohacker: Análise de Ritmo Circadiano (24h)")

# --- CONEXÃO GITHUB ---
def get_github_connection():
    try:
        token = st.secrets["github"]["token"]
        g = Github(token)
        repo_name = "diegotonialperetti/meu-dashboard-metabolico" 
        repo = g.get_repo(repo_name)
        return repo
    except Exception as e:
        st.error(f"Erro Github: {e}")
        return None

# --- CARREGAR DADOS ---
def load_data():
    try:
        repo = get_github_connection()
        if not repo: return pd.DataFrame()

        try:
            contents = repo.get_contents("dados_dieta.csv")
            csv_string = contents.decoded_content.decode("utf-8")
            df = pd.read_csv(StringIO(csv_string))
            
            # Colunas necessárias
            cols = ['Passos', 'Proteina', 'Sono', 'Cintura', 'Altura', 'BPM', 'Energia', 'Pressao_High', 'Pressao_Low', 'SpO2']
            for col in cols:
                if col not in df.columns: df[col] = 0.0
            
            # Tenta converter Data para datetime completo (Data + Hora)
            # Se for formato antigo (só data), ele põe hora 00:00
            df['Timestamp'] = pd.to_datetime(df['Data'])
            df['Data_So'] = df['Timestamp'].dt.date
            df['Hora'] = df['Timestamp'].dt.hour
            df['Minuto'] = df['Timestamp'].dt.minute
            
            return df.sort_values(by="Timestamp")
        except:
            return pd.DataFrame(columns=["Data", "Peso", "Calorias", "BPM", "SpO2", "Pressao_High", "Pressao_Low"])
            
    except Exception as e:
        return pd.DataFrame()

# --- SALVAR DADOS (COM HORA) ---
def save_data(data_ref, hora_ref, peso, calorias, passos, proteina, sono, cintura, altura, bpm, energia, p_high, p_low, spo2):
    repo = get_github_connection()
    if not repo: return

    try:
        contents = repo.get_contents("dados_dieta.csv")
        csv_string = contents.decoded_content.decode("utf-8")
        df = pd.read_csv(StringIO(csv_string))
        
        # Garante colunas
        cols_check = ['Passos', 'Proteina', 'Sono', 'Cintura', 'Altura', 'BPM', 'Energia', 'Pressao_High', 'Pressao_Low', 'SpO2']
        for col in cols_check:
            if col not in df.columns: df[col] = 0.0
            
        # Cria String de Data+Hora
        str_datetime = f"{data_ref} {hora_ref.strftime('%H:%M:%S')}"
        
        # Cria nova linha
        new_row = pd.DataFrame([{
            'Data': str_datetime, 
            'Peso': peso, 'Calorias': calorias, 'Passos': passos,
            'Proteina': proteina, 'Sono': sono, 'Cintura': cintura, 'Altura': altura,
            'BPM': bpm, 'Energia': energia, 
            'Pressao_High': p_high, 'Pressao_Low': p_low, 'SpO2': spo2
        }])
        
        df = pd.concat([df, new_row], ignore_index=True)
        msg_commit = f"Registro: {str_datetime}"

        output = StringIO()
        df.to_csv(output, index=False)
        repo.update_file("dados_dieta.csv", msg_commit, output.getvalue(), contents.sha)
        
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

# --- INICIALIZAÇÃO ---
df = load_data()

st.sidebar.header("⏱️ Registro Pontual")
data_selecionada = st.sidebar.date_input("Data", datetime.now())
hora_selecionada = st.sidebar.time_input("Hora da Leitura", datetime.now().time())

# Tenta pegar defaults do último registro geral (para facilitar)
defaults = {k: 0.0 for k in ['Peso', 'Altura', 'Cintura', 'Calorias', 'Proteina', 'Passos', 'Sono', 'BPM', 'Energia', 'Pressao_High', 'Pressao_Low', 'SpO2']}
defaults['Altura'] = 1.75
defaults['Energia'] = 5

if not df.empty:
    ult = df.iloc[-1]
    # Puxa dados que geralmente não mudam no dia (Peso, Altura)
    defaults['Peso'] = float(ult['Peso'])
    defaults['Altura'] = float(ult['Altura']) if ult['Altura'] > 0 else 1.75
    defaults['Cintura'] = float(ult['Cintura'])

# --- FORMULÁRIO ---
st.sidebar.markdown("### 🫀 Leitura do Anel")
bpm_inp = st.sidebar.number_input("BPM (Neste horário)", value=0, step=1, help="Ex: 49 as 03:30")
spo2_inp = st.sidebar.number_input("SpO2 %", value=0, step=1)
p_high_inp = st.sidebar.number_input("Pressão Alta", value=0)
p_low_inp = st.sidebar.number_input("Pressão Baixa", value=0)

st.sidebar.markdown("### 📝 Dados do Dia (Opcional)")
st.sidebar.caption("Preencha só se quiser atualizar o dia")
peso_inp = st.sidebar.number_input("Peso (kg)", value=defaults['Peso'], format="%.2f")
calorias_inp = st.sidebar.number_input("Calorias", value=0, step=10)
proteina_inp = st.sidebar.number_input("Proteína (g)", value=0, step=1)
passos_inp = st.sidebar.number_input("Passos", value=0, step=100)
sono_inp = st.sidebar.number_input("Sono (h)", value=0.0, format="%.1f")
energia_inp = st.sidebar.slider("Energia", 1, 10, value=5)
cintura_inp = st.sidebar.hidden_input = defaults['Cintura']
altura_inp = st.sidebar.hidden_input = defaults['Altura']

if st.sidebar.button("💾 Salvar Leitura"):
    with st.spinner("Salvando Ponto..."):
        save_data(data_selecionada, hora_selecionada, peso_inp, calorias_inp, passos_inp, proteina_inp, sono_inp, cintura_inp, altura_inp, bpm_inp, energia_inp, p_high_inp, p_low_inp, spo2_inp)
    st.success("Ponto Registrado!")
    import time
    time.sleep(1)
    st.rerun()

# --- ANÁLISE ---
st.subheader("🕑 Seu Coração nas 24 Horas")

if not df.empty:
    # Filtra apenas dados com BPM > 0
    df_bpm = df[df['BPM'] > 0].copy()
    
    if not df_bpm.empty:
        # Criação do Gráfico Circadiano
        # Eixo X = Hora do dia (decimal para ficar contínuo, ex: 3h30 = 3.5)
        df_bpm['Hora_Decimal'] = df_bpm['Hora'] + (df_bpm['Minuto'] / 60)
        
        # Gráfico de Dispersão (Pontos)
        scatter = alt.Chart(df_bpm).mark_circle(size=60).encode(
            x=alt.X('Hora_Decimal', title='Hora do Dia (0h - 24h)', scale=alt.Scale(domain=[0, 24])),
            y=alt.Y('BPM', title='Batimentos', scale=alt.Scale(domain=[30, 180])),
            color=alt.Color('Data_So', legend=None), # Cores diferentes por dia
            tooltip=['Data_So', 'Hora', 'Minuto', 'BPM']
        ).interactive()

        # Linha de Tendência (Média Geral por Horário)
        line = scatter.transform_loess(
            'Hora_Decimal', 'BPM', bandwidth=0.2
        ).mark_line(color='red', size=4).encode(
            opacity=alt.value(1)
        )

        st.altair_chart(scatter + line, use_container_width=True)
        st.info("🔴 A linha VERMELHA mostra o seu padrão normal. As bolinhas são suas leituras.")
        
        # Estatísticas por Turno
        st.write("#### 📊 Média por Turno")
        col1, col2, col3 = st.columns(3)
        
        madrugada = df_bpm[(df_bpm['Hora'] >= 0) & (df_bpm['Hora'] < 6)]
        dia = df_bpm[(df_bpm['Hora'] >= 6) & (df_bpm['Hora'] < 18)]
        noite = df_bpm[(df_bpm['Hora'] >= 18)]
        
        if not madrugada.empty: col1.metric("Madrugada (Sono)", f"{int(madrugada['BPM'].mean())} bpm", f"Mínimo: {int(madrugada['BPM'].min())}")
        if not dia.empty: col2.metric("Dia (Ativo)", f"{int(dia['BPM'].mean())} bpm")
        if not noite.empty: col3.metric("Noite (Repouso)", f"{int(noite['BPM'].mean())} bpm")

    else:
        st.warning("Adicione leituras de BPM com horários diferentes para gerar o gráfico.")

st.markdown("---")

# --- DASHBOARD DIÁRIO (AGREGADO) ---
st.subheader("📆 Resumo Diário")

# Agrupa dados por dia (Média do dia)
if not df.empty:
    df_daily = df.groupby('Data_So').agg({
        'Peso': lambda x: x[x > 0].mean() if not x[x > 0].empty else 0,
        'Calorias': 'sum', # Calorias soma
        'Proteina': 'sum', # Proteina soma
        'Passos': 'max',   # Passos pega o máximo do dia
        'Sono': 'max',     # Sono pega o máximo do dia
        'Pressao_High': 'max',
        'SpO2': 'mean'
    }).reset_index()
    
    df_daily.rename(columns={'Data_So': 'Data'}, inplace=True)
    df_daily = df_daily.sort_values(by="Data", ascending=False)
    
    st.dataframe(df_daily.head(7))
