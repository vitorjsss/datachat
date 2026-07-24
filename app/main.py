"""
DataChat NoSQL — Interface Streamlit (Semana 2).

Religado ao backend real: core/orquestrador.py coordena esquema → tradutor
(Gemini) → validador → executor → explicador (Gemini). Nenhum dado é mais
simulado — cada pergunta chama a API do Gemini de verdade.

Rodar:
    streamlit run app/main.py
"""

import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google import genai
from pymongo import MongoClient

from core.esquema import informacoes_colecao
from core.orquestrador import responder

load_dotenv()

st.set_page_config(page_title="DataChat NoSQL", page_icon="◆", layout="wide")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "datachat")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

EXEMPLOS = [
    "Quais os produtos com pior avaliação média, entre os que têm pelo menos 20 avaliações?",
    "Qual a distribuição das notas na base?",
    "Como evoluiu o volume de avaliações e a nota média por ano, a partir de 2018?",
    "Quais atributos existem no campo details dos produtos e com que frequência aparecem?",
    "Quais os 5 produtos que concentram mais avaliações?",
]

# ─────────────────────────────────────────────────────────────────────
# CONEXÕES — cacheadas para não reabrir a cada rerun do Streamlit
# ─────────────────────────────────────────────────────────────────────


@st.cache_resource
def obter_db():
    cliente = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    cliente.admin.command("ping")
    return cliente[MONGO_DB]


@st.cache_resource
def obter_cliente_llm():
    if not GOOGLE_API_KEY:
        return None
    return genai.Client(api_key=GOOGLE_API_KEY)


try:
    db = obter_db()
    erro_conexao = None
except Exception as e:  # conexão recusada, host errado etc.
    db = None
    erro_conexao = str(e)

cliente_llm = obter_cliente_llm()

# ─────────────────────────────────────────────────────────────────────
# ESTADO
# ─────────────────────────────────────────────────────────────────────

if "historico" not in st.session_state:
    st.session_state.historico = []
if "resposta" not in st.session_state:
    st.session_state.resposta = None
if "pergunta_atual" not in st.session_state:
    st.session_state.pergunta_atual = ""

# ─────────────────────────────────────────────────────────────────────
# BARRA LATERAL
# ─────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("### Conexão")
    if erro_conexao:
        st.error(f"MongoDB não conectou: {erro_conexao}", icon="⚠")
    else:
        st.success(f"MongoDB `{MONGO_DB}` conectado", icon="✓")

    if not GOOGLE_API_KEY:
        st.error("GOOGLE_API_KEY não definida no .env", icon="⚠")
    else:
        st.success("Gemini configurado", icon="✓")

    if db is not None:
        st.markdown("### Esquema")
        for colecao in ("reviews", "products"):
            info = informacoes_colecao(db, colecao)
            with st.expander(f"`{colecao}` — {info['quantidade_registros']:,} docs"):
                for campo in info["campos"]:
                    st.caption(f"· {campo}")

    st.markdown("### Histórico")
    if not st.session_state.historico:
        st.caption("Nenhuma consulta ainda.")
    else:
        for i, item in enumerate(reversed(st.session_state.historico[-8:])):
            if st.button(f"{item['hora']} — {item['pergunta'][:34]}…",
                         key=f"hist_{i}", use_container_width=True):
                st.session_state.pergunta_atual = item["pergunta"]
                st.session_state.resposta = item["resposta"]
                st.rerun()
        if st.button("Limpar histórico", use_container_width=True):
            st.session_state.historico = []
            st.rerun()

# ─────────────────────────────────────────────────────────────────────
# TELA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────

st.title("DataChat NoSQL")
st.caption("Pergunte em português. O Gemini traduz para MongoDB, executa e explica o resultado. "
           "Base: Amazon Reviews 2023 · categoria Gift_Cards.")

st.divider()

