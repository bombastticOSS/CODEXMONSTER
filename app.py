        nome = profissional["Nome"]

        for indice, valor in enumerate(valores):
            if valor not in CODIGOS_VALIDOS:
                problemas[identificador].add(COLUNAS_DIAS[indice])
                mensagens.append(f"{nome}: código inválido “{valor}” no dia {indice + 1}.")
            elif not turno_permitido(profissional, valor):
                problemas[identificador].add(COLUNAS_DIAS[indice])
                mensagens.append(f"{nome}: {valor} é incompatível com o turno cadastrado no dia {indice + 1}.")

        for indice in range(NUM_DIAS - 1):
            atual, proximo = valores[indice], valores[indice + 1]
            if atual in {"D12", "N12"} and proximo in TURNOS:
                problemas[identificador].update({COLUNAS_DIAS[indice], COLUNAS_DIAS[indice + 1]})
                mensagens.append(
                    f"{nome}: intervalo insuficiente entre os dias {indice + 1} ({atual}) e {indice + 2} ({proximo})."
                )

        consecutivos = 0
        for indice, valor in enumerate(valores):
            consecutivos = consecutivos + 1 if valor in TURNOS else 0
            if consecutivos > 6:
                problemas[identificador].add(COLUNAS_DIAS[indice])
                mensagens.append(f"{nome}: mais de seis dias consecutivos de trabalho no dia {indice + 1}.")

        if profissional["Sexo"] == "Feminino":
            domingos = [indice for indice, data in enumerate(DATAS) if data.weekday() == 6]
            for anterior, seguinte in zip(domingos, domingos[1:]):
                if valores[anterior] in TURNOS and valores[seguinte] in TURNOS:
                    problemas[identificador].update({COLUNAS_DIAS[anterior], COLUNAS_DIAS[seguinte]})
                    mensagens.append(f"{nome}: domingos consecutivos escalados ({anterior + 1} e {seguinte + 1}).")

    metricas = calcular_metricas_diarias(escala)
    for _, linha in metricas.iterrows():
        if int(linha["Déficit"]) > 0:
            mensagens.append(f"Dia {linha['Dia']}: déficit de {int(linha['Déficit'])} posição(ões) na cobertura mínima.")
    return problemas, mensagens, metricas


def totais_por_profissional(escala: pd.DataFrame) -> pd.DataFrame:
    por_id = escala.set_index("ID")
    linhas = []
    for _, profissional in PROFISSIONAIS.iterrows():
        identificador = profissional["ID"]
        realizado = sum(horas_de(por_id.at[identificador, coluna]) for coluna in COLUNAS_DIAS)
        meta = int(profissional["Meta"])
        linhas.append({"ID": identificador, "Meta": meta, "Realizado": realizado, "Saldo": realizado - meta})
    return pd.DataFrame(linhas).set_index("ID")


def linha_cobertura(metricas: pd.DataFrame) -> dict[str, Any]:
    linha: dict[str, Any] = {
        "_tipo": "cobertura",
        "_id": "__COBERTURA__",
        "Código/Cargo": "STATUS",
        "Nome": "Cobertura mínima",
        "Meta": "",
        "Realizado": "",
        "Saldo": "",
        "_travas": [],
        "_problemas": [],
    }
    for _, metrica in metricas.iterrows():
        coluna = metrica["Chave"]
        deficit, excedente = int(metrica["Déficit"]), int(metrica["Excedente"])
        linha[coluna] = "OK" if deficit == 0 and excedente == 0 else (f"–{deficit}" if deficit else f"+{excedente}")
    return linha


def montar_grade_exibicao(escala: pd.DataFrame) -> pd.DataFrame:
    problemas, _, metricas = auditar_escala(escala)
    totais = totais_por_profissional(escala)
    por_id = escala.set_index("ID")
    linhas: list[dict[str, Any]] = [linha_cobertura(metricas)]

    for cargo, titulo in (("ENF", None), ("TÉC", "TÉCNICOS DE ENFERMAGEM")):
        if titulo:
            divisor = {
                "_tipo": "divisor",
                "_id": "__TECNICOS__",
                "Código/Cargo": "EQUIPE",
                "Nome": titulo,
                "Meta": "",
                "Realizado": "",
                "Saldo": "",
                "_travas": [],
                "_problemas": [],
            }
            divisor.update({coluna: "" for coluna in COLUNAS_DIAS})
            linhas.append(divisor)

        for _, profissional in PROFISSIONAIS[PROFISSIONAIS["Cargo curto"] == cargo].iterrows():
            identificador = profissional["ID"]
            linha = {
                "_tipo": "profissional",
                "_id": identificador,
                "Código/Cargo": profissional["Código/Cargo"],
                "Nome": profissional["Nome"],
                "Meta": f"{int(totais.at[identificador, 'Meta'])}h",
                "Realizado": f"{int(totais.at[identificador, 'Realizado'])}h",
                "Saldo": f"{int(totais.at[identificador, 'Saldo']):+d}h",
                "_travas": sorted(st.session_state.travas.get(identificador, set())),
                "_problemas": sorted(problemas.get(identificador, set())),
            }
            for coluna in COLUNAS_DIAS:
                linha[coluna] = valor_exibido(identificador, coluna, valor_normalizado(por_id.at[identificador, coluna]))
            linhas.append(linha)
    return pd.DataFrame(linhas)


# -----------------------------------------------------------------------------
# ATUALIZAÇÃO MANUAL, TRAVAS E PEDIDOS DE FOLGA
# -----------------------------------------------------------------------------
def aplicar_edicoes_da_grade(retorno: pd.DataFrame) -> bool:
    """Registra edição manual e trava a célula; FP permanece uma preferência flexível."""
    if retorno is None or retorno.empty or "_id" not in retorno.columns:
        return False
    anterior = montar_grade_exibicao(st.session_state.escala).set_index("_id")
    escala = st.session_state.escala.set_index("ID")
    alterou = False

    for _, linha in retorno.iterrows():
        identificador = str(linha.get("_id", ""))
        if identificador not in POR_ID or identificador not in anterior.index:
            continue
        for coluna in COLUNAS_DIAS:
            novo = valor_normalizado(linha.get(coluna, ""))
            antigo_exibido = valor_normalizado(anterior.at[identificador, coluna])
            if novo == antigo_exibido:
                continue
            alterou = True
            pedidos = st.session_state.pedidos_folga.setdefault(identificador, set())
            travas = st.session_state.travas.setdefault(identificador, set())

            if novo == "FP":
                escala.at[identificador, coluna] = ""
                pedidos.add(coluna)
                travas.discard(coluna)
            else:
                escala.at[identificador, coluna] = novo
                pedidos.discard(coluna)
                # Inclui branco: o gestor pode proteger explicitamente uma folga.
                travas.add(coluna)

    if alterou:
        st.session_state.escala = escala.reset_index()
        salvar_estado()
    return alterou


def aplicar_marcacao_em_lote(identificadores: list[str], dias: list[str], codigo: str) -> int:
    escala = st.session_state.escala.set_index("ID")
    modificadas = 0
    for identificador in identificadores:
        travas = st.session_state.travas.setdefault(identificador, set())
        pedidos = st.session_state.pedidos_folga.setdefault(identificador, set())
        for coluna in dias:
            if coluna in travas:
                continue
            if codigo == "FP":
