import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
from datetime import datetime

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Dashboard Biohacker", layout="wide")
st.title("🧬 Dashboard Biohacker: Metabolismo & Composição")

# --- CONEXÃO GITHUB ---
def get_github_connection():
    try:
        token = st.secrets["github"]["token"]
        g = Github(token)
        repo_name = "diegotonialperetti/meu-dashboard-metabolico" # CONFIRA SEU REPO AQUI
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
            
            # Garante que as novas colunas existam (para compatibilidade)
            novas_colunas = ['Passos', 'Proteina', 'Sono', 'Cintura']
            for col in novas_colunas:
                if col not in df.columns:
                    df[col] = 0
            
            df['Data'] = pd.to_datetime(df['Data']).dt.date
            return df.sort_values(by="Data")
        except:
            return pd.DataFrame(columns=["Data", "Peso", "Calorias", "Passos", "Proteina", "Sono", "Cintura"])
            
    except Exception as e:
        return pd.DataFrame()

# --- SALVAR DADOS ---
def save_data(date, peso, calorias, passos, proteina, sono, cintura):
    repo = get_github_connection()
    if not repo: return

    date_str = date.strftime("%Y-%m-%d")
    new_line = f"{date_str},{peso},{calorias},{passos},{proteina},{sono},{cintura}\n"

    try:
        contents = repo.get_contents("dados_dieta.csv")
        current_data = contents.decoded_content.decode("utf-8")
        
        # Atualiza cabeçalho se for arquivo antigo
        header_line = current_data.split('\n')[0]
        if "Cintura" not in header_line:
            # Reconstrói o CSV inteiro se faltar colunas
            df = pd.read_csv(StringIO(current_data))
            novas_colunas = ['Passos', 'Proteina', 'Sono', 'Cintura']
            for col in novas_colunas:
                if col not in df.columns:
                    df[col] = 0
            
            # Adiciona a linha nova no dataframe
            # (Gambiarra simples: recriar o CSV string com pandas)
            output = StringIO()
            df.to_csv(output, index=False)
            current_data = output.getvalue()

        # Adiciona nova linha (método simples de append string para performance)
        # Se já tiver atualizado o header acima, usa o pandas, senão append direto
        if "Cintura" in current_data:
             updated_data = current_data.strip() + '\n' + new_line
        else:
             # Fallback de segurança
             updated_data = current_data + new_line

        repo.update_file("dados_dieta.csv", f"Registro Completo: {date_str}", updated_data, contents.sha)
        
    except:
        header = "Data,Peso,Calorias,Passos,Proteina,Sono,Cintura\n"
        repo.create_file("dados_dieta.csv", "Criando DB Biohacker", header + new_line)

# --- SIDEBAR ---
st.sidebar.header("📝 Diário Completo")
data_inp = st.sidebar.date_input("Data", datetime.now())
peso_inp = st.sidebar.number_input("Peso (kg)", format="%.2f", step=0.1)
cintura_inp = st.sidebar.number_input("Cintura/Abdomen (cm)", format="%.1f", step=0.5, help="Medir na altura do umbigo")
calorias_inp = st.sidebar.number_input("Calorias", step=10)
proteina_inp = st.sidebar.number_input("Proteína (g)", step=1, help="Total de gramas de proteína")
passos_inp = st.sidebar.number_input("Passos", step=100, value=0)
sono_inp = st.sidebar.number_input("Horas de Sono", format="%.1f", step=0.5)

if st.sidebar.button("💾 Salvar Tudo"):
    with st.spinner("Processando..."):
        save_data(data_inp, peso_inp, calorias_inp, passos_inp, proteina_inp, sono_inp, cintura_inp)
    st.success("Dados Salvos!")
    import time
    time.sleep(1)
    st.rerun()

# --- ANÁLISE ---
df = load_data()

# Lógica IA
tdee_real = 0
status_ia = False
ratio_proteina = 0

