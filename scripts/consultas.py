"""
DataChat NoSQL — As sete consultas da Semana 1.

Roda todas as consultas e imprime os resultados formatados. A saída deste
script é a evidência para o item 3 da entrega.

Uso:
    python scripts/consultas.py            # roda todas
    python scripts/consultas.py --numero 4 # roda só a consulta 4
"""

import argparse
import json
import os
from datetime import datetime

from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
BANCO = os.getenv("MONGO_DB", "datachat")


def imprimir(titulo, pergunta, resultado, exercita):
    print("\n" + "=" * 78)
    print(titulo)
    print("=" * 78)
    print(f'Pergunta: "{pergunta}"')
    print(f"Exercita: {exercita}\n")
    print(json.dumps(resultado, indent=2, ensure_ascii=False, default=str))


def c1(db):
    """Filtro simples com projeção e ordenação."""
    r = list(db.reviews.find(
        {"rating": 5.0, "verified_purchase": True},
        {"title": 1, "helpful_vote": 1, "parent_asin": 1, "_id": 0}
    ).sort("helpful_vote", -1).limit(10))
    imprimir("CONSULTA 1 — Filtro, projeção e ordenação",
             "Quais as avaliações 5 estrelas mais úteis de compras verificadas?",
             r, "find, filtro composto, projeção, sort, limit")


