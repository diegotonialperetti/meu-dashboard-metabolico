import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
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
            
            cols = ['Passos', 'Proteina', 'Sono', 'Cintura', 'Altura', 'BPM', 'Energia', 'Pressao_High', 'Pressao_Low', 'SpO2']
            for col in cols:
                if col not in df.columns: df[col] = 0.0
            
            df['Data'] = pd.to_datetime(df['Data'], errors='coerce').dt.date
            df = df.dropna(subset=['Data']) 
            df = df.sort_values(by="Data")
            df = df.drop_duplicates(subset=['Data'], keep='last')
            
            return df
        except:
            return pd.DataFrame(columns=["Data", "Peso", "Calorias", "Passos", "Proteina", "Sono", "Cintura", "Altura", "BPM", "Energia", "Pressao_High", "Pressao_Low", "SpO2"])
            
    except Exception as e:
        return pd.DataFrame()

# --- SALVAR LINHA ---
def save_data_row(data_ref, peso, calorias, passos, proteina, sono, cintura, altura, bpm, energia, p_high, p_low, spo2):
    repo = get_github_connection()
    if not repo: return

    try:
        contents = repo.get_contents("dados_dieta.csv")
        csv_string = contents.decoded_content.decode("utf-8")
        df = pd.read_csv(StringIO(csv_string))
        
        cols = ['Passos', 'Proteina', 'Sono', 'Cintura', 'Altura', 'BPM', 'Energia', 'Pressao_High', 'Pressao_Low', 'SpO2']
        for col in cols:
            if col not in df.columns: df[col] = 0.0
        
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce').dt.date
        df = df.dropna(subset=['Data'])

        vals = [peso, calorias, passos, proteina, sono, cintura, altura, bpm, energia, p_high, p_low, spo2]
        cols_save = ['Peso', 'Calorias', 'Passos', 'Proteina', 'Sono', 'Cintura', 'Altura', 'BPM', 'Energia', 'Pressao_High', 'Pressao_Low', 'SpO2']
        
        if data_ref in df['Data'].values:
            df.loc[df['Data'] == data_ref, cols_save] = vals
            msg_commit = f"Update: {data_ref}"
        else:
            new_row_dict = {'Data': data_ref}
            for c, v in zip(cols_save, vals): new_row_dict[c] = v
            new_row = pd.DataFrame([new_row_dict])
            df = pd.concat([df, new_row], ignore_index=True)
            msg_commit = f"Novo: {data_ref}"

        output = StringIO()
        df.to_csv(output, index=False)
        repo.update_file("dados_dieta.csv", msg_commit, output.getvalue(), contents.sha)
        
    except Exception as e:
        st.error(f"Erro ao salvar linha: {e}")

# --- SALVAR TABELA COMPLETA ---
def save_full_dataframe(df_to_save):
    repo = get_github_connection()
    if not repo: return

    try:
        df_to_save['Data'] = pd.to_datetime(df_to_save['Data'], errors='coerce').dt.date
        df_to_save = df_to_save.dropna(subset=['Data'])
        df_to_save = df_to_save.sort_values(by="Data")
        df_to_save = df_to_save.drop_duplicates(subset=['Data'], keep='last')

        contents = repo.get_contents("dados_dieta.csv")
        output = StringIO()
        df_to_save.to_csv(output, index=False)
        repo.update_file("dados_dieta.csv", "Edição em Massa", output.getvalue(), contents.sha)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar tabela: {e}")
        return False

# --- CÉREBRO: REGRESSÃO LINEAR PARA TDEE ---
def calcular_tdee_inteligente(df):
    # Precisa de pelo menos 3 pontos para uma tendência minimamente confiável
    if len(df) < 3:
        return 0, False, "Coletando dados..."

    # Pega os últimos 14 dias para ter contexto, mas dá mais peso para o recente
    recent = df.tail(14).copy()
    
    # Prepara dados para Regressão Linear (Converte data para número)
    recent['Dia_Num'] = (pd.to_datetime(recent['Data']) - pd.to_datetime(recent['Data'].min())).dt.days
    
    # 1. Calcula a TENDÊNCIA do Peso (Slope) usando numpy polyfit
    # Isso ignora picos repentinos (água) e vê a direção real da curva
    coef = np.polyfit(recent['Dia_Num'], recent['Peso'], 1)
    perda_diaria_kg_tendencia = coef[0] # Slope da reta (kg por dia)
    
    # 2. Média de Calorias Ingeridas
    media_kcal = recent['Calorias'].mean()
    
    # 3. Cálculo do TDEE suavizado
    # Se perda_diaria for negativa (emagreceu), TDEE é maior que ingestão
    # Se perda_diaria for positiva (engordou), TDEE é menor que ingestão
    # Mas usamos a TENDÊNCIA, não o peso de hoje
    
    deficit_real = perda_diaria_kg_tendencia * 7700
    tdee_calculado = media_kcal - deficit_real
    
    # 4. Trava de Segurança (Biohacking)
    # Impede valores absurdos causados por erros extremos
    if tdee_calculado < 1200: tdee_calculado = 1200 # Mínimo biológico
    if tdee_calculado > 4000: tdee_calculado = 4000 # Máximo provável
    
    # Detecção de Retenção Hídrica
    # Compara o peso real de hoje com o peso "Esperado" pela tendência
    peso_hoje = recent.iloc[-1]['Peso']
    peso_esperado = (recent.iloc[-1]['Dia_Num'] * coef[0]) + coef[1]
    
    msg = "Tendência Estável"
    if peso_hoje > (peso_esperado + 0.5):
        msg = "💧 Retenção Detectada (Ignorando pico)"
    elif peso_hoje < (peso_esperado - 0.5):
        msg = "🔥 Desidratação/Queima Rápida"
        
    return tdee_calculado, True, msg

