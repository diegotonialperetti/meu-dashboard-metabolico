import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
from datetime import datetime

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Dashboard Biohacker", layout="wide")
st.title("🧬 Dashboard Biohacker: Metabolismo & IMC")

# --- CONEXÃO GITHUB ---
def get_github_connection():
    try:
        token = st.secrets["github"]["token"]
        g = Github(token)
        repo_name = "diegotonialperetti/meu-dashboard-metabolico" # CONFIRA SEU REPO
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
            
            # Garante colunas novas (Altura)
            cols_obrigatorias = ['Passos', 'Proteina', 'Sono', 'Cintura', 'Altura']
            for col in cols_obrigatorias:
                if col not in df.columns:
                    df[col] = 0.0
            
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df.sort_values(by="Data")
        except:
            return pd.DataFrame(columns=["Data", "Peso", "Calorias", "Passos", "Proteina", "Sono", "Cintura", "Altura"])
            
    except Exception as e:
        return pd.DataFrame()

# --- SALVAR DADOS ---
def save_data(date, peso, calorias, passos, proteina, sono, cintura, altura):
    repo = get_github_connection()
    if not repo: return

    date_str = date.strftime("%Y-%m-%d")
    new_line = f"{date_str},{peso},{calorias},{passos},{proteina},{sono},{cintura},{altura}\n"

    try:
        contents = repo.get_contents("dados_dieta.csv")
        current_data = contents.decoded_content.decode("utf-8")
        
        # Reconstrói CSV se faltar coluna Altura (compatibilidade)
        if "Altura" not in current_data.split('\n')[0]:
            df = pd.read_csv(StringIO(current_data))
            if 'Altura' not in df.columns: df['Altura'] = 0.0
            # Adiciona a linha nova via pandas para garantir estrutura
            df_new = pd.DataFrame([[date_str, peso, calorias, passos, proteina, sono, cintura, altura]], 
                                  columns=df.columns)
            # Salva tudo
            df_final = pd.concat([df, df_new], ignore_index=True)
            output = StringIO()
            df_final.to_csv(output, index=False)
            updated_data = output.getvalue()
        else:
            updated_data = current_data.strip() + '\n' + new_line

        repo.update_file("dados_dieta.csv", f"Registro: {date_str}", updated_data, contents.sha)
        
    except:
        header = "Data,Peso,Calorias,Passos,Proteina,Sono,Cintura,Altura\n"
        repo.create_file("dados_dieta.csv", "Criando DB V5", header + new_line)

# --- INICIALIZAÇÃO ---
df = load_data()

# Pega a última altura registrada para preencher o campo automaticamente
last_height = 1.75 # Valor padrão
if not df.empty and 'Altura' in df.columns:
    ultimo_val = df.iloc[-1]['Altura']
    if ultimo_val > 0:
        last_height = float(ultimo_val)

# --- SIDEBAR ---
st.sidebar.header("📝 Diário Completo")
data_inp = st.sidebar.date_input("Data", datetime.now())

# Campos Biométricos
st.sidebar.subheader("Biometria")
peso_inp = st.sidebar.number_input("Peso (kg)", format="%.2f", step=0.1)
altura_inp = st.sidebar.number_input("Altura (m)", format="%.2f", step=0.01, value=last_height)
cintura_inp = st.sidebar.number_input("Cintura (cm)", format="%.1f", step=0.5)

# Campos Diários
st.sidebar.subheader("Rotina")
calorias_inp = st.sidebar.number_input("Calorias", step=10)
proteina_inp = st.sidebar.number_input("Proteína (g)", step=1)
passos_inp = st.sidebar.number_input("Passos", step=100, value=0)
sono_inp = st.sidebar.number_input("Horas Sono", format="%.1f", step=0.5)

if st.sidebar.button("💾 Salvar Tudo"):
    with st.spinner("Calculando IMC..."):
        save_data(data_inp, peso_inp, calorias_inp, passos_inp, proteina_inp, sono_inp, cintura_inp, altura_inp)
    st.success("Dados Salvos!")
    import time
    time.sleep(1)
    st.rerun()

# --- ANÁLISE ---

# Lógica IA
tdee_real = 0
status_ia = False
ratio_proteina = 0
imc_atual = 0
classif_imc = ""

if not df.empty and len(df) > 7:
    cols = ['Peso', 'Calorias', 'Passos', 'Proteina', 'Sono', 'Cintura', 'Altura']
    for c in cols: 
        if c in df.columns: df[c] = pd.to_numeric(df[c])

    # Médias Móveis
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
            
        # Cálculo IMC Atual
        altura_atual = recent.iloc[-1]['Altura']
        if altura_atual > 0:
            imc_atual = peso_atual / (altura_atual ** 2)
            if imc_atual < 18.5: classif_imc = "Abaixo do Peso"
            elif imc_atual < 24.9: classif_imc = "Peso Ideal ✅"
            elif imc_atual < 29.9: classif_imc = "Sobrepeso"
            else: classif_imc = "Obesidade"
    else:
        status_ia = False

# --- VISUALIZAÇÃO ---

# Linha 1: IMC e Peso Ideal
st.subheader("⚖️ Análise de Peso Ideal (IMC)")
c1, c2, c3 = st.columns(3)

if imc_atual > 0:
    c1.metric("Seu IMC Atual", f"{imc_atual:.1f}", classif_imc)
    
    # Cálculo das faixas de peso ideal (IMC 18.5 a 24.9)
    altura_user = df.iloc[-1]['Altura']
    peso_min_ideal = 18.5 * (altura_user ** 2)
    peso_max_ideal = 24.9 * (altura_user ** 2)
    
    c2.metric("Seu Peso Ideal (Mín)", f"{peso_min_ideal:.1f} kg")
    c3.metric("Seu Peso Ideal (Max)", f"{peso_max_ideal:.1f} kg")
else:
    c1.info("Informe sua altura para calcular o IMC")

st.markdown("---")

# Linha 2: Metabolismo
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

# --- GRÁFICOS AVANÇADOS ---
if not df.empty and 'Altura' in df.columns:
    # Prepara dados para o gráfico de Peso Ideal
    altura_ref = df.iloc[-1]['Altura']
    if altura_ref > 0:
        df['Limite_Min'] = 18.5 * (altura_ref ** 2)
        df['Limite_Max'] = 24.9 * (altura_ref ** 2)
    
    tab1, tab2, tab3 = st.tabs(["🎯 Rumo ao Peso Ideal", "💪 Composição (Cintura)", "💤 Sono & Recuperação"])
    
    with tab1:
        st.caption("Acompanhe se seu peso (Azul) está entrando na faixa de peso ideal (Verde/Vermelho)")
        # Plota 3 linhas: Peso, Limite Minimo e Limite Maximo
        st.line_chart(df.set_index("Data")[['Peso', 'Limite_Min', 'Limite_Max']], 
                      color=["#0000FF", "#00FF00", "#FF0000"]) 
        # Azul = Peso, Verde = Minimo, Vermelho = Maximo
    
    with tab2:
        st.caption("Peso e Cintura caindo juntos = Queima de gordura pura")
        st.line_chart(df.set_index("Data")[["Peso", "Cintura"]], color=["#0000FF", "#FFA500"])
        
    with tab3:
        st.bar_chart(df.set_index("Data")[["Calorias", "Proteina"]])

    with st.expander("Ver Tabela Completa"):
        st.dataframe(df.sort_values(by="Data", ascending=False))