if not df.empty and len(df) > 7:
    cols = ['Peso', 'Calorias', 'Passos', 'Proteina', 'Sono', 'Cintura']
    for c in cols: df[c] = pd.to_numeric(df[c])

    # Médias Móveis (Suavização)
    df['M_Peso'] = df['Peso'].rolling(7).mean()
    df['M_Cals'] = df['Calorias'].rolling(7).mean()
    
    recent = df.tail(14)
    if len(recent) >= 7:
        delta_p = recent.iloc[-1]['M_Peso'] - recent.iloc[0]['M_Peso']
        media_kcal = recent['M_Cals'].mean()
        
        tdee_real = media_kcal - ((delta_p * 7700) / len(recent))
        status_ia = True
        
        # Análise de Proteína (g/kg)
        peso_atual = recent.iloc[-1]['Peso']
        media_prot = recent[recent['Proteina'] > 0]['Proteina'].mean()
        if pd.notna(media_prot) and peso_atual > 0:
            ratio_proteina = media_prot / peso_atual
    else:
        status_ia = False

# --- VISUALIZAÇÃO ---

# Linha 1: Metabolismo
st.subheader("🔥 Termômetro Metabólico")
c1, c2, c3 = st.columns(3)
if status_ia:
    c1.metric("Gasto Real (TDEE)", f"{int(tdee_real)} kcal")
    c2.metric("Meta Secar", f"{int(tdee_real - 500)} kcal")
    
    # Análise de Proteína
    cor_prot = "normal"
    msg_prot = "Baixa!"
    if ratio_proteina > 1.8: msg_prot = "Excelente 🦁"
    elif ratio_proteina > 1.5: msg_prot = "Boa 💪"
    else: msg_prot = "Baixa ⚠️ (Perda muscular)"
    
    c3.metric("Proteína Média", f"{ratio_proteina:.1f} g/kg", msg_prot)
else:
    c1.info("Aguardando 7 dias de dados...")

st.markdown("---")

# Linha 2: Métricas de Saúde
st.subheader("🩺 Sinais Vitais")
k1, k2, k3 = st.columns(3)

if not df.empty:
    # Sono
    dias_sono = df[df['Sono'] > 0].tail(7)
    media_sono = dias_sono['Sono'].mean() if not dias_sono.empty else 0
    k1.metric("Média Sono (7d)", f"{media_sono:.1f} h", "Ideal: 7h-8h")
    
    # Cintura
    dias_cintura = df[df['Cintura'] > 0]
    if not dias_cintura.empty:
        atual_cint = dias_cintura.iloc[-1]['Cintura']
        inicio_cint = dias_cintura.iloc[0]['Cintura']
        delta_cint = atual_cint - inicio_cint
        k2.metric("Cintura Atual", f"{atual_cint} cm", f"{delta_cint:.1f} cm (Total)")
    else:
        k2.metric("Cintura", "--")

    # Passos
    dias_passos = df[df['Passos'] > 100].tail(7)
    media_passos = int(dias_passos['Passos'].mean()) if not dias_passos.empty else 0
    k3.metric("Média Passos", f"{media_passos}", f"~{int(media_passos*0.04)} kcal")

# --- GRÁFICOS AVANÇADOS ---
if not df.empty:
    tab1, tab2, tab3 = st.tabs(["📉 Peso x Cintura", "🥩 Nutrição", "💤 Sono x Peso"])
    
    with tab1:
        st.caption("Se o Peso (Azul) sobe e a Cintura (Vermelha) desce, você está ganhando massa muscular!")
        chart_data = df.set_index("Data")[["Peso", "Cintura"]]
        st.line_chart(chart_data, color=["#0000FF", "#FF0000"]) # Azul e Vermelho
        
    with tab2:
        st.caption("Relação entre o que você come (Calorias) e a qualidade (Proteína)")
        st.bar_chart(df.set_index("Data")[["Calorias", "Proteina"]])
        
    with tab3:
        st.caption("Dias com pouco sono tendem a aumentar o peso no dia seguinte (retenção)?")
        st.line_chart(df.set_index("Data")[["Peso", "Sono"]])
        
    with st.expander("Ver Dados Brutos"):
        st.dataframe(df.sort_values(by="Data", ascending=False))
