"""
DataChat NoSQL — Orquestrador (RF09: retry de autocorreção + tratamento de erro).

Sequencia: esquema → tradutor (LLM) → validador → executor → explicador (LLM).
Se tradutor, validador ou executor falharem, o erro cru volta para o tradutor
uma única vez ("retry único com autocorreção" — Seção 4.3 do relatório).
Falhando de novo, devolve um erro amigável em vez de estourar exceção na UI.
"""

import os
import time

from google import genai
from pymongo.database import Database

from core.esquema import contexto_esquema
from core.executor import ExecutorError, executar
from core.explicador import explicar
from core.tradutor import TradutorError, traduzir
from core.validador import ValidadorError, validar

_cache_esquema: dict[str, str] = {}


def _obter_cliente() -> "genai.Client":
    chave = os.getenv("GOOGLE_API_KEY")
    if not chave:
        raise RuntimeError(
            "GOOGLE_API_KEY não definida no .env — gere uma chave gratuita em "
            "https://aistudio.google.com/apikey"
        )
    return genai.Client(api_key=chave)


def _esquema_cacheado(db: Database) -> str:
    """O esquema não muda durante a sessão — evita recontar 152 mil documentos a cada pergunta."""
    if db.name not in _cache_esquema:
        _cache_esquema[db.name] = contexto_esquema(db)
    return _cache_esquema[db.name]


def responder(pergunta: str, db: Database, cliente: "genai.Client | None" = None) -> dict:
    """Executa o fluxo completo para uma pergunta em português.

    Retorna sempre um dict com a mesma forma (mesmo em erro), para a interface
    não precisar tratar exceção — RF09.
    """
    inicio = time.time()
    pergunta = pergunta.strip()

    if not pergunta:
        return _erro(pergunta, "Digite uma pergunta antes de consultar.")

    if cliente is None:
        try:
            cliente = _obter_cliente()
        except RuntimeError as e:
            return _erro(pergunta, str(e))

    esquema = _esquema_cacheado(db)

    erro_anterior = None
    ultimo_erro = None

    for tentativa in range(2):  # tentativa original + 1 retry de autocorreção
        try:
            dados = traduzir(pergunta, esquema, cliente, erro_anterior=erro_anterior)
            pipeline = validar(dados["colecao"], dados["pipeline"])
            resultados = executar(db, dados["colecao"], pipeline)

            explicacao = explicar(pergunta, resultados, cliente)

            return {
                "pergunta": pergunta,
                "colecao": dados["colecao"],
                "pipeline": pipeline,
                "resultados": resultados,
                "explicacao": explicacao,
                "erro": None,
                "tempo_s": round(time.time() - inicio, 1),
                "tentativas": tentativa + 1,
            }

        except (TradutorError, ValidadorError, ExecutorError) as e:
            ultimo_erro = e
            erro_anterior = str(e)
            continue

    return _erro(
        pergunta,
        "Não consegui gerar uma consulta válida para essa pergunta depois de "
        "tentar corrigir uma vez. Tente reformular — pode ser um campo que "
        "não existe na base, ou uma pergunta ambígua demais.",
        detalhe_tecnico=str(ultimo_erro),
        tempo_s=round(time.time() - inicio, 1),
    )


def _erro(pergunta: str, mensagem: str, detalhe_tecnico: str = "", tempo_s: float = 0.0) -> dict:
    return {
        "pergunta": pergunta,
        "colecao": None,
        "pipeline": None,
        "resultados": None,
        "explicacao": None,
        "erro": mensagem,
        "detalhe_tecnico": detalhe_tecnico,
        "tempo_s": tempo_s,
        "tentativas": 0,
    }
