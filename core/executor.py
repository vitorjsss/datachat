"""
DataChat NoSQL — Executor MongoDB (RF05).

Só recebe pipelines que já passaram por core/validador.py. Serializa
ObjectId/Date para tipos que o Streamlit e o json.dumps sabem exibir, e limita
o tempo de execução para não travar a interface numa consulta cara.
"""

from datetime import date, datetime

from bson import ObjectId
from pymongo.database import Database
from pymongo.errors import PyMongoError

TIMEOUT_MS = 15000


class ExecutorError(Exception):
    """Erro do MongoDB ao rodar o pipeline — mensagem crua, para o retry de autocorreção."""


def _serializar(valor):
    if isinstance(valor, ObjectId):
        return str(valor)
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    if isinstance(valor, dict):
        return {k: _serializar(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_serializar(v) for v in valor]
    return valor


def executar(db: Database, colecao: str, pipeline: list[dict]) -> list[dict]:
    """Roda o pipeline (já validado) via aggregate() e devolve documentos serializáveis em JSON."""
    try:
        cursor = db[colecao].aggregate(pipeline, maxTimeMS=TIMEOUT_MS)
        return [_serializar(doc) for doc in cursor]
    except PyMongoError as e:
        raise ExecutorError(str(e)) from e
