import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
from datetime import datetime, date

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Dashboard Biohacker", layout="wide")
st.title("🧬 Dashboard Biohacker: Metabolismo & IMC")

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
            cols = ['Passos', 'Proteina', 'Sono', 'Cintura', 'Altura']
            for col in cols:
                if col not in df.columns: df[col] = 0.0
            
            # Converte Data para objeto date (importante para comparação)
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df.sort_values(by="Data")
        except:
            return pd.DataFrame(columns=["Data", "Peso", "Calorias", "Passos", "Proteina", "Sono", "Cintura", "Altura"])
            
    except Exception as e:
        return pd.DataFrame()

# --- SALVAR DADOS (COM ATUALIZAÇÃO INTELIGENTE) ---
def save_data(data_ref, peso, calorias, passos, proteina, sono, cintura, altura):
    repo = get_github_connection()
    if not repo: return

    try:
        # Carrega o arquivo atual do GitHub
        contents = repo.get_contents("dados_dieta.csv")
        csv_string = contents.decoded_content.decode("utf-8")
        df = pd.read_csv(StringIO(csv_string))
        
        # Garante estrutura
        cols = ['Passos', 'Proteina', 'Sono', 'Cintura', 'Altura']
        for col in cols:
            if col not in df.columns: df[col] = 0.0
        
        df['Data'] = pd.to_datetime(df['Data']).dt.date

        # Verifica se a data já existe
        if data_ref in df['Data'].values:
            # ATUALIZA A LINHA EXISTENTE (Overwrite)
            df.loc[df['Data'] == data_ref, ['Peso', 'Calorias', 'Passos', 'Proteina', 'Sono', 'Cintura', 'Altura']] = \
                [peso, calorias, passos, proteina, sono, cintura, altura]
            msg_commit = f"Atualizando registro: {data_ref}"
        else:
            # CRIA UMA NOVA LINHA
            new_row = pd.DataFrame([{
                'Data': data_ref, 'Peso': peso, 'Calorias': calorias, 'Passos': passos,
                'Proteina': proteina, 'Sono': sono, 'Cintura': cintura, 'Altura': altura
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            msg_commit = f"Novo registro: {data_ref}"

        # Salva de volta no GitHub
        output = StringIO()
        df.to_csv(output, index=False)
        repo.update_file("dados_dieta.csv", msg_commit, output.getvalue(), contents.sha)
        
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

# --- INICIALIZAÇÃO E AUTO-PREENCHIMENTO ---
df = load_data()

st.sidebar.header("📝 Diário Inteligente")
# Input de Data
data_selecionada = st.sidebar.date_input("Data", datetime.now())

# --- MÁGICA DO PREENCHIMENTO ---
# Valores padrão (caso seja um dia novo)
defaults = {
    'Peso': 0.0, 'Altura': 1.75, 'Cintura': 0.0,
    'Calorias': 0, 'Proteina': 0, 'Passos': 0, 'Sono': 0.0
}

# Se já existe dado nesse dia, carrega eles nos inputs
dados_do_dia = df[df['Data'] == data_selecionada]
if not dados_do_dia.empty:
    row = dados_do_dia.iloc[0]
    st.sidebar.info("✏️ Editando dados existentes desta data.")
    defaults['Peso'] = float(row['Peso'])
    defaults['Altura'] = float(row['Altura']) if row['Altura'] > 0 else 1.75
    defaults['Cintura'] = float(row['Cintura'])
    defaults['Calorias'] = int(row['Calorias'])
    defaults['Proteina'] = int(row['Proteina'])
    defaults['Passos'] = int(row['Passos'])
    defaults['Sono'] = float(row['Sono'])
else:
    # Se é dia novo, tenta puxar a altura do último registro para facilitar
    if not df.empty and 'Altura' in df.columns:
        ult_altura = df.iloc[-1]['Altura']
        if ult_altura > 0: defaults['Altura'] = float(ult_altura)

# --- FORMULÁRIO ---
st.sidebar.subheader("Biometria")
peso_inp = st.sidebar.number_input("Peso (kg)", value=defaults['Peso'], format="%.2f", step=0.1)
altura_inp = st.sidebar.number_input("Altura (m)", value=defaults['Altura'], format="%.2f", step=0.01)
cintura_inp = st.sidebar.number_input("Cintura (cm)", value=defaults['Cintura'], format="%.1f", step=0.5)

st.sidebar.subheader("Rotina")
calorias_inp = st.sidebar.number_input("Calorias", value=defaults['Calorias'], step=10)
proteina_inp = st.sidebar.number_input("Proteína (g)", value=defaults['Proteina'], step=1)
passos_inp = st.sidebar.number_input("Passos", value=defaults['Passos'], step=100)
sono_inp = st.sidebar.number_input("Horas Sono", value=defaults['Sono'], format="%.1f", step=0.5)

if st.sidebar.button("💾 Salvar / Atualizar"):
    with st.spinner("Atualizando banco de dados..."):
        save_data(data_selecionada, peso_inp, calorias_inp, passos_inp, proteina_inp, sono_inp, cintura_inp, altura_inp)
    st.success("Dados atualizados com sucesso!")
    import time
    time.sleep(1)
    st.rerun()

# --- CÁLCULOS E VISUALIZAÇÃO ---
tdee_real = 0
status_ia = False
ratio_proteina = 0
imc_atual = 0
classif_imc = ""

if not df.empty and len(df) > 7:
    cols = ['Peso', 'Calorias', 'Passos', 'Proteina', 'Sono', 'Cintura', 'Altura']
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
        media_prot = recent[recent['Proteina'] > 0]['Proteina'].mean()
        if pd.notna(media_prot) and peso_atual > 0:
            ratio_proteina = media_prot / peso_atual
            
        altura_atual = recent.iloc[-1]['Altura']
        if altura_atual > 0:
            imc_atual = peso_atual / (altura_atual ** 2)
            if imc_atual < 18.5: classif_imc = "Abaixo do Peso"
            elif imc_atual < 24.9: classif_imc = "Peso Ideal ✅"
            elif imc_atual < 29.9: classif_imc = "Sobrepeso"
            else: classif_imc = "Obesidade"
    else:
        status_ia = False

# --- LAYOUT DASHBOARD ---
st.subheader("⚖️ Análise de Peso Ideal (IMC)")
c1, c2, c3 = st.columns(3)

if imc_atual > 0:
    c1.metric("Seu IMC Atual", f"{imc_atual:.1f}", classif_imc)
    altura_user = df.iloc[-1]['Altura']
    peso_min_ideal = 18.5 * (altura_user ** 2)
    peso_max_ideal = 24.9 * (altura_user ** 2)
    c2.metric("Seu Peso Ideal (Mín)", f"{peso_min_ideal:.1f} kg")
    c3.metric("Seu Peso Ideal (Max)", f"{peso_max_ideal:.1f} kg")
else:
    c1.info("Salve seus dados para calcular o IMC.")

st.markdown("---")

st.subheader("🔥 Metabolismo & Dieta")
k1, k2, k3 = st.columns(3)
if status_ia:
    k1.metric("Gasto Real (TDEE)", f"{int(tdee_real)} kcal")
    k2.metric("Meta Secar", f"{int(tdee_real - 500)} kcal")
    msg_prot = "Baixa"
    if ratio_proteina > 1.6: msg_prot = "Ótima 💪"
    k3.metric("Proteína/kg", f"{ratio_proteina:.1f} g", msg_prot)
else:
    k1.metric("Status", "Coletando dados...")

# --- GRÁFICOS ---
if not df.empty and 'Altura' in df.columns:
    altura_ref = df.iloc[-1]['Altura']
    df['Limite_Min'] = 18.5 * (altura_ref ** 2) if altura_ref > 0 else 0
    df['Limite_Max'] = 24.9 * (altura_ref ** 2) if altura_ref > 0 else 0
    
    tab1, tab2, tab3 = st.tabs(["🎯 Rumo ao Peso Ideal", "💪 Composição (Cintura)", "💤 Sono & Recuperação"])
    
    with tab1:
        st.caption("Acompanhe se seu peso (Azul) está entrando na faixa de peso ideal")
        st.line_chart(df.set_index("Data")[['Peso', 'Limite_Min', 'Limite_Max']], 
                      color=["#0000FF", "#00FF00", "#FF0000"]) 
    
    with tab2:
        st.line_chart(df.set_index("Data")[["Peso", "Cintura"]], color=["#0000FF", "#FFA500"])
        
    with tab3:
        st.bar_chart(df.set_index("Data")[["Calorias", "Proteina"]])

    with st.expander("Ver Tabela Completa"):
        st.dataframe(df.sort_values(by="Data", ascending=False))
