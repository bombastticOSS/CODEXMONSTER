import streamlit as st
import pandas as pd
import numpy as np
import io
import os
import json
import datetime
from ortools.sat.python import cp_model

# Importação opcional do Plotly para evitar falha caso a biblioteca não esteja no requirements.txt
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_DISPONIVEL = True
except ImportError:
    PLOTLY_DISPONIVEL = False

# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Escala Assistencial — HC 15º Andar",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Estilização CSS customizada para visual executivo e compacto
st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 2rem; }
    .stMetric { background-color: #f8f9fa; padding: 10px; border-radius: 8px; border: 1px solid #e9ecef; }
    div[data-testid="stTable"] table { font-size: 11px !important; }
    div[data-testid="stDataFrame"] { font-size: 11px !important; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# PARÂMETROS E BASE DE DADOS DO HC 15º ANDAR (CLÍNICA MÉDICA)
# -----------------------------------------------------------------------------
ANO = 2026
MES = 11  # Novembro / 2026
COMPETENCIA = datetime.date(ANO, MES, 1)
DIAS_NO_MES = 30

@st.cache_data
def carregar_base_profissionais():
    csv_data = """ID,Nome,Sexo,Cargo,Turno_Base,Carga_Semanal,Jornada_Padrao
ENF-01,Ana Paula Silva,Fem,Enfermeiro,Diurno,36h,6h (M)
ENF-02,Beatriz Oliveira,Fem,Enfermeiro,Diurno,36h,12h (D)
ENF-03,Carlos Eduardo Lima,Masc,Enfermeiro,Diurno,40h,12h (D)
ENF-04,Daniela Martins,Fem,Enfermeiro,Diurno,36h,12h (D)
ENF-05,Eduardo Rocha,Masc,Enfermeiro,Diurno,40h,12h (D)
ENF-06,Fernanda Alves,Fem,Enfermeiro,Diurno,36h,12h (D)
ENF-07,Gabriel Santos,Masc,Enfermeiro,Diurno,40h,12h (D)
ENF-08,Helena Costa,Fem,Enfermeiro,Diurno,36h,12h (D)
ENF-09,Igor Ribeiro,Masc,Enfermeiro,Diurno,36h,12h (D)
ENF-10,Juliana Lima,Fem,Enfermeiro,Diurno,40h,12h (D)
ENF-11,Kátia Mendes,Fem,Enfermeiro,Diurno,36h,12h (D)
ENF-12,Lucas Pereira,Masc,Enfermeiro,Diurno,40h,12h (D)
ENF-13,Marcelo Silva,Masc,Enfermeiro,Noturno,36h,12h (N)
ENF-14,Nádia Ferreira,Fem,Enfermeiro,Noturno,36h,12h (N)
ENF-15,Otávio Barbosa,Masc,Enfermeiro,Noturno,40h,12h (N)
ENF-16,Patricia Gomes,Fem,Enfermeiro,Noturno,36h,12h (N)
ENF-17,Renato Cardoso,Masc,Enfermeiro,Noturno,36h,12h (N)
ENF-18,Simone Duarte,Fem,Enfermeiro,Noturno,40h,12h (N)
ENF-19,Thiago Moraes,Masc,Enfermeiro,Noturno,36h,12h (N)
ENF-20,Vanessa Castro,Fem,Enfermeiro,Noturno,40h,12h (N)
TEC-01,Aline Souza,Fem,Técnico Enf.,Diurno,36h,6h (M)
TEC-02,Bruno Carrijo,Masc,Técnico Enf.,Diurno,36h,12h (D)
TEC-03,Camila Rodrigues,Fem,Técnico Enf.,Diurno,36h,12h (D)
TEC-04,Diego Fernandes,Masc,Técnico Enf.,Diurno,40h,12h (D)
TEC-05,Eliana Machado,Fem,Técnico Enf.,Diurno,40h,12h (D)
TEC-06,Fabio Henrique,Masc,Técnico Enf.,Diurno,36h,12h (D)
TEC-07,Gisele Prado,Fem,Técnico Enf.,Diurno,36h,12h (D)
TEC-08,Heitor Vasconcelos,Masc,Técnico Enf.,Diurno,40h,12h (D)
TEC-09,Isabela Faria,Fem,Técnico Enf.,Diurno,40h,12h (D)
TEC-10,João Vitor Cruz,Masc,Técnico Enf.,Diurno,40h,12h (D)
TEC-11,Karen Stephanie,Fem,Técnico Enf.,Diurno,36h,12h (D)
TEC-12,Leonardo Nogueira,Masc,Técnico Enf.,Diurno,36h,12h (D)
TEC-13,Mariana Freitas,Fem,Técnico Enf.,Diurno,40h,12h (D)
TEC-14,Natália Guimarães,Fem,Técnico Enf.,Diurno,36h,12h (D)
TEC-15,Orlando Ramos,Masc,Técnico Enf.,Noturno,36h,12h (N)
TEC-16,Paula Tejada,Fem,Técnico Enf.,Noturno,36h,12h (N)
TEC-17,Quintino Bocaiúva,Masc,Técnico Enf.,Noturno,36h,12h (N)
TEC-18,Raquel Xavier,Fem,Técnico Enf.,Noturno,36h,12h (N)
TEC-19,Samuel Rosa,Masc,Técnico Enf.,Noturno,36h,12h (N)
TEC-20,Tatiana Valente,Fem,Técnico Enf.,Noturno,40h,12h (N)"""
    df = pd.read_csv(io.StringIO(csv_data))
    df['Código/Cargo'] = df['Cargo'].apply(lambda x: 'ENF' if 'Enfermeiro' in x else 'TÉC')
    df['Meta_Horas'] = df['Carga_Semanal'].apply(lambda x: 156 if x == '36h' else 176)
    return df

PROFISSIONAIS = carregar_base_profissionais()

# Mapeamento do Calendário de Novembro/2026 (01/11/2026 é Domingo)
DIAS_SEMANA_SIGLAS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
COLUNAS_DIAS = [f"Dia_{d+1}" for d in range(DIAS_NO_MES)]
ROTULOS_DIAS = {}
FINAIS_DE_SEMANA_INDICES = []
DOMINGOS_INDICES = []

for d in range(DIAS_NO_MES):
    data_dia = datetime.date(ANO, MES, d + 1)
    sigla = DIAS_SEMANA_SIGLAS[data_dia.weekday() if data_dia.weekday() < 6 else 0]
    wd = data_dia.weekday()
    if wd == 6:  # Domingo
        sigla = "Dom"
        FINAIS_DE_SEMANA_INDICES.append(d)
        DOMINGOS_INDICES.append(d)
    elif wd == 5:  # Sábado
        sigla = "Sáb"
        FINAIS_DE_SEMANA_INDICES.append(d)
    elif wd == 0: sigla = "Seg"
    elif wd == 1: sigla = "Ter"
    elif wd == 2: sigla = "Qua"
    elif wd == 3: sigla = "Qui"
    elif wd == 4: sigla = "Sex"

    ROTULOS_DIAS[f"Dia_{d+1}"] = f"{d+1}\n({sigla})"

CODIGOS_EDITAVEIS = ["", "M6", "D12", "N12", "FP", "FE", "AT", "LM", "LIC"]
VALORES_HORAS = {"M6": 6, "D12": 12, "N12": 12, "": 0, "FP": 0, "FE": 0, "AT": 0, "LM": 0, "LIC": 0}

# -----------------------------------------------------------------------------
# PERSISTÊNCIA DE ESTADO LOCAL
# -----------------------------------------------------------------------------
ARQUIVO_ESTADO = os.path.join(os.getcwd(), "escala_estado_hc15.json")

def inicializar_estado():
    if 'escala' not in st.session_state or 'travas' not in st.session_state:
        if os.path.exists(ARQUIVO_ESTADO):
            try:
                with open(ARQUIVO_ESTADO, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                    st.session_state.escala = pd.DataFrame(dados['escala'])
                    st.session_state.travas = dados.get('travas', {})
                    return
            except Exception:
                pass
        
        # Estado Inicial Padrão
        rows = []
        for _, prof in PROFISSIONAIS.iterrows():
            r = {'ID': prof['ID'], 'Nome': prof['Nome'], 'Código/Cargo': prof['Código/Cargo']}
            for col in COLUNAS_DIAS:
                r[col] = ""
            rows.append(r)
        st.session_state.escala = pd.DataFrame(rows)
        st.session_state.travas = {prof['ID']: [] for _, prof in PROFISSIONAIS.iterrows()}

def salvar_estado():
    try:
        dados = {
            'escala': st.session_state.escala.to_dict(orient='records'),
            'travas': st.session_state.travas
        }
        with open(ARQUIVO_ESTADO, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

inicializar_estado()

# -----------------------------------------------------------------------------
# AUDITORIA E MÉTRICAS EM TEMPO REAL
# -----------------------------------------------------------------------------
def auditar_escala(df_escala):
    mensagens = []
    totais_cumpridos = []
    
    for idx, prof in PROFISSIONAIS.iterrows():
        pid = prof['ID']
        nome = prof['Nome']
        sexo = prof['Sexo']
        row = df_escala[df_escala['ID'] == pid].iloc[0]
        
        horas_trabalhadas = 0
        consecutivos = 0
        
        for d_idx, col in enumerate(COLUNAS_DIAS):
            val = str(row[col]).strip().upper()
            h = VALORES_HORAS.get(val, 0)
            horas_trabalhadas += h
            
            # Validação de código desconhecido
            if val not in CODIGOS_EDITAVEIS:
                mensagens.append(f"⚠️ **{nome}**: Código inválido '{val}' no Dia {d_idx+1}. Tratado como 0h.")

            # Validação de dias consecutivos
            if h > 0:
                consecutivos += 1
                if consecutivos > 6:
                    mensagens.append(f"🚨 **{nome}**: Excede o teto legal de 6 dias consecutivos de trabalho no Dia {d_idx+1}.")
            else:
                consecutivos = 0
                
            # Validação Interjornada / 12x36
            if d_idx < DIAS_NO_MES - 1:
                prox_col = COLUNAS_DIAS[d_idx + 1]
                prox_val = str(row[prox_col]).strip().upper()
                if val in ['D12', 'N12'] and prox_val in ['M6', 'D12', 'N12']:
                    mensagens.append(f"🚨 **{nome}**: Quebra de interjornada (12x36) entre Dia {d_idx+1} ({val}) e Dia {d_idx+2} ({prox_val}).")

        # Validação de Domingos para Mulheres (ACT Cl. 24ª §1º)
        if sexo == 'Fem':
            for i in range(len(DOMINGOS_INDICES) - 1):
                d1 = DOMINGOS_INDICES[i]
                d2 = DOMINGOS_INDICES[i+1]
                val1 = str(row[COLUNAS_DIAS[d1]]).strip().upper()
                val2 = str(row[COLUNAS_DIAS[d2]]).strip().upper()
                if VALORES_HORAS.get(val1, 0) > 0 and VALORES_HORAS.get(val2, 0) > 0:
                    mensagens.append(f"🚨 **{nome}**: Trabalha em dois domingos consecutivos (Dia {d1+1} e Dia {d2+1}), violando a regra feminina da Ebserh.")

        totais_cumpridos.append(horas_trabalhadas)

    # Cobertura por dia
    deficit_cobertura = np.zeros(DIAS_NO_MES)
    for d_idx, col in enumerate(COLUNAS_DIAS):
        enf_diurnos = sum(1 for _, p in PROFISSIONAIS.iterrows() if p['Código/Cargo'] == 'ENF' and str(df_escala[df_escala['ID']==p['ID']][col].values[0]).upper() in ['M6', 'D12'])
        enf_noturnos = sum(1 for _, p in PROFISSIONAIS.iterrows() if p['Código/Cargo'] == 'ENF' and str(df_escala[df_escala['ID']==p['ID']][col].values[0]).upper() == 'N12')
        tec_diurnos = sum(1 for _, p in PROFISSIONAIS.iterrows() if p['Código/Cargo'] == 'TÉC' and str(df_escala[df_escala['ID']==p['ID']][col].values[0]).upper() in ['M6', 'D12'])
        tec_noturnos = sum(1 for _, p in PROFISSIONAIS.iterrows() if p['Código/Cargo'] == 'TÉC' and str(df_escala[df_escala['ID']==p['ID']][col].values[0]).upper() == 'N12')

        if enf_diurnos < 8 or enf_noturnos < 4 or tec_diurnos < 10 or tec_noturnos < 6:
            deficit_cobertura[d_idx] = 1
            mensagens.append(f"📉 **Dia {d_idx+1}**: Cobertura incompleta (Presentes: ENF Diurno {enf_diurnos}/8, Noturno {enf_noturnos}/4 | TÉC Diurno {tec_diurnos}/10, Noturno {tec_noturnos}/6).")

    metricas = {
        "Cumpridas": totais_cumpridos,
        "Déficit": deficit_cobertura
    }
    return df_escala, mensagens, metricas

# -----------------------------------------------------------------------------
# OTIMIZADOR GOOGLE OR-TOOLS (CP-SAT) RESPEITANDO TRAVAS 🔒
# -----------------------------------------------------------------------------
def executar_otimizacao():
    modelo = cp_model.CpModel()
    num_profs = len(PROFISSIONAIS)
    dias = range(DIAS_NO_MES)
    turnos = ['M6', 'D12', 'N12']
    
    escala_vars = {}
    for p in range(num_profs):
        for d in dias:
            for t in turnos:
                escala_vars[(p, d, t)] = modelo.NewBoolVar(f'p_{p}_d_{d}_t_{t}')

    df_atual = st.session_state.escala
    travas = st.session_state.travas

    # Aplicação de Hard Constraints e Travas
    for p in range(num_profs):
        prof = PROFISSIONAIS.iloc[p]
        pid = prof['ID']
        row = df_atual[df_atual['ID'] == pid].iloc[0]
        dias_travados = travas.get(pid, [])

        for d in dias:
            col = COLUNAS_DIAS[d]
            val = str(row[col]).strip().upper()

            # Se a célula estiver travada 🔒 ou tiver afastamento (FE, AT, LM, LIC, FP), congela no solver
            if col in dias_travados or val in ['FE', 'AT', 'LM', 'LIC', 'FP']:
                for t in turnos:
                    if t == val:
                        modelo.Add(escala_vars[(p, d, t)] == 1)
                    else:
                        modelo.Add(escala_vars[(p, d, t)] == 0)
            else:
                # Regras normais por perfil de turno
                if prof['Turno_Base'] == 'Noturno':
                    modelo.Add(escala_vars[(p, d, 'M6')] == 0)
                    modelo.Add(escala_vars[(p, d, 'D12')] == 0)
                else:
                    modelo.Add(escala_vars[(p, d, 'N12')] == 0)

        # Máximo de 1 turno por dia
        for d in dias:
            modelo.AddAtMostOne(escala_vars[(p, d, t)] for t in turnos)

        # Interjornada 12x36
        for d in range(DIAS_NO_MES - 1):
            t12 = escala_vars[(p, d, 'D12')] + escala_vars[(p, d, 'N12')]
            tr_prox = sum(escala_vars[(p, d + 1, t)] for t in turnos)
            modelo.Add(t12 + tr_prox <= 1)

        # Teto de 6 dias consecutivos
        for d in range(DIAS_NO_MES - 6):
            modelo.Add(sum(escala_vars[(p, d + i, t)] for i in range(7) for t in turnos) <= 6)

        # Regra de domingos para mulheres
        if prof['Sexo'] == 'Fem':
            for i in range(len(DOMINGOS_INDICES) - 1):
                d1, d2 = DOMINGOS_INDICES[i], DOMINGOS_INDICES[i+1]
                m1 = sum(escala_vars[(p, d1, t)] for t in turnos)
                m2 = sum(escala_vars[(p, d2, t)] for t in turnos)
                modelo.Add(m1 + m2 <= 1)

    # Cobertura Mínima Obrigatória por Dia
    for d in dias:
        enf_diurnos = [p for p in range(num_profs) if PROFISSIONAIS.iloc[p]['Código/Cargo'] == 'ENF' and PROFISSIONAIS.iloc[p]['Turno_Base'] == 'Diurno']
        enf_noturnos = [p for p in range(num_profs) if PROFISSIONAIS.iloc[p]['Código/Cargo'] == 'ENF' and PROFISSIONAIS.iloc[p]['Turno_Base'] == 'Noturno']
        tec_diurnos = [p for p in range(num_profs) if PROFISSIONAIS.iloc[p]['Código/Cargo'] == 'TÉC' and PROFISSIONAIS.iloc[p]['Turno_Base'] == 'Diurno']
        tec_noturnos = [p for p in range(num_profs) if PROFISSIONAIS.iloc[p]['Código/Cargo'] == 'TÉC' and PROFISSIONAIS.iloc[p]['Turno_Base'] == 'Noturno']

        modelo.Add(sum(escala_vars[(p, d, 'M6')] for p in enf_diurnos) == 1)
        modelo.Add(sum(escala_vars[(p, d, 'D12')] for p in enf_diurnos) == 7)
        modelo.Add(sum(escala_vars[(p, d, 'M6')] for p in tec_diurnos) == 1)
        modelo.Add(sum(escala_vars[(p, d, 'D12')] for p in tec_diurnos) == 9)
        modelo.Add(sum(escala_vars[(p, d, 'N12')] for p in enf_noturnos) == 4)
        modelo.Add(sum(escala_vars[(p, d, 'N12')] for p in tec_noturnos) == 6)

    # Penalidade por desvio da Carga Horária Mensal (Soft Constraint)
    penalidades = []
    for p in range(num_profs):
        meta = PROFISSIONAIS.iloc[p]['Meta_Horas']
        horas_calc = sum(escala_vars[(p, d, 'M6')]*6 + escala_vars[(p, d, 'D12')]*12 + escala_vars[(p, d, 'N12')]*12 for d in dias)
        diff = modelo.NewIntVar(-40, 40, f'diff_{p}')
        modelo.Add(diff == horas_calc - meta)
        abs_diff = modelo.NewIntVar(0, 40, f'abs_diff_{p}')
        modelo.AddAbsEquality(abs_diff, diff)
        penalidades.append(abs_diff * 10)

    modelo.Minimize(sum(penalidades))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 15.0
    status = solver.Solve(modelo)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        novos_registros = []
        for p in range(num_profs):
            prof = PROFISSIONAIS.iloc[p]
            pid = prof['ID']
            row_antiga = df_atual[df_atual['ID'] == pid].iloc[0]
            dias_travados = travas.get(pid, [])
            
            r = {'ID': pid, 'Nome': prof['Nome'], 'Código/Cargo': prof['Código/Cargo']}
            for d in dias:
                col = COLUNAS_DIAS[d]
                val_antigo = str(row_antiga[col]).strip().upper()
                
                if col in dias_travados or val_antigo in ['FE', 'AT', 'LM', 'LIC', 'FP']:
                    r[col] = val_antigo
                else:
                    t_alocado = ""
                    for t in turnos:
                        if solver.Value(escala_vars[(p, d, t)]) == 1:
                            t_alocado = t
                    r[col] = t_alocado
            novos_registros.append(r)
        
        st.session_state.escala = pd.DataFrame(novos_registros)
        salvar_estado()
        return True, "✅ Escala otimizada com sucesso preservando todas as travas e afastamentos!"
    else:
        return False, "❌ INVIABILIDADE MATEMÁTICA: O total de afastamentos ou travas manuais impediu o cumprimento da cobertura diária mínima obrigatória do 15º Andar."

# -----------------------------------------------------------------------------
# FUNÇÕES DE MANIPULAÇÃO DE TRAVAS E LOTE
# -----------------------------------------------------------------------------
def aplicar_travas(pid, dias_lista, acao):
    if pid not in st.session_state.travas:
        st.session_state.travas[pid] = []
    
    if acao == "travar":
        for d in dias_lista:
            if d not in st.session_state.travas[pid]:
                st.session_state.travas[pid].append(d)
    elif acao == "destravar":
        st.session_state.travas[pid] = [d for d in st.session_state.travas[pid] if d not in dias_lista]
    salvar_estado()

def aplicar_marcacao_em_lote(pids, dias_lista, codigo):
    df = st.session_state.escala.copy()
    cont = 0
    for pid in pids:
        travados = st.session_state.travas.get(pid, [])
        idx = df[df['ID'] == pid].index[0]
        for d in dias_lista:
            if d not in travados:
                df.at[idx, d] = codigo
                cont += 1
    st.session_state.escala = df
    salvar_estado()
    return cont

def carregar_pedidos_arquivo(uploaded_file):
    try:
        df_p = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('.xlsx') else pd.read_csv(uploaded_file)
        avisos = []
        carregados = 0
        
        for _, r in df_p.iterrows():
            id_ou_nome = str(r.get('ID', r.get('Nome', r.get('Nome Completo', '')))).strip()
            dias_raw = str(r.get('Dias_Folga', r.get('Dias', ''))).split(',')
            
            prof_match = PROFISSIONAIS[(PROFISSIONAIS['ID'] == id_ou_nome) | (PROFISSIONAIS['Nome'].str.contains(id_ou_nome, case=False, na=False))]
            if not prof_match.empty:
                pid = prof_match.iloc[0]['ID']
                idx = st.session_state.escala[st.session_state.escala['ID'] == pid].index[0]
                for d_str in dias_raw:
                    d_clean = d_str.strip().lower().replace('dia', '').replace('d', '')
                    if d_clean.isdigit():
                        d_num = int(d_clean)
                        if 1 <= d_num <= DIAS_NO_MES:
                            col = f"Dia_{d_num}"
                            if col not in st.session_state.travas.get(pid, []):
                                st.session_state.escala.at[idx, col] = "FP"
                                carregados += 1
            else:
                avisos.append(f"Colaborador '{id_ou_nome}' não localizado na base.")
        salvar_estado()
        return carregados, avisos
    except Exception as e:
        raise e

# -----------------------------------------------------------------------------
# INTERFACE PRINCIPAL
# -----------------------------------------------------------------------------
st.title("🏥 Escala Assistencial — HC 15º Andar")
st.caption(f"{COMPETENCIA.strftime('%B').capitalize()}/{ANO} · Visão Mensal Editável · Dimensionamento por Cobertura e Censo das Alas A/B")

# Auditoria Atual
_, avisos_auditoria, metricas_atuais = auditar_escala(st.session_state.escala)
total_travas = sum(len(dias) for dias in st.session_state.travas.values())

# Cabeçalho Superior de Métricas e Ações
c1, c2, c3, c4 = st.columns([1.5, 1.2, 1.2, 2.1])
with c1:
    if st.button("✨ Otimizar Escala sem Afetar 🔒", type="primary", use_container_width=True):
        with st.spinner("Calculando a melhor escala com OR-Tools CP-SAT..."):
            sucesso, msg = executar_otimizacao()
            if sucesso:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)
with c2:
    st.metric("Células Protegidas 🔒", total_travas)
with c3:
    st.metric("Dias com Déficit 🚨", int(sum(metricas_atuais["Déficit"])))
with c4:
    st.caption("A otimização respeita todas as células com 🔒 e afastamentos (`FE`, `AT`, `LM`, `LIC`, `FP`). Para alterar uma célula protegida, destrave-a antes.")

# Painel de Ferramentas Retrátil
with st.expander("📁 Ferramentas de Gestão da Escala (Travas, Lote, Pedidos e Exportação)", expanded=False):
    aba_travas, aba_lote, aba_pedidos, aba_exportar = st.tabs(["🔒 Travas", "📌 Lançamento em Lote", "🌿 Pedidos de Folga", "⬇️ Exportar"])
    
    opcoes_pessoas = {f"{linha['Nome']} ({linha['Código/Cargo']})": linha["ID"] for _, linha in PROFISSIONAIS.iterrows()}
    
    with aba_travas:
        col_t1, col_t2, col_t3 = st.columns([2.5, 4.5, 2])
        pessoa_nome = col_t1.selectbox("Colaborador", list(opcoes_pessoas.keys()), key="trava_pessoa")
        dias_trava = col_t2.multiselect("Dias a Gerir", COLUNAS_DIAS, format_func=lambda k: ROTULOS_DIAS[k].replace("\n", " "), key="trava_dias")
        
        with col_t3:
            st.write("")
            b_travar = st.button("🔒 Travar", use_container_width=True, key="btn_tr")
            b_destravar = st.button("🔓 Destravar", use_container_width=True, key="btn_destr")
            
            if b_travar and dias_trava:
                aplicar_travas(opcoes_pessoas[pessoa_nome], dias_trava, "travar")
                st.success("Travas aplicadas.")
                st.rerun()
            if b_destravar and dias_trava:
                aplicar_travas(opcoes_pessoas[pessoa_nome], dias_trava, "destravar")
                st.success("Travas removidas.")
                st.rerun()

    with aba_lote:
        l1, l2, l3 = st.columns([3, 2.5, 3.5])
        selecionados = l1.multiselect("Colaboradores", list(opcoes_pessoas.keys()), key="lote_pessoas")
        codigo_lote = l2.selectbox("Código", CODIGOS_EDITAVEIS, format_func=lambda v: v if v else "FOL (Folga Regular)", key="lote_codigo")
        dias_lote = l3.multiselect("Dias", COLUNAS_DIAS, format_func=lambda k: ROTULOS_DIAS[k].replace("\n", " "), key="lote_dias")
        
        if st.button("Aplicar apenas em células livres", key="aplicar_lote", type="primary"):
            ids = [opcoes_pessoas[n] for n in selecionados]
            if not ids or not dias_lote:
                st.warning("Selecione ao menos um colaborador e um dia.")
            else:
                n_up = aplicar_marcacao_em_lote(ids, dias_lote, codigo_lote)
                st.success(f"{n_up} célula(s) atualizada(s). Células protegidas foram preservadas.")
                st.rerun()

    with aba_pedidos:
        arquivo_pedidos = st.file_uploader("Importar planilha de pedidos (.xlsx ou .csv)", type=["xlsx", "csv"], key="pedidos_upload")
        st.caption("Colunas aceitas: ID ou Nome; Dias_Folga ou Dias. Exemplo: ENF-01 | 1, 5, 12")
        if arquivo_pedidos is not None and st.button("Ler Pedidos de Folga", key="ler_pedidos"):
            try:
                qtd, avisos = carregar_pedidos_arquivo(arquivo_pedidos)
                st.success(f"{qtd} pedido(s) de folga ('FP') aplicados com sucesso!")
                for av in avisos[:5]:
                    st.warning(av)
                st.rerun()
            except Exception as err:
                st.error(f"Erro ao ler arquivo: {err}")

    with aba_exportar:
        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
            st.session_state.escala.to_excel(writer, sheet_name="Escala_Mensal", index=False)
            PROFISSIONAIS.to_excel(writer, sheet_name="Base_Profissionais", index=False)
        
        st.download_button(
            "⬇️ Baixar Planilha Consolidada (.xlsx)",
            data=output_excel.getvalue(),
            file_name=f"escala_hc15_{ANO}_{MES:02d}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

# -----------------------------------------------------------------------------
# ABAS PRINCIPAIS: ESCALA MENSAL & DASHBOARD
# -----------------------------------------------------------------------------
aba_escala, aba_dashboard = st.tabs(["📋 Escala Mensal", "📊 Dashboard de Dimensionamento"])

with aba_escala:
    st.subheader("📊 Grade Panorâmica de Novembro/2026")
    
    # Preparação da Tabela Formatada para Exibição
    df_exibicao = st.session_state.escala.copy()
    
    # Adicionar Fechamento de Carga Horária
    meta_map = {row['ID']: row['Meta_Horas'] for _, row in PROFISSIONAIS.iterrows()}
    cumpridas_map = {PROFISSIONAIS.iloc[i]['ID']: metricas_atuais["Cumpridas"][i] for i in range(len(PROFISSIONAIS))}
    
    df_exibicao['Meta'] = df_exibicao['ID'].map(meta_map)
    df_exibicao['Cumprida'] = df_exibicao['ID'].map(cumpridas_map)
    df_exibicao['Saldo'] = df_exibicao.apply(lambda r: f"+{r['Cumprida'] - r['Meta']}h" if r['Cumprida'] > r['Meta'] else f"{r['Cumprida'] - r['Meta']}h", axis=1)

    # Configuração do Editor de Dados com Restrição de Colunas
    column_config = {
        "ID": st.column_config.TextColumn("ID", disabled=True, width="small"),
        "Nome": st.column_config.TextColumn("Nome", disabled=True, width="medium"),
        "Código/Cargo": st.column_config.TextColumn("Cargo", disabled=True, width="small"),
        "Meta": st.column_config.NumberColumn("Meta", disabled=True, width="small"),
        "Cumprida": st.column_config.NumberColumn("Cumprida", disabled=True, width="small"),
        "Saldo": st.column_config.TextColumn("Saldo", disabled=True, width="small"),
    }
    
    for col in COLUNAS_DIAS:
        column_config[col] = st.column_config.SelectboxColumn(
            ROTULOS_DIAS[col],
            options=CODIGOS_EDITAVEIS,
            required=False,
            width="small"
        )

    # Reordenar colunas para manter fechamento ao final
    cols_ordenadas = ["ID", "Nome", "Código/Cargo"] + COLUNAS_DIAS + ["Meta", "Cumprida", "Saldo"]
    df_exibicao = df_exibicao[cols_ordenadas]

    # Renderização da Tabela Editável
    df_editado = st.data_editor(
        df_exibicao,
        column_config=column_config,
        use_container_width=True,
        hide_index=True,
        key="data_editor_escala"
    )

    # Atualiza o Session State se houver edição manual
    if not df_editado.equals(df_exibicao):
        for col in COLUNAS_DIAS:
            st.session_state.escala[col] = df_editado[col]
        salvar_estado()
        st.rerun()

    # Mapeamento de Cores no Pandas Styler para Destaques Visuais
    def aplicar_estilo_heatmap(val, is_weekend=False):
        val_str = str(val).strip().upper()
        if val_str == 'FP':
            return 'background-color: #D4EDDA; color: #155724; font-weight: bold;'
        elif val_str == 'FE':
            return 'background-color: #FFF3CD; color: #856404; font-weight: bold;'
        elif val_str == 'AT':
            return 'background-color: #F8D7DA; color: #721C24; font-weight: bold;'
        elif val_str == 'LM':
            return 'background-color: #E2E0F8; color: #381282; font-weight: bold;'
        elif val_str == 'LIC':
            return 'background-color: #FFE8D6; color: #853B00; font-weight: bold;'
        elif val_str in ['M6', 'D12', 'N12']:
            return 'background-color: #E2EFDA; color: #1E4620; font-weight: bold;'
        elif is_weekend:
            return 'background-color: #E8F4F8;'
        return ''

    with st.expander("🎨 Visualizar Matriz Formatada em Cores (Heatmap Visual)", expanded=False):
        styler = df_exibicao.style
        for d_idx, col in enumerate(COLUNAS_DIAS):
            is_wk = d_idx in FINAIS_DE_SEMANA_INDICES
            styler = styler.map(lambda v, w=is_wk: aplicar_estilo_heatmap(v, w), subset=[col])
        st.dataframe(styler, use_container_width=True, hide_index=True)

    # Painel Inferior de Avisos de Auditoria
    if avisos_auditoria:
        with st.expander(f"⚠️ {len(avisos_auditoria)} Alerta(s) de Conformidade Legal e Cobertura", expanded=True):
            for av in avisos_auditoria[:15]:
                st.write(f"• {av}")
            if len(avisos_auditoria) > 15:
                st.caption(f"Mostrando 15 de {len(avisos_auditoria)} alertas.")
    else:
        st.success("✅ 100% de conformidade normativa (12x36, interjornada, teto de 6 dias e regras de domingos atendidas).")

with aba_dashboard:
    st.subheader("📊 Dashboard de Inteligência & Dimensionamento (Alta Gestão)")
    
    # 1. Cards de Absenteísmo e Afastamentos
    df_esc = st.session_state.escala
    fe_count = sum((df_esc[COLUNAS_DIAS] == 'FE').sum())
    at_count = sum((df_esc[COLUNAS_DIAS] == 'AT').sum())
    lm_count = sum((df_esc[COLUNAS_DIAS] == 'LM').sum())
    lic_count = sum((df_esc[COLUNAS_DIAS] == 'LIC').sum())
    fp_count = sum((df_esc[COLUNAS_DIAS] == 'FP').sum())
    
    db1, db2, db3, db4, db5, db6 = st.columns(6)
    db1.metric("Equipe Total", len(PROFISSIONAIS))
    db2.metric("Férias (FE)", int(fe_count), delta_color="normal")
    db3.metric("Atestados (AT)", int(at_count), delta_color="inverse")
    db4.metric("Lic. Maternidade", int(lm_count))
    db5.metric("Lic. Pessoal", int(lic_count))
    db6.metric("Folgas Pedidas", int(fp_count))
    
    st.divider()
    
    # 2. Gráfico de Cobertura Diária Planejada por Cargo e Turno
    st.markdown("##### 📈 Cobertura Diária de Profissionais Ativos por Turno")
    
    cobertura_dados = []
    for d_idx, col in enumerate(COLUNAS_DIAS):
        data_d = datetime.date(ANO, MES, d_idx + 1)
        tipo_dia = "Fim de Semana" if d_idx in FINAIS_DE_SEMANA_INDICES else "Dia Útil"
        
        enf_diurno = sum(1 for _, p in PROFISSIONAIS.iterrows() if p['Código/Cargo'] == 'ENF' and str(df_esc[df_esc['ID']==p['ID']][col].values[0]).upper() in ['M6', 'D12'])
        enf_noturno = sum(1 for _, p in PROFISSIONAIS.iterrows() if p['Código/Cargo'] == 'ENF' and str(df_esc[df_esc['ID']==p['ID']][col].values[0]).upper() == 'N12')
        tec_diurno = sum(1 for _, p in PROFISSIONAIS.iterrows() if p['Código/Cargo'] == 'TÉC' and str(df_esc[df_esc['ID']==p['ID']][col].values[0]).upper() in ['M6', 'D12'])
        tec_noturno = sum(1 for _, p in PROFISSIONAIS.iterrows() if p['Código/Cargo'] == 'TÉC' and str(df_esc[df_esc['ID']==p['ID']][col].values[0]).upper() == 'N12')
        
        cobertura_dados.append({"Dia": d_idx + 1, "Categoria": "ENF Diurno (Meta: 8)", "Quantidade": enf_diurno, "Tipo": tipo_dia})
        cobertura_dados.append({"Dia": d_idx + 1, "Categoria": "ENF Noturno (Meta: 4)", "Quantidade": enf_noturno, "Tipo": tipo_dia})
        cobertura_dados.append({"Dia": d_idx + 1, "Categoria": "TÉC Diurno (Meta: 10)", "Quantidade": tec_diurno, "Tipo": tipo_dia})
        cobertura_dados.append({"Dia": d_idx + 1, "Categoria": "TÉC Noturno (Meta: 6)", "Quantidade": tec_noturno, "Tipo": tipo_dia})

    df_cob = pd.DataFrame(cobertura_dados)
    if PLOTLY_DISPONIVEL:
        fig_cob = px.bar(
            df_cob,
            x="Dia",
            y="Quantidade",
            color="Categoria",
            barmode="group",
            title="Quantitativo Diário de Pessoal Presente no 15º Andar",
            labels={"Quantidade": "Profissionais Presentes", "Dia": "Dia do Mês"},
            height=380
        )
        st.plotly_chart(fig_cob, use_container_width=True)
    else:
        pivot_cob = df_cob.pivot(index="Dia", columns="Categoria", values="Quantidade")
        st.bar_chart(pivot_cob, use_container_width=True)

    st.divider()

    # 3. Gráfico de Saldo de Banco de Horas da Equipe
    col_g1, col_g2 = st.columns([1.2, 1])
    
    with col_g1:
        st.markdown("##### ⚖️ Saldo de Banco de Horas por Colaborador")
        df_saldos = pd.DataFrame({
            "Nome": PROFISSIONAIS['Nome'],
            "Cargo": PROFISSIONAIS['Código/Cargo'],
            "Saldo_Horas": [metricas_atuais["Cumpridas"][i] - PROFISSIONAIS.iloc[i]['Meta_Horas'] for i in range(len(PROFISSIONAIS))]
        })
        
        if PLOTLY_DISPONIVEL:
            fig_saldo = px.bar(
                df_saldos,
                x="Nome",
                y="Saldo_Horas",
                color="Cargo",
                title="Distribuição do Saldo de Horas Mensal (ACT EBSERH)",
                labels={"Saldo_Horas": "Saldo em Horas (h)"},
                height=350
            )
            st.plotly_chart(fig_saldo, use_container_width=True)
        else:
            st.bar_chart(df_saldos.set_index("Nome")["Saldo_Horas"], use_container_width=True)

    with col_g2:
        st.markdown("##### 📄 Relatório Nominal de Afastamentos")
        afastamentos_lista = []
        for idx, prof in PROFISSIONAIS.iterrows():
            pid = prof['ID']
            row = df_esc[df_esc['ID'] == pid].iloc[0]
            
            cont_afast = 0
            tipos = set()
            for col in COLUNAS_DIAS:
                v = str(row[col]).strip().upper()
                if v in ['FE', 'AT', 'LM', 'LIC']:
                    cont_afast += 1
                    tipos.add(v)
            if cont_afast > 0:
                afastamentos_lista.append({
                    "Nome": prof['Nome'],
                    "Cargo": prof['Código/Cargo'],
                    "Tipo": ", ".join(tipos),
                    "Dias": cont_afast
                })
        
        if afastamentos_lista:
            st.dataframe(pd.DataFrame(afastamentos_lista), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum afastamento prolongado registrado para a equipe este mês.")

st.divider()
st.caption("🏥 Sistema de Otimização e Gestão de Escalas Assistenciais — HC 15º Andar (Clínica Médica) · HC-UFG / EBSERH")
