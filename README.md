# DataChat NoSQL

Interface de consulta em linguagem natural sobre o dataset **Amazon Reviews 2023**.
O usuário pergunta em português, um LLM traduz para uma consulta MongoDB, o sistema
executa e devolve a resposta explicada.

> Projeto acadêmico — _(Tópicos Especiais em Computação, 2026.1)_

---

## Como funciona

```
Pergunta em português
        ↓
Contexto de esquema  →  LLM (tradutor)  →  Validador de segurança
        ↓
MongoDB (aggregate)
        ↓
LLM (explicador)  →  Resposta em português + query + tabela
```

## Base de dados

**Amazon Reviews 2023** — McAuley Lab / UCSD ([site](https://amazon-reviews-2023.github.io/) · [paper](https://arxiv.org/abs/2403.03952))

Recorte usado: categoria **Gift_Cards**.

| Coleção    | Documentos | Origem                     |
| ---------- | ---------- | -------------------------- |
| `reviews`  | 152.410    | `Gift_Cards.jsonl.gz`      |
| `products` | 1.137      | `meta_Gift_Cards.jsonl.gz` |

Junção por `parent_asin`.

## Estrutura do repositório

```
datachat-nosql/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── app/
│   └── main.py              # interface Streamlit
│
├── core/
│   ├── orquestrador.py      # coordena o fluxo, com retry de autocorreção
│   ├── esquema.py           # contexto de esquema (campos, tipos, % preenchido)
│   ├── tradutor.py          # Gemini: pergunta → pipeline MongoDB
│   ├── validador.py         # bloqueia operações destrutivas (RF07)
│   ├── executor.py          # PyMongo
│   └── explicador.py        # Gemini: resultados → texto em português
│
├── scripts/
│   ├── importar_mongo.py     # ETL do .jsonl.gz para o MongoDB
│   ├── consultas.py          # as 8 consultas da Semana 1
│   ├── comparar_llms.py      # Gemini vs Llama local — evidência da escolha de LLM
│   └── exportar_slides_pdf.py  # gera docs/slides_semana2.pdf a partir do HTML
│
├── docs/
│   ├── RELATORIO_SEMANA1.md
│   ├── RELATORIO_SEMANA2.md
│   ├── slides_semana2.html          # slides da apresentação (abrir no navegador)
│   ├── slides_semana2.pdf           # export estático dos slides, um por página
│   ├── ROTEIRO_APRESENTACAO_SEMANA2.md  # fala mapeada aos slides, dividida por integrante
│   ├── ROTEIRO_DEMO_SEMANA2.md          # roteiro da demo ao vivo, com comandos
│   ├── comparacao_llms.txt          # log completo do comparativo Gemini vs Llama
│   └── arquitetura.mermaid
│
├── tests/
│   └── test_validador.py    # 17 casos, incluindo adversariais (RF07)
│
└── data/                    # (no .gitignore — não versionar)
```

## Instalação

```bash
git clone https://github.com/<org>/datachat-nosql.git
cd datachat-nosql

python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env   # preencha GOOGLE_API_KEY (gratuito em aistudio.google.com/apikey)
```

### MongoDB via Docker

```bash
docker run -d --name mongo-datachat -p 27017:27017 mongo:7
```

### Carregar os dados

Os arquivos ficam na página inicial do dataset, tabela **"Grouped by Category"**,
colunas `review` e `meta`. São **JSON Lines comprimidos** (`.jsonl.gz`) — um
documento por linha, sem array externo.

```bash
mkdir -p data
wget https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/review_categories/Gift_Cards.jsonl.gz -P data/
wget https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/meta_categories/meta_Gift_Cards.jsonl.gz -P data/

python scripts/importar_mongo.py --arquivo data/Gift_Cards.jsonl.gz --colecao reviews
python scripts/importar_mongo.py --arquivo data/meta_Gift_Cards.jsonl.gz --colecao products
```

Para um teste rápido, use `--limite 10000`.

### Rodar

```bash
python scripts/consultas.py             # valida a carga e roda as 8 consultas
pytest tests/                           # 17 testes do validador (RF07)
streamlit run app/main.py               # interface completa, com LLM real
```

## Stack

| Componente | Tecnologia                         | Por quê                                                            |
| ---------- | ----------------------------------- | ------------------------------------------------------------------- |
| Banco      | MongoDB 7                           | O dado já é JSON; `details` tem esquema aberto                      |
| Driver     | PyMongo                             | Driver oficial                                                      |
| Interface  | Streamlit                           | Protótipo em horas                                                  |
| LLM        | Gemini (`gemini-flash-lite-latest`) | Gratuito, saída JSON estruturada confiável — ver `docs/comparacao_llms.txt` |
| Config     | python-dotenv                       | Chave de API fora do Git                                            |

**Por que Gemini e não Llama local:** testamos os dois nas mesmas 7 perguntas
(`scripts/comparar_llms.py`). Gemini acertou 7/7 (JSON válido + pipeline
executou sem erro); Llama 3.2 3B local, rodando via Ollama no mesmo notebook
usado no projeto (MacBook Air M1, 8GB), acertou 1/7 — errou principalmente em
pipelines com `$lookup`/`$objectToArray`, e ainda assim foi ~2x mais lento. O
log completo (input e output brutos de cada modelo) está em
`docs/comparacao_llms.txt`.

Deliberadamente **sem LangChain**: para NL→Query são duas chamadas HTTP e um
`aggregate()`. A abstração custa depuração opaca e esconde exatamente o que o
projeto precisa demonstrar. A justificativa completa está na Seção 5.5 do relatório.

## Equipe

- Gabriel Azevedo Lira de Farias
- João Pedro de Queiroz Dantas
- Vitor Jesus Mamede Soares
- Vítor Raimundo Fernandes Gabínio
