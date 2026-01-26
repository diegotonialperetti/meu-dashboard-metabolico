import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import zipfile
from github import Github
from io import StringIO, BytesIO
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
            
            # Colunas
            cols = ['Passos', 'Proteina', 'Sono', 'Cintura', 'Altura', 'BPM', 'Energia', 'Pressao_High', 'Pressao_Low', 'SpO2']
            for col in cols:
                if col not in df.columns: df[col] = 0.0
            
            # Limpeza
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

# --- PROCESSAR ZIP DA PULSEIRA (O MÁGICO) ---
def processar_zip_pulseira(zip_file, df_atual):
    try:
        novos_dados = []
        
        with zipfile.ZipFile(zip_file) as z:
            file_names = z.namelist()
            
            # 1. Processa Passos (user_step.csv)
            # Estrutura esperada: date, step, calory
            df_step = pd.DataFrame()
            if "user_step.csv" in file_names:
                with z.open("user_step.csv") as f:
                    df_step = pd.read_csv(f)
                    df_step['Data'] = pd.to_datetime(df_step['date']).dt.date
                    # Agrupa por dia (soma passos)
                    df_step = df_step.groupby('Data').agg({'step': 'sum', 'calory': 'sum'}).reset_index()

            # 2. Processa Cardio (user_hb.csv)
            # Estrutura esperada: date, heart, lblood, hblood, spo
            df_hb = pd.DataFrame()
            if "user_hb.csv" in file_names:
                with z.open("user_hb.csv") as f:
                    df_hb = pd.read_csv(f)
                    df_hb['Data'] = pd.to_datetime(df_hb['date']).dt.date
                    # Agrupa por dia (média)
                    df_hb = df_hb.groupby('Data').mean(numeric_only=True).reset_index()

            # 3. Processa Sono (user_sleep.csv)
            # Estrutura esperada: date, minutes
            df_sleep = pd.DataFrame()
            if "user_sleep.csv" in file_names:
                with z.open("user_sleep.csv") as f:
                    df_sleep = pd.read_csv(f)
                    df_sleep['Data'] = pd.to_datetime(df_sleep['date']).dt.date
                    # Soma minutos de sono do dia e converte para horas
                    df_sleep = df_sleep.groupby('Data')['minutes'].sum().reset_index()
                    df_sleep['Sono_Horas'] = df_sleep['minutes'] / 60

        # --- MERGE DOS DADOS DA PULSEIRA ---
        # Começa com os passos como base, ou cria base vazia
        if not df_step.empty:
            df_final = df_step.copy()
        else:
            df_final = pd.DataFrame(columns=['Data'])

        # Junta Cardio
        if not df_hb.empty:
            df_final = pd.merge(df_final, df_hb, on='Data', how='outer')
        
        # Junta Sono
        if not df_sleep.empty:
            df_final = pd.merge(df_final, df_sleep, on='Data', how='outer')
            
        # Limpa NaN
        df_final = df_final.fillna(0)
        
        # --- ATUALIZAÇÃO DO DATAFRAME PRINCIPAL ---
        # Transforma o DF principal em Dict para busca rápida
        df_atual = df_atual.set_index('Data')
        df_final = df_final.set_index('Data')
        
        contador = 0
        
        for data, row in df_final.iterrows():
            if data in df_atual.index:
                # Atualiza existente se o valor for maior (para não sobrescrever com zero)
                if 'step' in row and row['step'] > 0: df_atual.at[data, 'Passos'] = row['step']
                if 'Sono_Horas' in row and row['Sono_Horas'] > 0: df_atual.at[data, 'Sono'] = row['Sono_Horas']
                if 'heart' in row and row['heart'] > 0: df_atual.at[data, 'BPM'] = row['heart']
                if 'spo' in row and row['spo'] > 0: df_atual.at[data, 'SpO2'] = row['spo']
                if 'hblood' in row and row['hblood'] > 0: df_atual.at[data, 'Pressao_High'] = row['hblood']
                if 'lblood' in row and row['lblood'] > 0: df_atual.at[data, 'Pressao_Low'] = row['lblood']
            else:
                # Cria nova linha se não existir (Cuidado com colunas faltantes)
                nova_linha = pd.Series(0, index=df_atual.columns)
                if 'step' in row: nova_linha['Passos'] = row['step']
                if 'Sono_Horas' in row: nova_linha['Sono'] = row['Sono_Horas']
                if 'heart' in row: nova_linha['BPM'] = row['heart']
                if 'spo' in row: nova_linha['SpO2'] = row['spo']
                if 'hblood' in row: nova_linha['Pressao_High'] = row['hblood']
                if 'lblood' in row: nova_linha['Pressao_Low'] = row['lblood']
                
                df_atual.loc[data] = nova_linha
                
            contador += 1
            
        return df_atual.reset_index(), contador

    except Exception as e:
        st.error(f"Erro ao processar ZIP: {e}")
        return df_atual, 0

