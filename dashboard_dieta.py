import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
from datetime import datetime, date

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Dashboard Biohacker Pro", layout="wide")
st.title("🧬 Dashboard Biohacker: Performance & Recuperação")

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
            
            # Garante colunas novas (BPM e Energia)
            cols = ['Passos', 'Proteina', 'Sono', 'Cintura', 'Altura', 'BPM', 'Energia']
            for col in cols:
                if col not in df.columns: df[col] = 0.0
            
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df.sort_values(by="Data")
        except:
            return pd.DataFrame(columns=["Data", "Peso", "Calorias", "Passos", "Proteina", "Sono", "Cintura", "Altura", "BPM", "Energia"])
            
    except Exception as e:
        return pd.DataFrame()

# --- SALVAR DADOS ---
def save_data(data_ref, peso, calorias, passos, proteina, sono, cintura, altura, bpm, energia):
    repo = get_github_connection()
    if not repo: return

    try:
        contents = repo.get_contents("dados_dieta.csv")
        csv_string = contents.decoded_content.decode("utf-8")
        df = pd.read_csv(StringIO(csv_string))
        
        cols = ['Passos', 'Proteina', 'Sono', 'Cintura', 'Altura', 'BPM', 'Energia']
        for col in cols:
            if col not in df.columns: df[col] = 0.0
        
        df['Data'] = pd.to_datetime(df['Data']).dt.date

        if data_ref in df['Data'].values:
            # Atualiza linha existente
            df.loc[df['Data'] == data_ref, ['Peso', 'Calorias', 'Passos', 'Proteina', 'Sono', 'Cintura', 'Altura', 'BPM', 'Energia']] = \
                [peso, calorias, passos, proteina, sono, cintura, altura, bpm, energia]
            msg_commit = f"Update registro: {data_ref}"
        else:
            # Cria nova linha
            new_row = pd.DataFrame([{
                'Data': data_ref, 'Peso': peso, 'Calorias': calorias, 'Passos': passos,
                'Proteina': proteina, 'Sono': sono, 'Cintura': cintura, 'Altura': altura,
                'BPM': bpm, 'Energia': energia
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            msg_commit = f"Novo registro: {data_ref}"

        output = StringIO()
        df.to_csv(output, index=False)
        repo.update_file("dados_dieta.csv", msg_commit, output.getvalue(), contents.sha)
        
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

# --- INICIALIZAÇÃO ---
df = load_data()

st.sidebar.header("📝 Diário Inteligente")
data_selecionada = st.sidebar.date_input("Data", datetime.now())

# Valores padrão
defaults = {
    'Peso': 0.0, 'Altura': 1.75, 'Cintura': 0.0,
    'Calorias': 0, 'Proteina': 0, 'Passos': 0, 'Sono': 0.0,
    'BPM': 0, 'Energia': 5
}

# Auto-preenchimento (Edição)
dados_do_dia = df[df['Data'] == data_selecionada]
if not dados_do_dia.empty:
    row = dados_do_dia.iloc[0]
    st.sidebar.info("✏️ Editando dia existente.")
    defaults['Peso'] = float(row['Peso'])
    defaults['Altura'] = float(row['Altura']) if row['Altura'] > 0 else 1.75
    defaults['Cintura'] = float(row['Cintura'])
    defaults['Calorias'] = int(row['Calorias'])
    defaults['Proteina'] = int(row['Proteina'])
    defaults['Passos'] = int(row['Passos'])
    defaults['Sono'] = float(row['Sono'])
    defaults['BPM'] = int(row['BPM'])
    defaults['Energia'] = int(row['Energia'])
else:
    if not df.empty and 'Altura' in df.columns:
        ult_altura = df.iloc[-1]['Altura']
        if ult_altura > 0: defaults['Altura'] = float(ult_altura)

# --- INPUTS ---
st.sidebar.subheader("Biometria & Anel")
peso_inp = st.sidebar.number_input("Peso (kg)", value=defaults['Peso'], format="%.2f", step=0.1)
altura_inp = st.sidebar.number_input("Altura (m)", value=defaults['Altura'], format="%.2f", step=0.01)
cintura_inp = st.sidebar.number_input("Cintura (cm)", value=defaults['Cintura'], format="%.1f", step=0.5)
bpm_inp = st.sidebar.number_input("BPM Repouso ❤️", value=defaults['BPM'], step=1, help="Olhe no app do anel")

st.sidebar.subheader("Rotina & Feeling")
calorias_inp = st.sidebar.number_input("Calorias", value=defaults['Calorias'], step=10)
proteina_inp = st.sidebar.number_input("Proteína (g)", value=defaults['Proteina'], step=1)
passos_inp = st.sidebar.number_input("Passos", value=defaults['Passos'], step=100)
sono_inp = st.sidebar.number_input("Horas Sono", value=defaults['Sono'], format="%.1f", step=0.5)
energia_inp = st.sidebar.slider("Nível de Energia ⚡", 1, 10, value=defaults['Energia'], help="1=Morto, 10=Super Saiyan")

if st.sidebar.button("💾 Salvar Dados"):
    with st.spinner("Processando..."):
        save_data(data_selecionada, peso_inp, calorias_inp, passos_inp, proteina_inp, sono_inp, cintura_inp, altura_inp, bpm_inp, energia_inp)
    st.success("Salvo com sucesso!")
    import time
    time.sleep(1)
    st.rerun()

# --- CÁLCULOS ---
tdee_real = 0
status_ia = False
ratio_proteina = 0
imc_atual = 0
classif_imc = ""

if not df.empty and len(df) > 7:
    cols = ['Peso', 'Calorias', 'Passos', 'Proteina', 'Sono', 'Cintura', 'Altura', 'BPM', 'Energia']
    for c in cols: df[c] = pd.to_numeric(df[c])

    df['M_Peso'] = df['Peso'].rolling(7).mean()
    df['M_Cals'] = df['Calorias'].rolling(7).mean()
    
    recent = df.tail(14)
    if len(recent) >= 7:
        delta_p = recent.iloc[-1]['M_Peso'] - recent.iloc[0]['M_Peso']
        media_kcal = recent['M_Cals'].mean()
        tdee_real = media_kcal - ((delta_p * 7700) / len(recent))
        status_ia = True
        
        peso_atual = recent.iloc[-1]['Peso']
        # Proteína
        media_prot = recent[recent['Proteina'] > 0]['Proteina'].mean()
        if pd.notna(media_prot) and peso_atual > 0: ratio_proteina = media_prot / peso_atual
        
        # IMC
        altura_atual = recent.iloc[-1]['Altura']
        if altura_atual > 0:
            imc_atual = peso_atual / (altura_atual ** 2)
            if imc_atual < 18.5: classif_imc = "Abaixo do Peso"
            elif imc_atual < 24.9: classif_imc = "Peso Ideal ✅"
            elif imc_atual < 29.9: classif_imc = "Sobrepeso"
            else: classif_imc = "Obesidade"
    else:
        status_ia = False

# --- LAYOUT VISUAL ---
st.subheader("📊 Resumo Vital")
k1, k2, k3, k4 = st.columns(4)

if status_ia:
    k1.metric("🔥 Gasto Diário", f"{int(tdee_real)} kcal")
    k2.metric("🍖 Proteína/kg", f"{ratio_proteina:.1f} g")
else:
    k1.metric("Status", "Coletando...")

# Novas Métricas de Recuperação
if not df.empty:
    # BPM
    dias_bpm = df[df['BPM'] > 30].tail(7) # Filtra zeros
    if not dias_bpm.empty:
        media_bpm = int(dias_bpm['BPM'].mean())
        k3.metric("❤️ BPM Médio (7d)", f"{media_bpm} bpm", help="Menor é melhor (Condicionamento)")
    else:
        k3.metric("❤️ BPM", "--")
        
    # Energia
    media_energia = df.tail(7)['Energia'].mean()
    k4.metric("⚡ Energia Média", f"{media_energia:.1f}/10")

st.markdown("---")

# --- GRÁFICOS POWER ---
if not df.empty and 'Altura' in df.columns:
    altura_ref = df.iloc[-1]['Altura']
    df['Limite_Min'] = 18.5 * (altura_ref ** 2) if altura_ref > 0 else 0
    df['Limite_Max'] = 24.9 * (altura_ref ** 2) if altura_ref > 0 else 0
    
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Peso & IMC", "💪 Cintura", "❤️ Coração & Sono", "⚡ Energia vs Dieta"])
    
    with tab1:
        st.caption("Mantenha a linha Azul entre a Verde e a Vermelha")
        st.line_chart(df.set_index("Data")[['Peso', 'Limite_Min', 'Limite_Max']], 
                      color=["#0000FF", "#00FF00", "#FF0000"]) 
    
    with tab2:
        st.line_chart(df.set_index("Data")[["Peso", "Cintura"]], color=["#0000FF", "#FFA500"])
        
    with tab3:
        st.caption("BPM caindo e Sono estável = Condicionamento Físico melhorando")
        st.line_chart(df.set_index("Data")[["BPM", "Sono"]], color=["#FF0000", "#0000FF"])

    with tab4:
        st.caption("Será que comer mais (Calorias) te dá mais Energia no dia seguinte?")
        st.line_chart(df.set_index("Data")[["Energia", "Calorias"]], color=["#FFA500", "#808080"])

    with st.expander("Ver Banco de Dados Completo"):
        st.dataframe(df.sort_values(by="Data", ascending=False))
