"""
Protótipo de escala assistencial — HC 15º Andar

Execução:
    pip install -r requirements_escala_hc15_v6.txt
    streamlit run sistema_escala_hc15_v6.py

O arquivo persiste somente dados operacionais agregados no computador em que
está sendo executado. Não armazena prontuários, diagnósticos ou identificadores
de pacientes.
"""

from __future__ import annotations

import calendar
import io
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from ortools.sat.python import cp_model

st.set_page_config(
    page_title="Escala Assistencial | HC 15º Andar",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

try:
    from st_aggrid import AgGrid, DataReturnMode, GridUpdateMode, GridOptionsBuilder, JsCode

    AGGRID_DISPONIVEL = True
except ImportError:
    AGGRID_DISPONIVEL = False

    # Mantém o modo de contingência carregável quando a dependência opcional
    # ainda não foi instalada. Os objetos não são usados nesse modo.
    def JsCode(*_args: Any, **_kwargs: Any) -> None:  # type: ignore[misc]
        return None


# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DA COMPETÊNCIA E DAS REGRAS OPERACIONAIS
# -----------------------------------------------------------------------------
ANO = 2026
MES = 11
LEITOS_TOTAIS = 60
CODIGOS_EDITAVEIS = ["", "M6", "D12", "N12", "FP", "FE", "AT", "LM", "LIC"]
CODIGOS_VALIDOS = set(CODIGOS_EDITAVEIS)
CODIGOS_AFASTAMENTO = {"FE", "AT", "LM", "LIC"}
TURNOS = ("M6", "D12", "N12")
HORAS_POR_CODIGO = {"M6": 6, "D12": 12, "N12": 12}
NOMES_DIAS = ("Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom")

# Este é o único bloco a ajustar caso o dimensionamento mínimo do setor mude.
# As chaves são cargo curto -> turno -> número mínimo de profissionais.
REQUISITOS_COBERTURA = {
    "dia_util": {
        "ENF": {"M6": 1, "D12": 5, "N12": 4},
        "TÉC": {"M6": 1, "D12": 6, "N12": 3},
    },
    "fim_de_semana": {
        "ENF": {"M6": 1, "D12": 3, "N12": 4},
        "TÉC": {"M6": 1, "D12": 4, "N12": 3},
    },
}

COMPETENCIA = date(ANO, MES, 1)
NUM_DIAS = calendar.monthrange(ANO, MES)[1]
DATAS = [date(ANO, MES, dia) for dia in range(1, NUM_DIAS + 1)]
COLUNAS_DIAS = [f"D{data.day:02d}" for data in DATAS]
COLUNAS_FIM_DE_SEMANA = [f"D{data.day:02d}" for data in DATAS if data.weekday() >= 5]
ROTULOS_DIAS = {
    f"D{data.day:02d}": f"{data.day:02d}\n{NOMES_DIAS[data.weekday()]}" for data in DATAS
}


def caminho_dados() -> Path:
    """Usa diretório local explícito e cria-o; não engole falhas de persistência."""
    raiz_padrao = Path(os.getenv("LOCALAPPDATA", Path.home())) / "HC15_Escala"
    raiz = Path(os.getenv("ESCALA_DATA_DIR", str(raiz_padrao)))
    raiz.mkdir(parents=True, exist_ok=True)
    return raiz


ARQUIVO_ESTADO = caminho_dados() / f"escala_{ANO}_{MES:02d}_v6.json"


# -----------------------------------------------------------------------------
# BASE DEMONSTRATIVA — substitua esta fonte por integração segura no projeto real
# -----------------------------------------------------------------------------
