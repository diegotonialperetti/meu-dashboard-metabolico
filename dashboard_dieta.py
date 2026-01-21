import streamlit as st
import pandas as pd
import altair as alt
from github import Github
from io import StringIO
from datetime import datetime, date

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Biohacker Completo", layout="wide")
st.title("🧬 Biohacker: Dashboard Completo (Diário + Circadiano)")

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
            
            # Tratamento de Data e Hora
            df['Timestamp'] = pd.to_datetime(df['Data'])
            df['Data_Ref'] = df['Timestamp'].dt.date # Data pura (sem hora) para agrupamento
            df['Hora'] = df['Timestamp'].dt.hour
            df['Minuto'] = df['Timestamp'].dt.minute
            
            return df.sort_values(by="Timestamp")
        except:
            return pd.DataFrame()
            
    except Exception as e:
        return pd.DataFrame()

# --- SALVAR DADOS ---
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

# --- PROCESSAMENTO INTELIGENTE (AGREGAR POR DIA) ---
def processar_diario(df_raw):
    if df_raw.empty: return pd.DataFrame()
    
    # Agrupa por dia para restaurar os gráficos antigos
    # Lógica: 
    # - Peso, Altura, Cintura: Pega o ÚLTIMO registro do dia (mais atual)
    # - Passos, Calorias, Proteina: Pega o MÁXIMO do dia (assumindo que você vai atualizando o total)
    # - BPM, SpO2, Energia: Pega a MÉDIA do dia (ignorando zeros)
    
    df_daily = df_raw.groupby('Data_Ref').agg({
        'Peso': 'last',
        'Altura': 'last', 
        'Cintura': 'last',
        'Calorias': 'max',
        'Proteina': 'max',
        'Passos': 'max',
        'Sono': 'max',
        'BPM': lambda x: x[x > 0].mean() if not x[x > 0].empty else 0,
        'Energia': lambda x: x[x > 0].mean() if not x[x > 0].empty else 0,
        'SpO2': lambda x: x[x > 0].mean() if not x[x > 0].empty else 0,
        'Pressao_High': 'max'
    }).reset_index()
    
    df_daily.rename(columns={'Data_Ref': 'Data'}, inplace=True)
    return df_daily.sort_values(by="Data")

# --- INICIALIZAÇÃO ---
df_raw = load_data()
df_daily = processar_diario(df_raw) # Cria a versão resumida para os gráficos

st.sidebar.header("⏱️ Registro Pontual")
data_selecionada = st.sidebar.date_input("Data", datetime.now())
hora_selecionada = st.sidebar.time_input("Hora da Leitura", datetime.now().time())

# Defaults inteligentes
defaults = {k: 0.0 for k in ['Peso', 'Altura', 'Cintura', 'Calorias', 'Proteina', 'Passos', 'Sono', 'BPM', 'Energia', 'Pressao_High', 'Pressao_Low', 'SpO2']}
defaults['Altura'] = 1.75
defaults['Energia'] = 5

if not df_daily.empty:
    ult = df_daily.iloc[-1]
    defaults['Peso'] = float(ult['Peso'])
    defaults['Altura'] = float(ult['Altura']) if ult['Altura'] > 0 else 1.75
    defaults['Cintura'] = float(ult['Cintura'])

# --- FORMULÁRIO LATERAL ---
st.sidebar.markdown("### 🫀 Leitura do Anel")
bpm_inp = st.sidebar.number_input("BPM (Neste horário)", value=0, step=1)
spo2_inp = st.sidebar.number_input("SpO2 %", value=0, step=1)
p_high_inp = st.sidebar.number_input("Pressão Alta", value=0)
p_low_inp = st.sidebar.number_input("Pressão Baixa", value=0)

st.sidebar.markdown("### 📝 Dados do Dia")
peso_inp = st.sidebar.number_input("Peso (kg)", value=defaults['Peso'], format="%.2f")
calorias_inp = st.sidebar.number_input("Calorias", value=0, step=10, help="Total do dia até agora")
proteina_inp = st.sidebar.number_input("Proteína (g)", value=0, step=1)
passos_inp = st.sidebar.number_input("Passos", value=0, step=100)
sono_inp = st.sidebar.number_input("Sono (h)", value=0.0, format="%.1f")
energia_inp = st.sidebar.slider("Energia", 1, 10, value=5)
cintura_inp = st.sidebar.hidden_input = defaults['Cintura']
altura_inp = st.sidebar.hidden_input = defaults['Altura']

if st.sidebar.button("💾 Salvar Leitura"):
    with st.spinner("Salvando Ponto..."):
        save_data(data_selecionada, hora_selecionada, peso_inp, calorias_inp, passos_inp, proteina_inp, sono_inp, cintura_inp, altura_inp, bpm_inp, energia_inp, p_high_inp, p_low_inp, spo2_inp)
    st.success("Ponto Registrado! Recarregando...")
    import time
    time.sleep(1)
    st.rerun()