def c2(db):
    """Agregação com agrupamento."""
    r = list(db.reviews.aggregate([
        {"$group": {"_id": "$rating", "total": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]))
    imprimir("CONSULTA 2 — Distribuição de notas",
             "Qual a distribuição das notas na base?",
             r, "$group, $sum")


def c3(db):
    """Ranking com $match pós-agrupamento (equivalente ao HAVING do SQL)."""
    r = list(db.reviews.aggregate([
        {"$group": {
            "_id": "$parent_asin",
            "nota_media": {"$avg": "$rating"},
            "total_avaliacoes": {"$sum": 1},
        }},
        {"$match": {"total_avaliacoes": {"$gte": 50}}},
        {"$sort": {"nota_media": -1}},
        {"$limit": 10},
    ]))
    imprimir("CONSULTA 3 — Melhores produtos com volume mínimo",
             "Quais os 10 produtos com melhor nota média, entre os que têm ao menos 50 avaliações?",
             r, "$avg, $match após $group (HAVING)")


def c4(db):
    """Junção entre coleções — a consulta-chave do projeto.

    price só existe em 33,4% dos produtos, então projetamos 'store' (98,5%)
    como atributo principal e tratamos o preço ausente com $ifNull em vez de
    filtrar — filtrar descartaria 2/3 do catálogo.
    """
    r = list(db.reviews.aggregate([
        {"$group": {
            "_id": "$parent_asin",
            "nota_media": {"$avg": "$rating"},
            "total": {"$sum": 1},
        }},
        {"$match": {"total": {"$gte": 20}}},
        {"$sort": {"nota_media": 1}},
        {"$limit": 10},
        {"$lookup": {
            "from": "products",
            "localField": "_id",
            "foreignField": "parent_asin",
            "as": "produto",
        }},
        {"$unwind": "$produto"},
        {"$project": {
            "_id": 0,
            "parent_asin": "$_id",
            "nome": "$produto.title",
            "loja": "$produto.store",
            "preco": {"$ifNull": ["$produto.price", "não informado"]},
            "nota_media": {"$round": ["$nota_media", 2]},
            "total": 1,
        }},
    ]))
    imprimir("CONSULTA 4 — Junção reviews × products ($lookup)",
             "Quais os produtos mais mal avaliados, com nome, loja e preço?",
             r, "$lookup, $unwind, $ifNull, $project — prova que o modelo referenciado funciona")


def c5(db):
    """Série temporal usando o campo review_date derivado no ETL."""
    r = list(db.reviews.aggregate([
        {"$match": {"review_date": {"$gte": datetime(2018, 1, 1)}}},
        {"$group": {
            "_id": {"ano": {"$year": "$review_date"}},
            "total": {"$sum": 1},
            "nota_media": {"$avg": "$rating"},
        }},
        {"$sort": {"_id.ano": 1}},
    ]))
    imprimir("CONSULTA 5 — Evolução temporal",
             "Como evoluiu o volume de avaliações e a nota média por ano, de 2018 em diante?",
             r, "$year sobre review_date, $match antes do $group (usa índice)")


def c6(db):
    """Busca textual — termos do domínio de vale-presente."""
    r = list(db.reviews.find(
        {"$text": {"$search": "never received scam refund"}, "rating": {"$lte": 2.0}},
        {"score": {"$meta": "textScore"}, "title": 1, "text": 1, "rating": 1, "_id": 0}
    ).sort([("score", {"$meta": "textScore"})]).limit(10))
    for d in r:
        if len(d.get("text", "")) > 200:
            d["text"] = d["text"][:200] + "..."
    imprimir("CONSULTA 6 — Busca textual",
             "O que reclamam os clientes que não receberam o vale-presente?",
             r, "índice de texto, $text, $meta textScore")


def c7(db):
    """Descoberta dinâmica de esquema — o argumento a favor do NoSQL.

    Em vez de assumir que 'details.Brand' existe, a consulta DESCOBRE quais
    atributos existem e com que frequência. Impossível de escrever em SQL sem
    conhecer as colunas de antemão — é exatamente o ponto do modelo de documentos.
    """
    r = list(db.products.aggregate([
        {"$match": {"details": {"$exists": True, "$ne": {}}}},
        {"$project": {"kv": {"$objectToArray": "$details"}}},
        {"$unwind": "$kv"},
        {"$group": {
            "_id": "$kv.k",
            "produtos": {"$sum": 1},
            "exemplo": {"$first": "$kv.v"},
        }},
        {"$sort": {"produtos": -1}},
        {"$limit": 15},
    ]))
    imprimir("CONSULTA 7 — Descoberta de esquema em documento aberto",
             "Quais atributos existem em 'details' e com que frequência aparecem?",
             r, "$objectToArray, $unwind, $group — esquema descoberto em tempo de consulta")


def verificar_carga(db):
    print("=" * 78)
    print("VERIFICAÇÃO DA CARGA")
    print("=" * 78)
    print(f"  reviews  : {db.reviews.count_documents({}):,} documentos")
    print(f"  products : {db.products.count_documents({}):,} documentos")
    print("\n  Índices em reviews:")
    for nome in db.reviews.index_information():
        print(f"    · {nome}")
    print("\n  Índices em products:")
    for nome in db.products.index_information():
        print(f"    · {nome}")


def explain_demo(db):
    """Mostra a árvore de execução real — prova que o FILTRO usa índice (sem COLLSCAN)."""
    plano = db.reviews.find(
        {"rating": 5.0, "verified_purchase": True}
    ).sort("helpful_vote", -1).limit(10).explain()
    stats = plano.get("executionStats", {})

    def achatar(estagio):
        """Lista os estágios de fora para dentro: [SORT, FETCH, IXSCAN, ...]."""
        nomes = []
        while estagio:
            nomes.append(estagio.get("stage"))
            estagio = estagio.get("inputStage")
        return nomes

    pilha = achatar(stats.get("executionStages", {}))

    print("\n" + "=" * 78)
    print("EXPLAIN — Consulta 1")
    print("=" * 78)
    print(f"  Documentos retornados : {stats.get('nReturned')}")
    print(f"  Documentos examinados : {stats.get('totalDocsExamined')}")
    print(f"  Chaves examinadas ... : {stats.get('totalKeysExamined')}")
    print(f"  Tempo (ms) .......... : {stats.get('executionTimeMillis')}")
    print(f"  Árvore de execução .. : {' → '.join(pilha)}")
    if "COLLSCAN" in pilha:
        print("  → COLLSCAN: o filtro NÃO usou índice — varredura completa da coleção.")
    elif "IXSCAN" in pilha:
        print("  → IXSCAN presente: o filtro (verified_purchase, rating) usa o índice composto.")
        if pilha[0] == "SORT":
            print("  → mas o estágio externo é SORT: a ordenação por 'helpful_vote' não está")
            print("    coberta pelo índice, então o Mongo ordena em memória os documentos já")
            print("    filtrados. Para eliminar esse SORT seria preciso um índice composto")
            print("    (verified_purchase, rating, helpful_vote).")


def c8(db):
    """Concentração — o achado mais interessante desta base.

    Um único produto concentra ~24% de todas as avaliações. Esta consulta
    quantifica isso e nomeia o produto.
    """
    total = db.reviews.count_documents({})
    r = list(db.reviews.aggregate([
        {"$group": {"_id": "$parent_asin", "avaliacoes": {"$sum": 1},
                    "nota_media": {"$avg": "$rating"}}},
        {"$sort": {"avaliacoes": -1}},
        {"$limit": 5},
        {"$lookup": {"from": "products", "localField": "_id",
                     "foreignField": "parent_asin", "as": "p"}},
        {"$unwind": "$p"},
        {"$project": {
            "_id": 0,
            "nome": "$p.title",
            "avaliacoes": 1,
            "nota_media": {"$round": ["$nota_media", 2]},
            "pct_da_base": {"$round": [
                {"$multiply": [{"$divide": ["$avaliacoes", total]}, 100]}, 1]},
        }},
    ]))
    imprimir("CONSULTA 8 — Concentração da base",
             "Quais produtos concentram mais avaliações, e que fatia da base representam?",
             r, "$divide, $multiply, $round — cauda longa extrema")


CONSULTAS = {1: c1, 2: c2, 3: c3, 4: c4, 5: c5, 6: c6, 7: c7, 8: c8}

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--numero", type=int, choices=list(CONSULTAS))
    args = p.parse_args()

    db = MongoClient(MONGO_URI)[BANCO]

    if args.numero:
        CONSULTAS[args.numero](db)
    else:
        verificar_carga(db)
        for fn in CONSULTAS.values():
            fn(db)
        explain_demo(db)
