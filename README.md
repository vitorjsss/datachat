# DataChat NoSQL

Interface de consulta em linguagem natural sobre o dataset **Amazon Reviews 2023**.
O usuário pergunta em português, um LLM traduz para uma consulta MongoDB, o sistema
executa e devolve a resposta explicada.

> Projeto acadêmico — _(disciplina, período)_

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

| Coleção | Documentos | Origem |
|---|---|---|
| `reviews` | 152.410 | `Gift_Cards.jsonl.gz` |
| `products` | 1.137 | `meta_Gift_Cards.jsonl.gz` |

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
├── core/                    # Semana 2
│   ├── orquestrador.py      # coordena o fluxo
│   ├── esquema.py           # contexto de esquema para o prompt
│   ├── tradutor.py          # LLM: pergunta → query
│   ├── validador.py         # bloqueia operações destrutivas
│   ├── executor.py          # PyMongo
│   └── explicador.py        # LLM: resultados → texto
│
├── scripts/
│   ├── importar_mongo.py    # ETL do .jsonl.gz para o MongoDB
│   └── consultas.py         # as 7 consultas da Semana 1
│
├── docs/
│   ├── RELATORIO_SEMANA1.md
│   └── arquitetura.mermaid
│
├── tests/                   # Semana 2
│   └── test_validador.py
│
└── data/                    # (no .gitignore — não versionar)
```

## Instalação

```bash
git clone https://github.com/<org>/datachat-nosql.git
cd datachat-nosql

python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env   # preencha MONGO_URI e a chave do LLM
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
python scripts/consultas.py     # valida a carga e roda as 7 consultas
streamlit run app/main.py       # interface
```

## Stack

| Componente | Tecnologia | Por quê |
|---|---|---|
| Banco | MongoDB 7 | O dado já é JSON; `details` tem esquema aberto |
| Driver | PyMongo | Driver oficial |
| Interface | Streamlit | Protótipo em horas |
| LLM | SDK oficial do provedor | Pipeline de agregação é lista de JSON — saída confiável |
| Config | python-dotenv | Chave de API fora do Git |

Deliberadamente **sem LangChain**: para NL→Query são duas chamadas HTTP e um
`aggregate()`. A abstração custa depuração opaca e esconde exatamente o que o
projeto precisa demonstrar. A justificativa completa está na Seção 5.5 do relatório.

## Status

| Entrega | Status |
|---|---|
| Estudo da base | ✅ |
| Importação para o MongoDB | ✅ |
| Base + 7 consultas testadas | ✅ |
| Arquitetura da solução | ✅ |
| Análise das tecnologias | ✅ |
| Repositório organizado | ✅ |
| Protótipo da interface (mock) | ✅ |
| Integração com LLM | ⬜ Semana 2 |
| Validador de segurança | ⬜ Semana 2 |

## Equipe

- Gabriel Azevedo Lira de Farias
- João Pedro de Queiroz Dantas
- Vitor Jesus Mamede Soares
- Vítor Raimundo Fernandes Gabínio

_(Responsabilidade de cada integrante nesta entrega a detalhar.)_

## Licença

Uso acadêmico. O dataset Amazon Reviews 2023 pertence ao McAuley Lab (UCSD) —
cite o artigo original em qualquer trabalho derivado.