# --- CÁLCULOS METABÓLICOS (Baseados no Diário) ---
tdee_real = 0
status_ia = False
imc_atual = 0
ratio_proteina = 0

if not df_daily.empty and len(df_daily) > 7:
    df_calc = df_daily.copy()
    df_calc['M_Peso'] = df_calc['Peso'].rolling(7).mean()
    df_calc['M_Cals'] = df_calc['Calorias'].rolling(7).mean()
    
    recent = df_calc.tail(14)
    if len(recent) >= 7:
        delta_p = recent.iloc[-1]['M_Peso'] - recent.iloc[0]['M_Peso']
        media_kcal = recent['M_Cals'].mean()
        tdee_real = media_kcal - ((delta_p * 7700) / len(recent))
        status_ia = True
        
        peso_atual = recent.iloc[-1]['Peso']
        altura_atual = recent.iloc[-1]['Altura']
        
        # IMC
        if altura_atual > 0: imc_atual = peso_atual / (altura_atual ** 2)
        
        # Proteína
        media_prot = recent['Proteina'].mean()
        if peso_atual > 0: ratio_proteina = media_prot / peso_atual
    else:
        status_ia = False

# === VISUALIZAÇÃO ===

# 1. Painel de Métricas (Restaurado)
st.subheader("📊 Painel Metabólico Diário")
k1, k2, k3, k4 = st.columns(4)

if status_ia:
    k1.metric("🔥 TDEE (Gasto)", f"{int(tdee_real)} kcal")
    k2.metric("⚖️ IMC Atual", f"{imc_atual:.1f}")
    k3.metric("🍖 Proteína", f"{ratio_proteina:.1f} g/kg")
else:
    k1.metric("Status", "Coletando 7 dias de dados...")

if not df_daily.empty:
    dias_sono = df_daily[df_daily['Sono'] > 0].tail(7)
    val_sono = f"{dias_sono['Sono'].mean():.1f} h" if not dias_sono.empty else "--"
    k4.metric("💤 Sono Médio", val_sono)

st.markdown("---")

# 2. GRÁFICOS DIÁRIOS (Restaurados)
if not df_daily.empty and 'Altura' in df_daily.columns:
    altura_ref = df_daily.iloc[-1]['Altura']
    df_daily['Limite_Min'] = 18.5 * (altura_ref ** 2) if altura_ref > 0 else 0
    df_daily['Limite_Max'] = 24.9 * (altura_ref ** 2) if altura_ref > 0 else 0
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎯 Peso & IMC", "💪 Cintura", "⚡ Energia & Passos", "❤️ Coração (Média)", "🕒 Ritmo Circadiano (Novo)"])
    
    with tab1:
        st.line_chart(df_daily.set_index("Data")[['Peso', 'Limite_Min', 'Limite_Max']], 
                      color=["#0000FF", "#00FF00", "#FF0000"]) 
    
    with tab2:
        df_cint = df_daily[df_daily['Cintura'] > 0]
        if not df_cint.empty:
            st.line_chart(df_cint.set_index("Data")["Cintura"], color="#FFA500")
            
    with tab3:
        st.bar_chart(df_daily.set_index("Data")[["Calorias", "Proteina"]])
        
    with tab4:
        # Gráfico Média Diária de BPM vs Sono
        df_saude = df_daily[(df_daily['BPM'] > 0) & (df_daily['Sono'] > 0)]
        if not df_saude.empty:
            st.line_chart(df_saude.set_index("Data")[["BPM", "Sono"]], color=["#FF0000", "#0000FF"])
        else:
            st.info("Falta dados coincidentes de BPM e Sono.")

    # 3. GRÁFICO CIRCADIANO (Mantido da v10)
    with tab5:
        st.caption("Raio-X das 24h: Veja como seu coração se comporta ao longo do dia")
        if not df_raw.empty:
            df_bpm = df_raw[df_raw['BPM'] > 0].copy()
            if not df_bpm.empty:
                df_bpm['Hora_Decimal'] = df_bpm['Hora'] + (df_bpm['Minuto'] / 60)
                
                scatter = alt.Chart(df_bpm).mark_circle(size=60).encode(
                    x=alt.X('Hora_Decimal', title='Hora (0h-24h)', scale=alt.Scale(domain=[0, 24])),
                    y=alt.Y('BPM', scale=alt.Scale(domain=[30, 180])),
                    color=alt.Color('Data_Ref', legend=None),
                    tooltip=['Data_Ref', 'Hora', 'BPM']
                ).interactive()

                line = scatter.transform_loess('Hora_Decimal', 'BPM').mark_line(color='red', size=4)
                st.altair_chart(scatter + line, use_container_width=True)
            else:
                st.write("Sem dados de BPM ainda.")

    with st.expander("Ver Tabela Diária Agregada"):
        st.dataframe(df_daily.sort_values(by="Data", ascending=False))
