# Escala assistencial HC 15º Andar — versão 6

## Como executar

```powershell
pip install -r requirements_escala_hc15_v6.txt
streamlit run sistema_escala_hc15_v6.py
```

O estado local é salvo em `%LOCALAPPDATA%\HC15_Escala`. Para definir outro
diretório, configure a variável de ambiente `ESCALA_DATA_DIR` antes de iniciar
o Streamlit.

## O que esta versão entrega

- Escala mensal em uma única grade, com Enfermeiros e Técnicos separados por
  seção, identificação por nome e código/cargo e totais à direita.
- Células com lista controlada: vazio/FOL, M6, D12, N12, FP, FE, AT, LM e LIC.
- Cores por tipo de plantão/afastamento, fim de semana sinalizado e vermelho
  para conflitos de regra ou déficit de cobertura.
- Travas por célula: toda edição manual é protegida automaticamente; a IA não
  altera células travadas, inclusive uma folga vazia. O gestor pode travar ou
  destravar dias pelo painel de gestão.
- Otimizador CP-SAT com cobertura por cargo/turno, descanso entre jornadas,
  teto de dias consecutivos, regra de domingos e prioridade para pedidos de
  folga.
- Aba própria de dashboard com censo manual diário das alas A e B, limitadas a
  60 leitos em conjunto; ocupação, cobertura, profissionais/dia, horas,
  comparação entre dias úteis e fins de semana e alertas críticos.
- Exportação para Excel com escala, cobertura e censo.

## Pontos a validar antes de uso real

Este é um protótipo operacional, não um sistema hospitalar homologado. A
implantação institucional deve substituir a base demonstrativa por fonte de
dados autorizada, validar as metas e as regras trabalhistas com RH e
enfermagem, prever autenticação, perfis de acesso, trilha de auditoria,
backup, concorrência entre gestores e integração segura com os sistemas do
hospital. Para uma operação de 400+ colaboradores, a regra de cobertura deve
ser configurada por unidade/ala/turno, e o estado local deve migrar para banco
de dados com controle de acesso.
