"""
DataChat NoSQL — Contexto de esquema para o prompt do LLM (RF02 + RF03/RF04).

Não é só uma lista de nomes de campo: inclui o % de preenchimento medido em
scripts/perfilar.py. Sem isso o Gemini gera consultas filtrando por `price`
como se estivesse sempre presente, e devolve 2/3 a menos de resultado sem
avisar ninguém (ver Seção 1.5 do RELATORIO_SEMANA1.md).
"""

from pymongo.database import Database

CAMPOS_REVIEWS = [
    "rating", "title", "text", "asin", "parent_asin", "user_id",
    "timestamp", "review_date", "verified_purchase", "helpful_vote", "images",
]

CAMPOS_PRODUCTS = [
    "parent_asin", "title", "main_category", "average_rating", "rating_number",
    "price", "store", "features", "description", "categories", "details",
    "images", "videos",
]

TIPOS_CONHECIDOS = {
    "rating": "double (1.0 a 5.0)",
    "title": "string",
    "text": "string",
    "asin": "string",
    "parent_asin": "string — chave de junção reviews.parent_asin = products.parent_asin",
    "user_id": "string",
    "timestamp": "long (unix ms) — prefira review_date para consultas de data",
    "review_date": "date (BSON Date) — use $year, $month, $dateTrunc",
    "verified_purchase": "bool",
    "helpful_vote": "int",
    "images": "array<object>",
    "main_category": "string",
    "average_rating": "double",
    "rating_number": "int",
    "price": "double | null",
    "store": "string",
    "features": "array<string>",
    "description": "array<string>",
    "categories": "array<string>",
    "details": "object de esquema aberto — use $objectToArray para descobrir chaves",
    "videos": "array<object>",
}


def _preenchimento(db: Database, colecao: str, campos: list[str], total: int) -> list[str]:
    linhas = []
    for campo in campos:
        n = db[colecao].count_documents({campo: {"$exists": True, "$nin": [None, "", [], {}]}})
        pct = (n / total * 100) if total else 0.0
        tipo = TIPOS_CONHECIDOS.get(campo, "desconhecido")
        aviso = "" if pct >= 80 else f"  ← só {pct:.0f}% preenchido, cuidado ao filtrar"
        linhas.append(f"  - {campo}: {tipo} ({pct:.0f}% preenchido){aviso}")
    return linhas


def contexto_esquema(db: Database) -> str:
    """Gera a string de esquema + estatísticas reais que entra no prompt do tradutor."""
    total_reviews = db.reviews.count_documents({})
    total_products = db.products.count_documents({})

    partes = [
        f'Banco MongoDB "{db.name}" com duas coleções:',
        "",
        f"reviews ({total_reviews:,} documentos) — avaliações de produtos:",
        *_preenchimento(db, "reviews", CAMPOS_REVIEWS, total_reviews),
        "",
        f"products ({total_products:,} documentos) — metadados de produtos:",
        *_preenchimento(db, "products", CAMPOS_PRODUCTS, total_products),
        "",
        "Junção: reviews.parent_asin = products.parent_asin, via $lookup.",
        "Sem campo `category` com múltiplos valores nesta carga — todas as consultas",
        "de \"categoria\" devem usar `main_category` de products, não assumir várias categorias.",
    ]
    return "\n".join(partes)


def informacoes_colecao(db: Database, colecao: str) -> dict:
    """RF02 — campos existentes, tipos, exemplo de documento, quantidade de registros."""
    exemplo = db[colecao].find_one()
    if exemplo:
        exemplo = {k: (str(v) if k == "_id" else v) for k, v in exemplo.items()}
    return {
        "colecao": colecao,
        "quantidade_registros": db[colecao].count_documents({}),
        "campos": sorted(exemplo.keys()) if exemplo else [],
        "exemplo_documento": exemplo,
    }
