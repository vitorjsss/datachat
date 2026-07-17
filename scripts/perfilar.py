"""
DataChat NoSQL — Perfilamento da base.

Roda DEPOIS da importação. Extrai os números reais que vão para o relatório
e avisa quais campos estão vazios ou inúteis no recorte escolhido.

A saída deste script substitui as estimativas do site pelos seus números.

Uso:
    python scripts/perfilar.py
"""

import os
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
BANCO = os.getenv("MONGO_DB", "datachat")

db = MongoClient(MONGO_URI)[BANCO]


def secao(titulo):
    print("\n" + "=" * 72)
    print(titulo)
    print("=" * 72)


def preenchimento(colecao, campos):
    """% de documentos em que o campo existe e não é nulo/vazio.

    É o teste que decide se uma consulta faz sentido: agrupar por um campo
    preenchido em 2% dos documentos não gera resultado apresentável.
    """
    total = db[colecao].count_documents({})
    if total == 0:
        print(f"  Coleção '{colecao}' está VAZIA — a importação falhou.")
        return
    print(f"  {colecao}: {total:,} documentos\n")
    print(f"  {'campo':<26} {'preenchido':>12} {'%':>7}   status")
    print("  " + "-" * 62)
    for campo in campos:
        n = db[colecao].count_documents(
            {campo: {"$exists": True, "$nin": [None, "", [], {}]}}
        )
        pct = n / total * 100
        if pct >= 80:
            status = "ok"
        elif pct >= 20:
            status = "parcial — cuidado"
        else:
            status = "INUTILIZÁVEL"
        print(f"  {campo:<26} {n:>12,} {pct:>6.1f}%   {status}")


secao("1. CONTAGEM DE DOCUMENTOS")
print(f"  reviews  : {db.reviews.count_documents({}):,}")
print(f"  products : {db.products.count_documents({}):,}")
print(f"  usuários distintos : {len(db.reviews.distinct('user_id')):,}")
print(f"  produtos com review: {len(db.reviews.distinct('parent_asin')):,}")

secao("2. PREENCHIMENTO DOS CAMPOS — reviews")
preenchimento("reviews", [
    "rating", "title", "text", "asin", "parent_asin", "user_id",
    "review_date", "verified_purchase", "helpful_vote", "images",
])

secao("3. PREENCHIMENTO DOS CAMPOS — products")
preenchimento("products", [
    "parent_asin", "title", "main_category", "average_rating", "rating_number",
    "price", "store", "features", "description", "categories", "details",
    "images", "videos", "bought_together",
])

secao("4. CHAVES REAIS DENTRO DE 'details'")
print("  (esquema aberto — varia por produto; é o argumento a favor do NoSQL)\n")
chaves = list(db.products.aggregate([
    {"$match": {"details": {"$exists": True, "$ne": {}}}},
    {"$project": {"kv": {"$objectToArray": "$details"}}},
    {"$unwind": "$kv"},
    {"$group": {"_id": "$kv.k", "n": {"$sum": 1}}},
    {"$sort": {"n": -1}},
    {"$limit": 20},
]))
if not chaves:
    print("  Nenhuma chave encontrada — 'details' está vazio nesta categoria.")
else:
    for c in chaves:
        print(f"    {c['_id']:<34} {c['n']:>7,} produtos")

secao("5. DISTRIBUIÇÃO DE NOTAS")
total_r = db.reviews.count_documents({})
for d in db.reviews.aggregate([
    {"$group": {"_id": "$rating", "n": {"$sum": 1}}},
    {"$sort": {"_id": 1}},
]):
    barra = "█" * int(d["n"] / total_r * 50)
    print(f"  {d['_id']:.0f}★  {d['n']:>9,}  {d['n']/total_r*100:>5.1f}%  {barra}")

secao("6. FAIXA TEMPORAL")
p = list(db.reviews.find({"review_date": {"$ne": None}}, {"review_date": 1})
         .sort("review_date", 1).limit(1))
u = list(db.reviews.find({"review_date": {"$ne": None}}, {"review_date": 1})
         .sort("review_date", -1).limit(1))
if p and u:
    print(f"  Mais antiga : {p[0]['review_date']}")
    print(f"  Mais recente: {u[0]['review_date']}")
else:
    print("  review_date não foi gerado — verifique a importação.")

secao("7. AVALIAÇÕES POR PRODUTO")
for d in db.reviews.aggregate([
    {"$group": {"_id": "$parent_asin", "n": {"$sum": 1}}},
    {"$group": {"_id": None, "media": {"$avg": "$n"}, "max": {"$max": "$n"},
                "min": {"$min": "$n"}, "produtos": {"$sum": 1}}},
]):
    print(f"  Produtos com avaliação : {d['produtos']:,}")
    print(f"  Média por produto ..... : {d['media']:.1f}")
    print(f"  Máximo / mínimo ....... : {d['max']:,} / {d['min']}")
    print("\n  → use isso para calibrar o corte das Consultas 3 e 4")
    print("    (se a média for baixa, $gte: 50 devolve pouca coisa)")

secao("8. TAMANHO NO DISCO")
s = db.command("dbStats")
print(f"  Dados   : {s.get('storageSize', 0)/1024**2:>8.1f} MB")
print(f"  Índices : {s.get('indexSize', 0)/1024**2:>8.1f} MB")
print(f"  Total   : {(s.get('storageSize',0)+s.get('indexSize',0))/1024**2:>8.1f} MB")

print("\n" + "=" * 72)
print("Leve estes números para o relatório. As estimativas do site são")
print("aproximações — o professor pode conferir os seus.")
print("=" * 72)
