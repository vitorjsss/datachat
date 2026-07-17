"""
DataChat NoSQL — Importação do Amazon Reviews 2023 para o MongoDB.

Lê arquivos .jsonl.gz em streaming (sem descompactar em disco), converte o
timestamp Unix em BSON Date e insere em lotes.

Uso:
    python scripts/importar_mongo.py --arquivo data/Gift_Cards.jsonl.gz --colecao reviews
    python scripts/importar_mongo.py --arquivo data/meta_Gift_Cards.jsonl.gz --colecao products

Baixe os arquivos em https://amazon-reviews-2023.github.io/ (tabela "Grouped by Category").
"""

import argparse
import gzip
import json
import os
import sys
import time
from datetime import datetime, timezone

from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.errors import BulkWriteError

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
BANCO = os.getenv("MONGO_DB", "datachat")
TAMANHO_LOTE = 5000


def abrir(caminho):
    """Abre .jsonl ou .jsonl.gz de forma transparente."""
    if caminho.endswith(".gz"):
        return gzip.open(caminho, "rt", encoding="utf-8")
    return open(caminho, "r", encoding="utf-8")


def transformar_review(doc):
    """Converte o timestamp Unix (ms) em BSON Date.

    Sem esse campo os operadores $year, $month e $dateTrunc não funcionam,
    e toda pergunta temporal exigiria aritmética manual no pipeline.
    """
    ts = doc.get("timestamp")
    if isinstance(ts, (int, float)) and ts > 0:
        doc["review_date"] = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
    return doc


def transformar_produto(doc):
    """Normaliza price para float. Vem como null ou string em parte dos registros."""
    preco = doc.get("price")
    if isinstance(preco, str):
        try:
            doc["price"] = float(preco.replace("$", "").replace(",", "").strip())
        except ValueError:
            doc["price"] = None
    return doc


# ─────────────────────────────────────────────────────────────────────
# MODO ENXUTO — para caber nos 512 MB do Atlas Free
# ─────────────────────────────────────────────────────────────────────
# Os campos abaixo respondem pela maior parte do volume e não são usados
# por nenhuma das 7 consultas. Descartá-los reduz o banco em ~70% sem
# perder nada que o projeto precise.

DESCARTAR_REVIEW = ["images"]
DESCARTAR_PRODUTO = ["images", "videos", "description", "features", "bought_together"]

LIMITE_TEXTO = 600  # caracteres; a mediana das reviews fica bem abaixo disso


def enxugar_review(doc):
    for campo in DESCARTAR_REVIEW:
        doc.pop(campo, None)
    texto = doc.get("text")
    if isinstance(texto, str) and len(texto) > LIMITE_TEXTO:
        doc["text"] = texto[:LIMITE_TEXTO]
        doc["texto_truncado"] = True
    return doc


def enxugar_produto(doc):
    for campo in DESCARTAR_PRODUTO:
        doc.pop(campo, None)
    return doc


def criar_indices(db, colecao):
    """Índices justificados pelas consultas da Seção 3 do relatório."""
    if colecao == "reviews":
        db.reviews.create_index([("parent_asin", ASCENDING)])
        db.reviews.create_index([("user_id", ASCENDING)])
        db.reviews.create_index([("rating", ASCENDING)])
        db.reviews.create_index([("review_date", DESCENDING)])
        db.reviews.create_index([("verified_purchase", ASCENDING), ("rating", DESCENDING)])
        db.reviews.create_index([("title", TEXT), ("text", TEXT)], name="busca_textual")
    elif colecao == "products":
        db.products.create_index([("parent_asin", ASCENDING)], unique=True)
        db.products.create_index([("store", ASCENDING)])
        db.products.create_index([("price", ASCENDING)])
        db.products.create_index([("main_category", ASCENDING)])
    print(f"  Índices criados em '{colecao}'.")


