"""
DataChat NoSQL — Protótipo da interface (Semana 1).

Valida o fluxo da aplicação antes da integração com o backend e o LLM.
Todos os dados são simulados (mock). Nenhuma conexão real com MongoDB
ou com API de LLM acontece aqui.

Rodar:
    streamlit run app/main.py
"""

import json
import time
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(page_title="DataChat NoSQL", page_icon="◆", layout="wide")

# ─────────────────────────────────────────────────────────────────────
# MOCK DATA — substituído pelo backend real na Semana 2
# ─────────────────────────────────────────────────────────────────────

MOCK = {
    "quais produtos concentram mais avaliações?": {
        "query": [
            {"$group": {"_id": "$parent_asin", "avaliacoes": {"$sum": 1},
                        "nota_media": {"$avg": "$rating"}}},
            {"$sort": {"avaliacoes": -1}},
            {"$limit": 5},
            {"$lookup": {"from": "products", "localField": "_id",
                         "foreignField": "parent_asin", "as": "produto"}},
            {"$unwind": "$produto"},
            {"$project": {"_id": 0, "nome": "$produto.title",
                          "avaliacoes": 1, "nota_media": 1}},
        ],
        "colecao": "reviews",
        "resultados": [
            {"nome": "Amazon Reload", "avaliacoes": 36863, "nota_media": 4.60},
            {"nome": "Amazon.com Gift Card in a Holiday Gift Box (Various Designs)", "avaliacoes": 14912, "nota_media": 4.74},
            {"nome": "Amazon.com Gift Card in Various Gift Boxes", "avaliacoes": 6940, "nota_media": 4.58},
            {"nome": "Amazon Reload", "avaliacoes": 6635, "nota_media": 4.35},
            {"nome": "Amazon.com Gift Card in a Reveal (Various Designs)", "avaliacoes": 6329, "nota_media": 4.68},
        ],
        "explicacao": (
            "O **Amazon Reload** concentra sozinho **36.863 avaliações — "
            "24,2% de toda a base** de 152.410 reviews. Os 5 produtos mais avaliados "
            "somam mais de 40% da base — resultado medido diretamente na Consulta 8 "
            "de `scripts/consultas.py`.\n\n"
            "É uma cauda longa extrema: a média de 134 avaliações por produto esconde "
            "esse desequilíbrio, então qualquer ranking por volume precisa de cuidado "
            "— é por isso que as consultas de \"melhor/pior produto\" usam um corte "
            "mínimo de avaliações antes de ordenar."
        ),
    },
    "qual a distribuição das notas?": {
        "query": [
            {"$group": {"_id": "$rating", "total": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ],
        "colecao": "reviews",
        "resultados": [
            {"_id": 1.0, "total": 12326},
            {"_id": 2.0, "total": 1873},
            {"_id": 3.0, "total": 3271},
            {"_id": 4.0, "total": 6692},
            {"_id": 5.0, "total": 128248},
        ],
        "explicacao": (
            "A base tem **152.410** avaliações, e a distribuição é assimétrica em "
            "grau extremo: **84,1%** são 5 estrelas e **8,1%** são 1 estrela — quase "
            "sem meio-termo.\n\n"
            "Faz sentido para o produto: um vale-presente ou funciona como esperado "
            "(código válido, saldo correto, chegou a tempo) ou falha por completo "
            "(código inválido, já resgatado, nunca chegou). Não existe \"vale-presente "
            "razoável\" para avaliar com 3 estrelas."
        ),
    },
    "quantas avaliações verificadas existem por ano?": {
        "query": [
            {"$match": {"verified_purchase": True,
                        "review_date": {"$gte": {"$date": "2019-01-01T00:00:00Z"}}}},
            {"$group": {"_id": {"ano": {"$year": "$review_date"}},
                        "total": {"$sum": 1}, "nota_media": {"$avg": "$rating"}}},
            {"$sort": {"_id.ano": 1}},
        ],
        "colecao": "reviews",
        "resultados": [
            {"ano": 2019, "total": 13820, "nota_media": 4.58},
            {"ano": 2020, "total": 21140, "nota_media": 4.61},
            {"ano": 2021, "total": 23705, "nota_media": 4.59},
            {"ano": 2022, "total": 18932, "nota_media": 4.55},
            {"ano": 2023, "total": 11077, "nota_media": 4.57},
        ],
        "explicacao": (
            "O volume de avaliações verificadas cresceu **71%** entre 2019 e 2021, "
            "com pico em **2021 (23.705)** — coerente com o aumento de compras online "
            "durante a pandemia.\n\n"
            "A queda em 2022 e 2023 tem duas leituras possíveis: retração real do "
            "volume ou corte da coleta em setembro de 2023 (a base vai até "
            "06/09/2023), o que deixa o último ano incompleto. A nota média é estável, "
            "entre 4,55 e 4,61, refletindo a distribuição em J da base inteira."
        ),
    },
}

EXEMPLOS = list(MOCK.keys())

ESQUEMA = {
    "reviews": ["rating: double", "title: string", "text: string", "asin: string",
                "parent_asin: string", "user_id: string", "review_date: date",
                "verified_purchase: bool", "helpful_vote: int", "images: array"],
    "products": ["parent_asin: string", "title: string", "main_category: string",
                 "average_rating: double", "rating_number: int", "price: double|null",
                 "store: string", "features: array", "categories: array",
                 "details: object", "images: array"],
}


def consultar_mock(pergunta: str):
    """Placeholder do orquestrador. Semana 2: chama core/orquestrador.py."""
    time.sleep(1.2)  # simula latência do LLM
    chave = pergunta.strip().lower()
    if chave in MOCK:
        return MOCK[chave]
    for k, v in MOCK.items():
        if any(p in chave for p in k.split() if len(p) > 4):
            return v
    return None


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
    st.warning("Modo protótipo — dados simulados", icon="⚠")
    st.caption("Banco: `datachat` · Coleções: `reviews`, `products`")

    st.markdown("### Esquema")
    for colecao, campos in ESQUEMA.items():
        with st.expander(f"`{colecao}`"):
            for campo in campos:
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
st.caption("Pergunte em português. A aplicação traduz para MongoDB, executa e explica o resultado. "
           "Base: Amazon Reviews 2023 · categoria Gift_Cards · 152.410 avaliações.")

st.divider()

pergunta = st.text_input(
    "Sua pergunta",
    value=st.session_state.pergunta_atual,
    placeholder="Ex.: quais produtos concentram mais avaliações?",
)

col_botao, col_exemplos = st.columns([1, 3])
with col_botao:
    consultar = st.button("Consultar", type="primary", use_container_width=True)
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
        time.sleep(0.3)
        st.write("Traduzindo a pergunta para MongoDB")
        resposta = consultar_mock(pergunta)
        st.write("Validando a consulta gerada")
        time.sleep(0.3)
        st.write("Executando no MongoDB")
        time.sleep(0.3)
        st.write("Redigindo a explicação")
        time.sleep(0.3)
        status.update(label="Pronto", state="complete", expanded=False)

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

if resposta is None and st.session_state.historico:
    st.error("Não consegui traduzir essa pergunta. Tente reformular ou use um dos exemplos.")

elif resposta:
    aba_resposta, aba_query, aba_dados = st.tabs(
        ["Explicação", "Consulta MongoDB", "Resultados"]
    )

    with aba_resposta:
        st.markdown(resposta["explicacao"])

    with aba_query:
        st.caption(f"Coleção: `{resposta['colecao']}` · "
                   f"{len(resposta['query'])} estágios de agregação")
        st.code(
            f"db.{resposta['colecao']}.aggregate(\n"
            + json.dumps(resposta["query"], indent=2, ensure_ascii=False)
            + "\n)",
            language="javascript",
        )

    with aba_dados:
        df = pd.DataFrame(resposta["resultados"])
        c1, c2 = st.columns([1, 1])
        c1.metric("Documentos retornados", len(df))
        c2.metric("Tempo de execução", "412 ms")
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
st.caption("Protótipo — Semana 1 · Integração com LLM e MongoDB prevista para a Semana 2.")