# --- SALVAR TABELA COMPLETA ---
def save_full_dataframe(df_to_save):
    repo = get_github_connection()
    if not repo: return False

    try:
        df_to_save['Data'] = pd.to_datetime(df_to_save['Data'], errors='coerce').dt.date
        df_to_save = df_to_save.dropna(subset=['Data'])
        df_to_save = df_to_save.sort_values(by="Data")
        df_to_save = df_to_save.drop_duplicates(subset=['Data'], keep='last')

        contents = repo.get_contents("dados_dieta.csv")
        output = StringIO()
        df_to_save.to_csv(output, index=False)
        repo.update_file("dados_dieta.csv", "Importação ZIP / Edição Massa", output.getvalue(), contents.sha)
        return True
    except Exception as e:
        st.error(f"Erro ao salvar tabela: {e}")
        return False

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

# --- CÁLCULO TDEE ---
def calcular_tdee_inteligente(df):
    if len(df) < 3: return 0, False, "Coletando dados..."
    recent = df.tail(14).copy()
    recent['Dia_Num'] = (pd.to_datetime(recent['Data']) - pd.to_datetime(recent['Data'].min())).dt.days
    coef = np.polyfit(recent['Dia_Num'], recent['Peso'], 1)
    perda_diaria_kg_tendencia = coef[0]
    media_kcal = recent['Calorias'].mean()
    deficit_real = perda_diaria_kg_tendencia * 7700
    tdee_calculado = media_kcal - deficit_real
    if tdee_calculado < 1200: tdee_calculado = 1200 
    if tdee_calculado > 4000: tdee_calculado = 4000
    
    peso_hoje = recent.iloc[-1]['Peso']
    peso_esperado = (recent.iloc[-1]['Dia_Num'] * coef[0]) + coef[1]
    msg = "Tendência Estável"
    if peso_hoje > (peso_esperado + 0.5): msg = "💧 Retenção Detectada"
    elif peso_hoje < (peso_esperado - 0.5): msg = "🔥 Queima Rápida"
        
    return tdee_calculado, True, msg

# --- INICIALIZAÇÃO ---
df = load_data()

st.sidebar.header("📝 Diário & Smart Ring")

# --- NOVO: IMPORTADOR DE ZIP ---
uploaded_zip = st.sidebar.file_uploader("📂 Importar ZIP da Pulseira", type="zip")
if uploaded_zip is not None:
    if st.sidebar.button("Processar ZIP"):
        with st.spinner("Lendo arquivos da pulseira..."):
            df_atualizado, qtd = processar_zip_pulseira(uploaded_zip, df.copy())
            if qtd > 0:
                sucesso = save_full_dataframe(df_atualizado)
                if sucesso:
                    st.success(f"{qtd} dias importados com sucesso!")
                    import time
                    time.sleep(2)
                    st.rerun()
            else:
                st.warning("Não encontrei dados novos no ZIP.")

# --- FORMULÁRIO PADRÃO ---
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

# --- DASHBOARD ---
tdee_real, status_tdee, msg_tdee = 0, False, ""
imc_atual, ratio_proteina = 0, 0

if not df.empty:
    cols_num = ['Peso', 'Calorias', 'Passos', 'Proteina', 'Sono', 'Cintura', 'Altura', 'BPM', 'Energia', 'Pressao_High', 'SpO2']
    for c in cols_num: 
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    tdee_real, status_tdee, msg_tdee = calcular_tdee_inteligente(df)
    
    recent = df.tail(7)
    peso_atual = recent.iloc[-1]['Peso']
    altura_atual = recent.iloc[-1]['Altura']
    if altura_atual > 0: imc_atual = peso_atual / (altura_atual ** 2)
    
    dias_com_prot = recent[recent['Proteina'] > 0]
    media_prot = dias_com_prot['Proteina'].mean() if not dias_com_prot.empty else 0
    if peso_atual > 0: ratio_proteina = media_prot / peso_atual

# --- LAYOUT ---
st.subheader("📊 Painel Vital (IA Estatística)")
k1, k2, k3, k4 = st.columns(4)

if status_tdee:
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

    # --- TABELA EDITÁVEL ---
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

