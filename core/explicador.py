"""
DataChat NoSQL — Explicador de resultados via Gemini (RF06).

Segunda chamada ao LLM, separada da tradução (Seção 4.4b do relatório):
traduzir pede saída estruturada e temperatura 0; explicar se beneficia de
redigir em português natural. Junta os dois numa função só faria o prompt de
tradução carregar instrução de estilo de escrita à toa.
"""

import json
import os

from google import genai
from google.genai import types

MODELO = os.getenv("LLM_MODELO") or "gemini-flash-lite-latest"

MAX_DOCUMENTOS_NO_PROMPT = 30  # corta o payload para não estourar o contexto à toa

PROMPT_SISTEMA = """Você explica, em português, o resultado de uma consulta MongoDB
para quem fez a pergunta em linguagem natural. Seja direto: responda a pergunta
primeiro, cite números concretos do resultado, e só depois aponte um padrão ou
observação relevante se houver. Não repita a pergunta. Não invente números que
não estão no resultado. No máximo um parágrafo curto.
"""


def explicar(pergunta: str, resultados: list[dict], cliente: "genai.Client") -> str:
    """Resultado do MongoDB → explicação em português (RF06)."""
    if not resultados:
        return (
            "A consulta rodou sem erro, mas não retornou nenhum documento. "
            "Isso pode significar que o filtro é específico demais para os dados "
            "carregados, ou que a pergunta assume algo que não existe nesta base "
            "(ver o esquema na barra lateral)."
        )

    amostra = resultados[:MAX_DOCUMENTOS_NO_PROMPT]
    mensagem = (
        f'Pergunta original: "{pergunta}"\n\n'
        f"Resultado da consulta ({len(resultados)} documento(s), "
        f"mostrando até {MAX_DOCUMENTOS_NO_PROMPT}):\n"
        f"{json.dumps(amostra, ensure_ascii=False, indent=2)}"
    )

    resposta = cliente.models.generate_content(
        model=MODELO,
        contents=mensagem,
        config=types.GenerateContentConfig(
            system_instruction=PROMPT_SISTEMA,
            temperature=0.7,
        ),
    )
    return (resposta.text or "").strip()
