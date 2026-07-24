"""
DataChat NoSQL — Tradutor NL→MongoDB via Gemini (RF03 + RF04).

Escolha do LLM documentada em docs/comparacao_llms.txt: testamos Gemini
(gemini-flash-lite-latest) contra Llama 3.2 3B local nas 7 consultas do projeto.
Gemini acertou 7/7 (JSON válido + executou sem erro), Llama 3/7. Gemini também
é gratuito (free tier), o que elimina o custo como fator de decisão.

O modelo devolve {"colecao": ..., "pipeline": [...]}. Pipeline é sempre uma
lista de estágios de agregação — mesmo filtros simples viram um único estágio
$match, para manter uma única forma de execução em core/executor.py.
"""

import json
import os

from google import genai
from google.genai import types

MODELO = os.getenv("LLM_MODELO") or "gemini-flash-lite-latest"

# Três exemplos few-shot (README menciona "3 exemplos few-shot"), cobrindo os
# padrões mais difíceis de acertar: $lookup+$unwind e $objectToArray.
FEW_SHOT = [
    {
        "pergunta": "Quais as avaliações 5 estrelas mais úteis de compras verificadas?",
        "resposta": {
            "colecao": "reviews",
            "pipeline": [
                {"$match": {"rating": 5.0, "verified_purchase": True}},
                {"$sort": {"helpful_vote": -1}},
                {"$limit": 10},
                {"$project": {"_id": 0, "title": 1, "helpful_vote": 1, "parent_asin": 1}},
            ],
        },
    },
    {
        "pergunta": "Quais os produtos mais mal avaliados, com nome, loja e preço?",
        "resposta": {
            "colecao": "reviews",
            "pipeline": [
                {"$group": {"_id": "$parent_asin", "nota_media": {"$avg": "$rating"}, "total": {"$sum": 1}}},
                {"$match": {"total": {"$gte": 20}}},
                {"$sort": {"nota_media": 1}},
                {"$limit": 10},
                {"$lookup": {"from": "products", "localField": "_id",
                             "foreignField": "parent_asin", "as": "produto"}},
                {"$unwind": "$produto"},
                {"$project": {"_id": 0, "nome": "$produto.title", "loja": "$produto.store",
                              "preco": {"$ifNull": ["$produto.price", "não informado"]},
                              "nota_media": {"$round": ["$nota_media", 2]}}},
            ],
        },
    },
    {
        "pergunta": "Quais atributos existem em details e com que frequência aparecem?",
        "resposta": {
            "colecao": "products",
            "pipeline": [
                {"$match": {"details": {"$exists": True, "$ne": {}}}},
                {"$project": {"kv": {"$objectToArray": "$details"}}},
                {"$unwind": "$kv"},
                {"$group": {"_id": "$kv.k", "produtos": {"$sum": 1}}},
                {"$sort": {"produtos": -1}},
                {"$limit": 15},
            ],
        },
    },
]


class TradutorError(Exception):
    """A saída do LLM não veio como {"colecao": ..., "pipeline": [...]} válido."""


def _prompt_sistema(esquema_contexto: str) -> str:
    exemplos = "\n\n".join(
        f'Pergunta: "{ex["pergunta"]}"\nResposta: {json.dumps(ex["resposta"], ensure_ascii=False)}'
        for ex in FEW_SHOT
    )
    return f"""Você traduz perguntas em português para pipelines de agregação do MongoDB.

{esquema_contexto}

Responda APENAS com um objeto JSON no formato:
{{"colecao": "reviews" ou "products", "pipeline": [...]}}

"pipeline" é sempre uma lista de estágios de agregação (mesmo para filtros simples,
use um único estágio $match em vez de find()). Sempre inclua $limit (no máximo 100)
a menos que a pergunta peça uma contagem/agregação de valor único.

Exemplos:

{exemplos}

Sem markdown, sem explicação — só o objeto JSON.
"""


def traduzir(
    pergunta: str,
    esquema_contexto: str,
    cliente: "genai.Client",
    erro_anterior: str | None = None,
) -> dict:
    """Pergunta em português → {"colecao": str, "pipeline": list[dict]}.

    Se `erro_anterior` for passado (retry de autocorreção — ver
    core/orquestrador.py), o erro do MongoDB/parsing é devolvido ao modelo
    junto com a pergunta original para ele se corrigir.
    """
    mensagem = pergunta
    if erro_anterior:
        mensagem = (
            f"{pergunta}\n\n"
            f"Sua resposta anterior falhou com este erro, corrija:\n{erro_anterior}"
        )

    resposta = cliente.models.generate_content(
        model=MODELO,
        contents=mensagem,
        config=types.GenerateContentConfig(
            system_instruction=_prompt_sistema(esquema_contexto),
            temperature=0,
            response_mime_type="application/json",
        ),
    )

    texto = (resposta.text or "").strip()
    if texto.startswith("```"):
        texto = texto.split("```")[1].removeprefix("json").strip()

    try:
        dados = json.loads(texto)
    except json.JSONDecodeError as e:
        raise TradutorError(f"JSON inválido devolvido pelo modelo: {e}\nBruto: {texto[:500]}") from e

    if "colecao" not in dados or "pipeline" not in dados:
        raise TradutorError(f'Resposta sem "colecao"/"pipeline": {texto[:500]}')
    if dados["colecao"] not in ("reviews", "products"):
        raise TradutorError(f'Coleção desconhecida: {dados["colecao"]!r}')
    if not isinstance(dados["pipeline"], list) or not dados["pipeline"]:
        raise TradutorError("Pipeline vazio ou não é uma lista")

    return dados
