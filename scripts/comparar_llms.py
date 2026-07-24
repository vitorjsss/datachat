"""
DataChat NoSQL — Comparação Llama 3.2 3B (local, Ollama) vs Gemini (gemini-flash-lite-latest, nuvem, free tier).

Roda as mesmas perguntas nos dois modelos, pedindo um pipeline MongoDB em JSON,
e reporta: se o JSON veio válido, se o pipeline rodou sem erro no Mongo, quantos
documentos voltaram, e o tempo de resposta. É a evidência para a Seção 5 do
relatório ("análise crítica das tecnologias").

Requer:
    - Ollama rodando localmente com `ollama pull llama3.2:3b`
    - GOOGLE_API_KEY no .env (gratuito em https://aistudio.google.com/apikey)
    - MongoDB carregado (rode scripts/importar_mongo.py antes)

Uso:
    python scripts/comparar_llms.py
"""

import json
import os
import time
from datetime import datetime

import ollama
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
BANCO = os.getenv("MONGO_DB", "datachat")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ARQUIVO_LOG = "docs/comparacao_llms.txt"

OLLAMA_MODELO = "llama3.2:3b"
GEMINI_MODELO = "gemini-flash-lite-latest"

# ─────────────────────────────────────────────────────────────────────
# Contexto de esquema — mesma info que vai para core/esquema.py na Semana 2
# ─────────────────────────────────────────────────────────────────────

ESQUEMA = """
Banco MongoDB "datachat" com duas coleções:

reviews (avaliações de produtos):
  rating: double (1.0 a 5.0) | title: string | text: string | asin: string
  parent_asin: string (chave de junção com products) | user_id: string
  review_date: date | verified_purchase: bool | helpful_vote: int

products (metadados de produtos):
  parent_asin: string | title: string | main_category: string
  average_rating: double | rating_number: int | price: double (pode ser null)
  store: string | features: array<string> | categories: array<string>
  details: object (esquema aberto)

Junção reviews x products é feita por parent_asin usando $lookup.
""".strip()

PROMPT_SISTEMA = f"""Você traduz perguntas em português para pipelines de agregação do MongoDB.

{ESQUEMA}

Responda APENAS com um array JSON válido representando os estágios do pipeline
(ex.: [{{"$match": {{...}}}}, {{"$group": {{...}}}}]). Sem explicação, sem markdown,
sem texto antes ou depois — só o JSON do array.
"""

PERGUNTAS = [
    "Quais as avaliações 5 estrelas mais úteis de compras verificadas? Traga só título, votos úteis e id do produto, ordenado por votos úteis, no máximo 10.",
    "Qual a distribuição das notas na base?",
    "Quais os 10 produtos com melhor nota média, entre os que têm pelo menos 50 avaliações?",
    "Quais os produtos mais mal avaliados, com nome, loja e preço? Considere só produtos com pelo menos 20 avaliações, no máximo 10.",
    "Como evoluiu o volume de avaliações e a nota média por ano, a partir de 2018?",
    "Quais atributos existem no campo details dos produtos e com que frequência aparecem? No máximo 15.",
    "Quais os 5 produtos que concentram mais avaliações, com nome e nota média?",
]


def extrair_json(texto: str):
    """Modelos às vezes envolvem o JSON em ```json ... ``` — remove antes de parsear."""
    texto = texto.strip()
    if texto.startswith("```"):
        texto = texto.split("```")[1]
        texto = texto.removeprefix("json").strip()
    return json.loads(texto)


def perguntar_ollama(pergunta: str) -> tuple[str, float]:
    inicio = time.time()
    resposta = ollama.chat(
        model=OLLAMA_MODELO,
        messages=[
            {"role": "system", "content": PROMPT_SISTEMA},
            {"role": "user", "content": pergunta},
        ],
        options={"temperature": 0},
    )
    return resposta["message"]["content"], time.time() - inicio