def importar(arquivo, colecao, limite=None, recriar=False, enxuto=False):
    if not os.path.exists(arquivo):
        sys.exit(f"Arquivo não encontrado: {arquivo}\nBaixe em https://amazon-reviews-2023.github.io/")

    if "mongodb+srv" in MONGO_URI:
        print("  Destino: MongoDB Atlas (nuvem)")
        if not enxuto:
            print("  Aviso: o plano gratuito tem 512 MB. Considere --enxuto.")
    else:
        print("  Destino: MongoDB local")

    cliente = MongoClient(MONGO_URI)
    db = cliente[BANCO]
    col = db[colecao]

    if recriar:
        col.drop()
        print(f"  Coleção '{colecao}' removida.")

    if colecao == "reviews":
        base = transformar_review
        corte = enxugar_review
    else:
        base = transformar_produto
        corte = enxugar_produto

    transformar = (lambda d: corte(base(d))) if enxuto else base
    if enxuto:
        print("  Modo enxuto: descartando campos pesados não usados pelas consultas.")

    inicio = time.time()
    lote, inseridos, invalidos = [], 0, 0

    print(f"Importando {arquivo} → {BANCO}.{colecao}")

    with abrir(arquivo) as fp:
        for numero_linha, linha in enumerate(fp, 1):
            linha = linha.strip()
            if not linha:
                continue
            try:
                # JSON Lines: um documento por linha. json.load() no arquivo inteiro FALHA.
                lote.append(transformar(json.loads(linha)))
            except json.JSONDecodeError:
                invalidos += 1
                continue

            if len(lote) >= TAMANHO_LOTE:
                inseridos += gravar(col, lote)
                lote = []
                print(f"  {inseridos:>8,} documentos...", end="\r")

            if limite and numero_linha >= limite:
                break

    if lote:
        inseridos += gravar(col, lote)

    duracao = time.time() - inicio
    total = col.count_documents({})

    print(f"\n  Inseridos ...... {inseridos:,}")
    print(f"  Linhas inválidas  {invalidos:,}")
    print(f"  Tempo .......... {duracao:.1f}s ({inseridos/max(duracao,1):,.0f} docs/s)")
    print(f"  Total na coleção  {total:,}")

    criar_indices(db, colecao)

    # Espaço ocupado — decisivo se o destino for o Atlas Free (512 MB)
    try:
        s = db.command("collStats", colecao)
        dados_mb = s.get("storageSize", 0) / 1024**2
        indices_mb = s.get("totalIndexSize", 0) / 1024**2
        total_mb = (db.command("dbStats").get("storageSize", 0)
                    + db.command("dbStats").get("indexSize", 0)) / 1024**2
        print(f"\n  Espaço — dados {dados_mb:.1f} MB · índices {indices_mb:.1f} MB")
        print(f"  Banco '{BANCO}' inteiro: {total_mb:.1f} MB")
        if "mongodb+srv" in MONGO_URI:
            print(f"  Cota do Atlas Free: {total_mb/512*100:.0f}% de 512 MB usados")
    except Exception:
        pass

    print("\n  Documento de exemplo:")
    exemplo = col.find_one()
    if exemplo:
        exemplo.pop("_id", None)
        print(json.dumps(exemplo, indent=2, ensure_ascii=False, default=str)[:900])

    cliente.close()


def gravar(col, lote):
    """ordered=False: uma falha não aborta o lote inteiro."""
    try:
        return len(col.insert_many(lote, ordered=False).inserted_ids)
    except BulkWriteError as e:
        return e.details.get("nInserted", 0)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Importa Amazon Reviews 2023 para o MongoDB")
    p.add_argument("--arquivo", required=True, help="Caminho do .jsonl ou .jsonl.gz")
    p.add_argument("--colecao", required=True, choices=["reviews", "products"])
    p.add_argument("--limite", type=int, help="Importar apenas as N primeiras linhas (teste)")
    p.add_argument("--recriar", action="store_true", help="Apagar a coleção antes de importar")
    p.add_argument("--enxuto", action="store_true",
                   help="Descartar campos pesados (images, videos, description...) "
                        "para caber nos 512 MB do Atlas Free")
    args = p.parse_args()

    importar(args.arquivo, args.colecao, args.limite, args.recriar, args.enxuto)
