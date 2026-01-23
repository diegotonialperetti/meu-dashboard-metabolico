import streamlit as st
import pandas as pd
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
            
            # Garante colunas
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

# --- FUNÇÃO DE GRÁFICO TRAVADO (ALTAIR) ---
def plotar_travado(df, cols_y, cores, titulo_y="Valor"):
    # Prepara dados para o formato do Altair (Long Format)
    source = df[['Data'] + cols_y].melt('Data', var_name='Indicador', value_name='Valor')
    
    # Cria o gráfico base
    chart = alt.Chart(source).mark_line(point=True).encode(
        x=alt.X('Data:T', axis=alt.Axis(format="%d/%m", title="Data")), # T = Tempo
        y=alt.Y('Valor:Q', scale=alt.Scale(zero=False), title=titulo_y), # Q = Quantidade, zero=False para dar zoom automático na escala
        color=alt.Color('Indicador:N', scale=alt.Scale(domain=cols_y, range=cores), legend=alt.Legend(title="Legenda")),
        tooltip=['Data', 'Indicador', 'Valor']
    ).properties(
        height=350
    ).interactive(bind_y=False) # <--- AQUI ESTÁ A MÁGICA: bind_y=False trava o eixo vertical

    st.altair_chart(chart, use_container_width=True)

# --- INICIALIZAÇÃO ---
df = load_data()

st.sidebar.header("📝 Diário & Smart Ring")
data_selecionada = st.sidebar.date_input("Data", datetime.now())

# Defaults
defaults = {k: 0.0 for k in ['Peso', 'Altura', 'Cintura', 'Calorias', 'Proteina', 'Passos', 'Sono', 'BPM', 'Energia', 'Pressao_High', 'Pressao_Low', 'SpO2']}
defaults['Altura'] = 1.75
defaults['Energia'] = 5

# Edição Sidebar
dados_do_dia = df[df['Data'] == data_selecionada]
if not dados_do_dia.empty:
    row = dados_do_dia.iloc[0]
    st.sidebar.info("✏️ Editando dia existente.")
    for k in defaults.keys():
        if k in row: defaults[k] = float(row[k])
else:
    if not df.empty and 'Altura' in df.columns:
        if df.iloc[-1]['Altura'] > 0: defaults['Altura'] = float(df.iloc[-1]['Altura'])

# --- FORMULÁRIO SIDEBAR ---
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

# --- CÁLCULOS ---
tdee_real = 0
status_ia = False
imc_atual = 0
ratio_proteina = 0

if not df.empty:
    cols_num = ['Peso', 'Calorias', 'Passos', 'Proteina', 'Sono', 'Cintura', 'Altura', 'BPM', 'Energia', 'Pressao_High', 'SpO2']
    for c in cols_num: 
        if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    dias_registrados = len(df)
    
    if dias_registrados >= 2:
        window_size = min(7, dias_registrados)
        recent = df.tail(window_size)
        
        delta_peso = recent.iloc[-1]['Peso'] - recent.iloc[0]['Peso']
        media_kcal = recent['Calorias'].mean()
        
        if window_size > 0:
            superavit_diario = (delta_peso * 7700) / window_size
            tdee_real = media_kcal - superavit_diario
            status_ia = True
        
        peso_atual = recent.iloc[-1]['Peso']
        altura_atual = recent.iloc[-1]['Altura']
        if altura_atual > 0: imc_atual = peso_atual / (altura_atual ** 2)
        
        dias_com_prot = recent[recent['Proteina'] > 0]
        media_prot = dias_com_prot['Proteina'].mean() if not dias_com_prot.empty else 0
        if peso_atual > 0: ratio_proteina = media_prot / peso_atual
    else:
        status_ia = False

# --- LAYOUT DASHBOARD ---
st.subheader("📊 Painel Vital")
k1, k2, k3, k4 = st.columns(4)

if status_ia:
    k1.metric("🔥 TDEE (Gasto)", f"{int(tdee_real)} kcal")
    k2.metric("🍖 Proteína", f"{ratio_proteina:.1f} g/kg")
else:
    k1.metric("Status", f"{len(df)} registro(s)")

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

# --- GRÁFICOS INTERATIVOS TRAVADOS ---
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
                # Energia fica melhor como barra mesmo
                st.bar_chart(df_en.set_index("Data")["Energia"], color="#FFA500")

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
