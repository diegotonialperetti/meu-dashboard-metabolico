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
            
            # Garante colunas
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
            df.loc[df['Data'] == data_ref, ['Peso', 'Calorias', 'Passos', 'Proteina', 'Sono', 'Cintura', 'Altura', 'BPM', 'Energia']] = \
                [peso, calorias, passos, proteina, sono, cintura, altura, bpm, energia]
            msg_commit = f"Update registro: {data_ref}"
        else:
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

# Auto-preenchimento
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
st.sidebar.subheader("Biometria")
peso_inp = st.sidebar.number_input("Peso (kg)", value=defaults['Peso'], format="%.2f", step=0.1)
altura_inp = st.sidebar.number_input("Altura (m)", value=defaults['Altura'], format="%.2f", step=0.01)
cintura_inp = st.sidebar.number_input("Cintura (cm)", value=defaults['Cintura'], format="%.1f", step=0.5)

st.sidebar.subheader("Rotina Diária")
col_s1, col_s2 = st.sidebar.columns(2)
with col_s1:
    calorias_inp = st.number_input("Calorias", value=defaults['Calorias'], step=10)
    passos_inp = st.number_input("Passos", value=defaults['Passos'], step=100)
    bpm_inp = st.number_input("BPM ❤️", value=defaults['BPM'], step=1)
with col_s2:
    proteina_inp = st.number_input("Proteína (g)", value=defaults['Proteina'], step=1)
    sono_inp = st.number_input("Sono (h)", value=defaults['Sono'], format="%.1f", step=0.5)
    energia_inp = st.slider("Energia ⚡", 1, 10, value=defaults['Energia'])

if st.sidebar.button("💾 Salvar Dados"):
    with st.spinner("Processando..."):
        save_data(data_selecionada, peso_inp, calorias_inp, passos_inp, proteina_inp, sono_inp, cintura_inp, altura_inp, bpm_inp, energia_inp)
    st.success("Salvo com sucesso!")
    import time
    time.sleep(1)
    st.rerun()

# --- CÁLCULOS GLOBAIS ---
tdee_real = 0
status_ia = False
ratio_proteina = 0
imc_atual = 0
classif_imc = ""

if not df.empty and len(df) > 7:
    cols = ['Peso', 'Calorias', 'Passos', 'Proteina', 'Sono', 'Cintura', 'Altura', 'BPM', 'Energia']
    for c in cols: df[c] = pd.to_numeric(df[c])

    # Médias Móveis para TDEE (Aqui não filtramos zero pois TDEE precisa da continuidade dos dias)
    df['M_Peso'] = df['Peso'].rolling(7).mean()
    df['M_Cals'] = df['Calorias'].rolling(7).mean()
    
    recent = df.tail(14)
    if len(recent) >= 7:
        delta_p = recent.iloc[-1]['M_Peso'] - recent.iloc[0]['M_Peso']
        media_kcal = recent['M_Cals'].mean()
        tdee_real = media_kcal - ((delta_p * 7700) / len(recent))
        status_ia = True
        
        peso_atual = recent.iloc[-1]['Peso']
        
        # Proteína (Filtra Zeros)
        dias_com_prot = recent[recent['Proteina'] > 0]
        media_prot = dias_com_prot['Proteina'].mean() if not dias_com_prot.empty else 0
        if peso_atual > 0: ratio_proteina = media_prot / peso_atual
        
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
st.subheader("📊 Painel de Controle Metabólico")
col1, col2, col3, col4 = st.columns(4)

if status_ia:
    col1.metric("🔥 TDEE (Gasto)", f"{int(tdee_real)} kcal", f"Meta: {int(tdee_real - 500)}")
    col2.metric("🍖 Proteína Média", f"{ratio_proteina:.1f} g/kg", "Considerando dias registrados")
else:
    col1.metric("Status", "Coletando...")