def perguntar_gemini(cliente: "genai.Client", pergunta: str) -> tuple[str, float]:
    inicio = time.time()
    resposta = cliente.models.generate_content(
        model=GEMINI_MODELO,
        contents=pergunta,
        config=types.GenerateContentConfig(
            system_instruction=PROMPT_SISTEMA,
            temperature=0,
            response_mime_type="application/json",
        ),
    )
    return resposta.text, time.time() - inicio


def avaliar(nome: str, texto_bruto: str, tempo: float, db) -> dict:
    linha = {"modelo": nome, "tempo_s": round(tempo, 1), "json_valido": False,
             "executou": False, "documentos": None, "erro": None}
    try:
        pipeline = extrair_json(texto_bruto)
        linha["json_valido"] = True
    except Exception as e:
        linha["erro"] = f"JSON inválido: {e}"
        return linha

    try:
        resultado = list(db.reviews.aggregate(pipeline, maxTimeMS=15000))
        linha["executou"] = True
        linha["documentos"] = len(resultado)
    except PyMongoError as e:
        linha["erro"] = f"Erro no MongoDB: {e}"
    return linha


def escrever(f, *args):
    """Espelha print() na tela e no arquivo de log, sem truncar nada."""
    texto = " ".join(str(a) for a in args)
    print(texto)
    f.write(texto + "\n")


def main():
    db = MongoClient(MONGO_URI)[BANCO]

    if not GOOGLE_API_KEY:
        print("AVISO: GOOGLE_API_KEY não definida no .env — pulando Gemini.")
        cliente_gemini = None
    else:
        cliente_gemini = genai.Client(api_key=GOOGLE_API_KEY)

    os.makedirs(os.path.dirname(ARQUIVO_LOG), exist_ok=True)
    linhas = []

    with open(ARQUIVO_LOG, "w", encoding="utf-8") as f:
        escrever(f, "DataChat NoSQL — Comparação Llama 3.2 3B (local) vs Gemini (nuvem)")
        escrever(f, f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        escrever(f, f"Modelos: {OLLAMA_MODELO} (Ollama, local) | {GEMINI_MODELO} (Google, nuvem)")

        for i, pergunta in enumerate(PERGUNTAS, 1):
            escrever(f, f"\n{'=' * 78}\nPergunta {i}: {pergunta}\n{'=' * 78}")

            escrever(f, "\n--- INPUT enviado (idêntico para os dois modelos) ---")
            escrever(f, f"[system instruction]\n{PROMPT_SISTEMA}")
            escrever(f, f"[user]\n{pergunta}")

            escrever(f, "\n--- OUTPUT: Llama 3.2 3B (local) ---")
            texto, tempo = perguntar_ollama(pergunta)
            linha = avaliar("Llama 3.2 3B (local)", texto, tempo, db)
            linha["pergunta"] = i
            linhas.append(linha)
            escrever(f, texto)
            escrever(f, f"[avaliação] {linha}")

            if cliente_gemini:
                escrever(f, "\n--- OUTPUT: Gemini (gemini-flash-lite-latest, nuvem) ---")
                texto, tempo = perguntar_gemini(cliente_gemini, pergunta)
                linha = avaliar("Gemini (gemini-flash-lite-latest)", texto, tempo, db)
                linha["pergunta"] = i
                linhas.append(linha)
                escrever(f, texto)
                escrever(f, f"[avaliação] {linha}")

        escrever(f, f"\n\n{'=' * 78}\nRESUMO\n{'=' * 78}")
        for nome in sorted({l["modelo"] for l in linhas}):
            do_modelo = [l for l in linhas if l["modelo"] == nome]
            validos = sum(l["json_valido"] for l in do_modelo)
            executados = sum(l["executou"] for l in do_modelo)
            tempo_medio = sum(l["tempo_s"] for l in do_modelo) / len(do_modelo)
            escrever(f, f"\n{nome}:")
            escrever(f, f"  JSON válido:        {validos}/{len(do_modelo)}")
            escrever(f, f"  Executou sem erro:  {executados}/{len(do_modelo)}")
            escrever(f, f"  Tempo médio:        {tempo_medio:.1f}s")

    print(f"\nLog completo salvo em: {ARQUIVO_LOG}")


if __name__ == "__main__":
    main()