pergunta = st.text_input(
    "Sua pergunta",
    value=st.session_state.pergunta_atual,
    placeholder="Ex.: quais os produtos com pior avaliação média?",
)

col_botao, col_exemplos = st.columns([1, 3])
with col_botao:
    consultar = st.button(
        "Consultar", type="primary", use_container_width=True,
        disabled=db is None or cliente_llm is None,
    )
with col_exemplos:
    escolha = st.selectbox("Ou use um exemplo", ["—"] + EXEMPLOS,
                           label_visibility="collapsed")
    if escolha != "—" and escolha != st.session_state.pergunta_atual:
        st.session_state.pergunta_atual = escolha
        st.rerun()

# ─────────────────────────────────────────────────────────────────────
# EXECUÇÃO
# ─────────────────────────────────────────────────────────────────────

if consultar and pergunta.strip():
    with st.status("Processando…", expanded=True) as status:
        st.write("Carregando o esquema das coleções")
        st.write("Traduzindo a pergunta para MongoDB (Gemini)")
        st.write("Validando a consulta gerada")
        st.write("Executando no MongoDB")
        st.write("Redigindo a explicação (Gemini)")
        resposta = responder(pergunta, db, cliente_llm)
        status.update(
            label="Pronto" if not resposta["erro"] else "Erro",
            state="complete" if not resposta["erro"] else "error",
            expanded=False,
        )

    st.session_state.resposta = resposta
    st.session_state.pergunta_atual = pergunta
    st.session_state.historico.append({
        "hora": datetime.now().strftime("%H:%M"),
        "pergunta": pergunta,
        "resposta": resposta,
    })

elif consultar:
    st.info("Digite uma pergunta para consultar.")

# ─────────────────────────────────────────────────────────────────────
# RESULTADO
# ─────────────────────────────────────────────────────────────────────

resposta = st.session_state.resposta

if resposta and resposta["erro"]:
    st.error(resposta["erro"])
    if resposta.get("detalhe_tecnico"):
        with st.expander("Detalhe técnico"):
            st.code(resposta["detalhe_tecnico"])

elif resposta:
    aba_resposta, aba_query, aba_dados = st.tabs(
        ["Explicação", "Consulta MongoDB", "Resultados"]
    )

    with aba_resposta:
        st.markdown(resposta["explicacao"])
        if resposta["tentativas"] > 1:
            st.caption(f"(precisou de autocorreção — {resposta['tentativas']} tentativas)")

    with aba_query:
        st.caption(f"Coleção: `{resposta['colecao']}` · "
                   f"{len(resposta['pipeline'])} estágios · {resposta['tempo_s']}s")
        st.code(
            f"db.{resposta['colecao']}.aggregate(\n"
            + json.dumps(resposta["pipeline"], indent=2, ensure_ascii=False)
            + "\n)",
            language="javascript",
        )

    with aba_dados:
        resultados = resposta["resultados"]
        if not resultados:
            st.info("A consulta rodou sem erro, mas não retornou documentos.")
        else:
            df = pd.DataFrame(resultados)
            c1, c2 = st.columns([1, 1])
            c1.metric("Documentos retornados", len(df))
            c2.metric("Tempo total", f"{resposta['tempo_s']}s")
            st.dataframe(df, use_container_width=True, hide_index=True)

            numericas = df.select_dtypes("number").columns
            if len(numericas) and len(df) > 1:
                st.bar_chart(df.set_index(df.columns[0])[numericas[-1]])

            st.download_button("Baixar CSV", df.to_csv(index=False),
                               "resultados.csv", "text/csv")

else:
    st.markdown(
        "**Como usar:** digite uma pergunta em linguagem natural ou escolha um exemplo. "
        "O resultado aparece em três abas — a explicação em português, a consulta "
        "MongoDB que foi gerada e os dados brutos."
    )

st.divider()
st.caption("Backend real — Gemini (gemini-flash-latest) + MongoDB. Semana 2.")