# --- MÉTRICAS INTELIGENTES (FILTRO DE ZEROS) ---
if not df.empty:
    # SONO
    dias_sono = df[df['Sono'] > 0].tail(7)
    val_sono = f"{dias_sono['Sono'].mean():.1f} h" if not dias_sono.empty else "--"
    col3.metric("💤 Sono Médio", val_sono)
    
    # PASSOS
    dias_passos = df[df['Passos'] > 0].tail(7)
    val_passos = f"{int(dias_passos['Passos'].mean())}" if not dias_passos.empty else "--"
    col4.metric("👣 Passos Médios", val_passos)

# Linha 2 de Métricas
c1, c2, c3, c4 = st.columns(4)
if not df.empty:
    # BPM
    dias_bpm = df[df['BPM'] > 0].tail(7)
    val_bpm = f"{int(dias_bpm['BPM'].mean())} bpm" if not dias_bpm.empty else "--"
    c1.metric("❤️ BPM Repouso", val_bpm)
    
    # ENERGIA
    dias_energia = df[df['Energia'] > 0].tail(7)
    val_energia = f"{dias_energia['Energia'].mean():.1f}/10" if not dias_energia.empty else "--"
    c2.metric("⚡ Energia Média", val_energia)
    
    # IMC
    if imc_atual > 0:
        c3.metric("⚖️ IMC Atual", f"{imc_atual:.1f}", classif_imc)
        altura_ref = df.iloc[-1]['Altura']
        peso_ideal = 21.7 * (altura_ref ** 2) # Media do IMC ideal
        c4.metric("🎯 Alvo (IMC 21.7)", f"{peso_ideal:.1f} kg", f"Faltam {peso_atual - peso_ideal:.1f} kg")

st.markdown("---")

# --- GRÁFICOS (COM FILTRO VISUAL) ---
if not df.empty and 'Altura' in df.columns:
    altura_ref = df.iloc[-1]['Altura']
    df['Limite_Min'] = 18.5 * (altura_ref ** 2) if altura_ref > 0 else 0
    df['Limite_Max'] = 24.9 * (altura_ref ** 2) if altura_ref > 0 else 0
    
    tab1, tab2, tab3, tab4 = st.tabs(["🎯 Peso & IMC", "💪 Cintura & Proteína", "❤️ Coração & Sono", "⚡ Energia & Passos"])
    
    with tab1:
        st.line_chart(df.set_index("Data")[['Peso', 'Limite_Min', 'Limite_Max']], 
                      color=["#0000FF", "#00FF00", "#FF0000"]) 
    
    with tab2:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.caption("Evolução da Cintura (Ignorando dias não medidos)")
            # Filtra Zeros para o gráfico não cair
            df_cintura = df[df['Cintura'] > 0]
            if not df_cintura.empty:
                st.line_chart(df_cintura.set_index("Data")["Cintura"], color="#FFA500")
            else:
                st.info("Sem dados de cintura.")
        with col_g2:
            st.caption("Ingestão de Proteína")
            st.bar_chart(df.set_index("Data")["Proteina"], color="#00FF00")
        
    with tab3:
        st.caption("BPM (Vermelho) vs Sono (Azul) - Dias sem registro são ignorados")
        # Cria um dataframe apenas com dados válidos para o gráfico ficar bonito
        df_saude = df[(df['BPM'] > 0) & (df['Sono'] > 0)]
        if not df_saude.empty:
            st.line_chart(df_saude.set_index("Data")[["BPM", "Sono"]], color=["#FF0000", "#0000FF"])
        else:
            st.info("Preencha BPM e Sono no mesmo dia para ver a correlação.")

    with tab4:
        df_energia = df[df['Energia'] > 0]
        if not df_energia.empty:
            st.line_chart(df_energia.set_index("Data")[["Energia", "Passos"]], color=["#FFA500", "#808080"])
        else:
            st.info("Sem dados de energia.")

    with st.expander("Ver Banco de Dados Completo"):
        st.dataframe(df.sort_values(by="Data", ascending=False))