# --- GRÁFICOS TRAVADOS (ALTAIR) ---
def plotar_travado(df, cols_y, cores, titulo_y="Valor"):
    source = df[['Data'] + cols_y].melt('Data', var_name='Indicador', value_name='Valor')
    chart = alt.Chart(source).mark_line(point=True).encode(
        x=alt.X('Data:T', axis=alt.Axis(format="%d/%m", title="Data")),
        y=alt.Y('Valor:Q', scale=alt.Scale(zero=False), title=titulo_y), 
        color=alt.Color('Indicador:N', scale=alt.Scale(domain=cols_y, range=cores), legend=alt.Legend(title="Legenda")),
        tooltip=['Data', 'Indicador', 'Valor']
    ).properties(height=350).interactive(bind_y=False)
    st.altair_chart(chart, use_container_width=True)

# --- INICIALIZAÇÃO ---
df = load_data()

st.sidebar.header("📝 Diário & Smart Ring")
data_selecionada = st.sidebar.date_input("Data", datetime.now())

defaults = {k: 0.0 for k in ['Peso', 'Altura', 'Cintura', 'Calorias', 'Proteina', 'Passos', 'Sono', 'BPM', 'Energia', 'Pressao_High', 'Pressao_Low', 'SpO2']}
defaults['Altura'] = 1.75
defaults['Energia'] = 5

dados_do_dia = df[df['Data'] == data_selecionada]
if not dados_do_dia.empty:
    row = dados_do_dia.iloc[0]
    st.sidebar.info("✏️ Editando dia existente.")
    for k in defaults.keys():
        if k in row: defaults[k] = float(row[k])
else:
    if not df.empty and 'Altura' in df.columns:
        if df.iloc[-1]['Altura'] > 0: defaults['Altura'] = float(df.iloc[-1]['Altura'])

with st.sidebar.expander("💍 Smart Ring / Cardio", expanded=True):
    bpm_inp = st.number_input("BPM Médio", value=int(defaults['BPM']), step=1)
    spo2_inp = st.number_input("Oxigênio (SpO2 %)", value=int(defaults['SpO2']), step=1, max_value=100)
    st.caption("Pressão Arterial")
    c_p1, c_p2 = st.columns(2)
    p_high_inp = c_p1.number_input("Alta (Sis)", value=int(defaults['Pressao_High']), step=1)
    p_low_inp = c_p2.number_input("Baixa (Dia)", value=int(defaults['Pressao_Low']), step=1)

st.sidebar.subheader("Rotina")
peso_inp = st.sidebar.number_input("Peso (kg)", value=defaults['Peso'], format="%.2f")
cintura_inp = st.sidebar.number_input("Cintura (cm)", value=defaults['Cintura'], format="%.1f")
calorias_inp = st.sidebar.number_input("Calorias", value=int(defaults['Calorias']), step=10)
proteina_inp = st.sidebar.number_input("Proteína (g)", value=int(defaults['Proteina']), step=1)
passos_inp = st.sidebar.number_input("Passos", value=int(defaults['Passos']), step=100)
sono_inp = st.sidebar.number_input("Sono (h)", value=defaults['Sono'], format="%.1f")
energia_inp = st.sidebar.slider("Energia", 1, 10, value=int(defaults['Energia']))
altura_inp = st.sidebar.hidden_input = defaults['Altura'] 

if st.sidebar.button("💾 Salvar Dados (Sidebar)"):
    with st.spinner("Salvando..."):
        save_data_row(data_selecionada, peso_inp, calorias_inp, passos_inp, proteina_inp, sono_inp, cintura_inp, altura_inp, bpm_inp, energia_inp, p_high_inp, p_low_inp, spo2_inp)
    st.success("Dados Salvos!")
    import time
    time.sleep(1)
    st.rerun()

# --- CÁLCULOS INTELIGENTES (TDEE SMOOTH) ---
tdee_real, status_tdee, msg_tdee = 0, False, ""
imc_atual = 0
ratio_proteina = 0

if not df.empty:
    cols_num = ['Peso', 'Calorias', 'Passos', 'Proteina', 'Sono', 'Cintura', 'Altura', 'BPM', 'Energia', 'Pressao_High', 'SpO2']
    for c in cols_num: 
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    # 1. Chama o Cérebro Estatístico
    tdee_real, status_tdee, msg_tdee = calcular_tdee_inteligente(df)
    
    # 2. Outros cálculos simples
    recent = df.tail(7)
    peso_atual = recent.iloc[-1]['Peso']
    altura_atual = recent.iloc[-1]['Altura']
    if altura_atual > 0: imc_atual = peso_atual / (altura_atual ** 2)
    
    dias_com_prot = recent[recent['Proteina'] > 0]
    media_prot = dias_com_prot['Proteina'].mean() if not dias_com_prot.empty else 0
    if peso_atual > 0: ratio_proteina = media_prot / peso_atual

# --- LAYOUT DASHBOARD ---
st.subheader("📊 Painel Vital (IA Estatística)")
k1, k2, k3, k4 = st.columns(4)

if status_tdee:
    # Mostra o TDEE e a mensagem da IA (ex: Retenção Detectada)
    k1.metric("🔥 TDEE Inteligente", f"{int(tdee_real)} kcal", msg_tdee)
    k2.metric("🍖 Proteína", f"{ratio_proteina:.1f} g/kg")
else:
    k1.metric("Status", msg_tdee)

if not df.empty:
    df_sono = df[df['Sono'] > 0.1].tail(7)
    if not df_sono.empty:
        media_sono = df_sono['Sono'].mean()
        k3.metric("💤 Sono Médio", f"{media_sono:.1f} h", help=f"Base: {len(df_sono)} dias")
    else:
        k3.metric("💤 Sono Médio", "--")
    
    if 'SpO2' in df.columns:
        dias_spo2 = df[df['SpO2'] > 0].tail(7)
        val_spo2 = f"{int(dias_spo2['SpO2'].mean())}%" if not dias_spo2.empty else "--"
        k4.metric("🫁 SpO2 Médio", val_spo2)

st.markdown("---")

# --- GRÁFICOS ---
if not df.empty and 'Altura' in df.columns:
    altura_ref = df.iloc[-1]['Altura']
    df['Limite_Min'] = 18.5 * (altura_ref ** 2) if altura_ref > 0 else 0
    df['Limite_Max'] = 24.9 * (altura_ref ** 2) if altura_ref > 0 else 0
    
    tab1, tab2, tab3 = st.tabs(["🎯 Peso & IMC", "💍 Smart Ring & Cardio", "⚡ Energia & Sono"])
    
    with tab1:
        # Peso com Linhas de Tendência seria legal no futuro
        plotar_travado(df, ['Peso', 'Limite_Min', 'Limite_Max'], ["#0000FF", "#00FF00", "#FF0000"], "Peso (kg)")
    
    with tab2:
        st.caption("Pressão Arterial (Alta) e Oxigênio")
        if 'Pressao_High' in df.columns and 'SpO2' in df.columns:
            df_an = df[(df['Pressao_High'] > 0) | (df['SpO2'] > 0)]
            if not df_an.empty:
                plotar_travado(df_an, ['Pressao_High', 'SpO2'], ["#FF0000", "#00FF00"], "Valor")
            else:
                st.info("Registre dados do anel para ver o gráfico.")

    with tab3:
        if 'Energia' in df.columns:
            df_en = df[df['Energia'] > 0]
            if not df_en.empty:
                st.bar_chart(df_en.set_index("Data")["Energia"])

    with st.expander("📝 Ver Tabela Completa (Modo Edição)", expanded=False):
        st.info("💡 Clique nas células para editar.")
        
        df_editado = st.data_editor(
            df.sort_values(by="Data", ascending=False),
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Peso": st.column_config.NumberColumn(format="%.2f kg"),
                "Altura": st.column_config.NumberColumn(format="%.2f m"),
                "Sono": st.column_config.NumberColumn(format="%.1f h"),
                "Data": st.column_config.DateColumn(format="DD/MM/YYYY"),
            }
        )
        
        if st.button("💾 Salvar Alterações da Tabela"):
            with st.spinner("Salvando tabela completa..."):
                if save_full_dataframe(df_editado):
                    st.success("Tabela atualizada com sucesso!")
                    import time
                    time.sleep(1)
                    st.rerun()
