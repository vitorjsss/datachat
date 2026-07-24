# DataChat NoSQL — Relatório da Semana 1

**Equipe:** Gabriel Azevedo Lira de Farias, João Pedro de Queiroz Dantas, Vitor Jesus Mamede Soares, Vítor Raimundo Fernandes Gabínio
**Disciplina:** _(preencher)_
**Data:** _(preencher)_
**Repositório:** _(link do GitHub)_

> Todos os números deste relatório foram medidos na base carregada, não estimados.
> A saída bruta do perfilamento está em `docs/perfil_base.txt`.

---

## 1. Estudo da Base de Dados

### 1.1 Base escolhida

**Amazon Reviews 2023** — McAuley Lab, University of California San Diego (UCSD).

- Site oficial: https://amazon-reviews-2023.github.io/
- Artigo: *Bridging Language and Items for Retrieval and Recommendation* (Hou et al., arXiv:2403.03952, 2024)
- Espelho no Hugging Face: https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023

Recorte utilizado: categoria **Gift_Cards**.

### 1.2 Objetivo da base

A base foi construída para pesquisa em **sistemas de recomendação**, **mineração de opinião** e, mais recentemente, para servir de insumo a **modelos de linguagem** aplicados a e-commerce. Reúne o comportamento real de compra e avaliação de consumidores da Amazon ao longo de 27 anos.

Os próprios autores destacam a contagem de tokens das avaliações e dos metadados como estatística central "na era dos LLMs" — o que alinha a base diretamente com o objetivo do nosso projeto.

### 1.3 Origem dos dados

Coleta (crawling) do site da Amazon realizada em 2023 pelo McAuley Lab. É a quarta geração de um dataset histórico:

| Versão | #Reviews | #Usuários | #Itens | Período |
|---|---|---|---|---|
| 2013 | 34,69 M | 6,64 M | 2,44 M | jun/96 – mar/13 |
| 2014 | 82,83 M | 21,13 M | 9,86 M | mai/96 – jul/14 |
| 2018 | 233,10 M | 43,53 M | 15,17 M | mai/96 – out/18 |
| **2023** | **571,54 M** | **54,51 M** | **48,19 M** | **mai/96 – set/23** |

A versão 2023 é 245,2% maior que a anterior, cobre 33 domínios e traz *timestamp* em nível de segundo ou mais fino.

### 1.4 Número de documentos — medido

A base completa tem 571,54 milhões de avaliações, inviável para o escopo da disciplina. Trabalhamos com a categoria **Gift_Cards**:

| Métrica | Estimativa do site | **Medido na carga** |
|---|---|---|
| Avaliações (`reviews`) | 152,4 K | **152.410** |
| Produtos (`products`) | 1,1 K | **1.137** |
| Usuários distintos | 132,7 K | **132.732** |
| Produtos com ao menos 1 avaliação | — | **1.137 (100%)** |
| Tokens de review | 3,6 M | — |
| Tokens de metadados | 630 K | — |
| Faixa temporal | — | **06/08/2008 a 06/09/2023** |
| Média de avaliações por produto | — | **134,0** |

**Justificativa do recorte:** volume suficiente para exigir índices e agregações reais, mas que carrega em segundos e ocupa ~52 MB — cabe folgadamente no *free tier* do Atlas (10% da cota de 512 MB). A arquitetura é agnóstica à categoria: trocar de recorte exige apenas mudar o arquivo de entrada.

Um detalhe favorável do recorte: **100% dos produtos têm avaliação**, então a junção `reviews × products` não perde nenhum registro.

### 1.5 Principais atributos do documento JSON

A coluna *preenchimento* foi medida em `scripts/perfilar.py` e é decisiva: campos pouco preenchidos não sustentam consulta apresentável.

#### Coleção `reviews` — 152.410 documentos

| Campo | Tipo | Preenchimento | Descrição |
|---|---|---|---|
| `rating` | float | 100,0% | Nota do produto, de 1.0 a 5.0 |
| `title` | string | 100,0% | Título da avaliação |
| `text` | string | 100,0% | Corpo da avaliação (6 documentos vazios) |
| `asin` | string | 100,0% | ID do produto |
| `parent_asin` | string | 100,0% | ID pai — **chave de junção com os metadados** |
| `user_id` | string | 100,0% | ID do avaliador |
| `timestamp` | int | 100,0% | Data em Unix time (ms) |
| `review_date` | date | 100,0% | **Campo derivado no ETL** a partir de `timestamp` |
| `verified_purchase` | bool | 100,0% | Compra verificada |
| `helpful_vote` | int | 100,0% | Votos de "útil" |
| `images` | array | **0,9%** | Fotos postadas pelo usuário — praticamente ausente |

#### Coleção `products` — 1.137 documentos

| Campo | Tipo | Preenchimento | Descrição |
|---|---|---|---|
| `parent_asin` | string | 100,0% | ID pai do produto |
| `title` | string | 100,0% | Nome do produto |
| `average_rating` | float | 100,0% | Nota exibida na página |
| `rating_number` | int | 100,0% | Quantidade de avaliações |
| `images` | array | 99,9% | Imagens (`thumb`, `large`, `hi_res`, `variant`) |
| `store` | string | 98,5% | Nome da loja/vendedor |
| `categories` | array | 97,9% | Categorias hierárquicas |
| `details` | object | 97,1% | Detalhes de **esquema aberto** |
| `features` | array | 90,8% | Características em bullet points |
| `main_category` | string | 85,0% | Categoria principal |
| `description` | array | **77,0%** | Descrição — parcial |
| `price` | float | **33,4%** | Preço em USD — **ausente em 2 de cada 3 produtos** |
| `videos` | array | **12,0%** | Vídeos — inutilizável |
| `bought_together` | array | **0,0%** | **Ausente na íntegra (0 de 1.137)** |

**Consequência prática documentada:** o campo `price` existe no esquema oficial da base, mas está preenchido em apenas 380 dos 1.137 produtos. Isso foi descoberto no perfilamento **antes** de escrever as consultas, e levou a Consulta 4 a usar `$ifNull` em vez de filtrar por preço — filtrar descartaria dois terços do catálogo. O campo `bought_together` está documentado no site mas não existe neste recorte.

### 1.6 Principais tipos de dados

- **Escalares:** `string` (textos, IDs), `double` (`rating`, `price`), `int`/`long` (`timestamp`, `helpful_vote`, `rating_number`), `bool` (`verified_purchase`)
- **Data:** `review_date` — BSON `Date`, derivado no ETL
- **Arrays de escalares:** `features`, `description`, `categories`
- **Arrays de subdocumentos:** `images`, `videos` — hierarquia de 2 níveis
- **Documento aninhado de esquema aberto:** `details` — **20 chaves distintas** encontradas, com frequências muito díspares (ver 1.9). É o caso que justifica NoSQL sobre relacional
- **Nulos:** `price` ausente em 66,6% dos produtos

### 1.7 Possíveis aplicações da base

1. **Detecção de fraude e problemas de entrega** — vale-presente digital tem um modo de falha próprio: o código não chega ou já foi resgatado. As 12.326 avaliações de 1 estrela concentram esse relato
2. **Análise de sentimento** — texto livre com a nota como rótulo supervisionado
3. **Estudo de sazonalidade** — vale-presente tem pico previsível em datas comemorativas; `review_date` permite medir
4. **Business intelligence de e-commerce** — desempenho por loja e por emissor do vale
5. **Busca semântica e RAG** — os textos alimentam embeddings para recuperação por significado
6. **Nosso caso: consulta em linguagem natural** — traduzir perguntas de negócio em consultas MongoDB

### 1.8 Esquema simplificado da coleção

```
datachat (database) — 51,6 MB
│
├── reviews (152.410 documentos)
│   ├── _id              : ObjectId
│   ├── rating           : double        ← 1.0 a 5.0
│   ├── title            : string
│   ├── text             : string
│   ├── asin             : string
│   ├── parent_asin      : string  ──────┐  (chave de junção)
│   ├── user_id          : string        │
│   ├── timestamp        : long          │
│   ├── review_date      : date    ← derivado no ETL
│   ├── verified_purchase: bool          │
│   ├── helpful_vote     : int           │
│   └── images           : array   (0,9% — quase sempre ausente)
│       └── [0] { small_image_url, medium_image_url,
│                 large_image_url, attachment_type }
│                                        │
└── products (1.137 documentos)          │
    ├── _id             : ObjectId       │
    ├── parent_asin     : string  ───────┘  (100% de correspondência)
    ├── title           : string
    ├── main_category   : string   (85,0%)
    ├── average_rating  : double
    ├── rating_number   : int
    ├── price           : double | null  (33,4% — ver 1.5)
    ├── store           : string   (98,5%)
    ├── features        : array<string>  (90,8%)
    ├── description     : array<string>  (77,0%)
    ├── categories      : array<string>  (97,9%)
    ├── bought_together : ausente neste recorte
    ├── details         : object   (97,1%) ← esquema aberto, 20 chaves
    │   ├── Date First Available : string   (1.093 produtos)
    │   ├── Package Dimensions   : string   (825)
    │   ├── Manufacturer         : string   (497)
    │   ├── Brand                : string   (30)
    │   └── ...                  : chaves variáveis por produto
    ├── images          : array<object>  (99,9%)
    │   └── [0] { thumb, large, hi_res, variant }
    └── videos          : array<object>  (12,0%)
```

**Decisão de modelagem:** mantivemos **duas coleções referenciadas** por `parent_asin` em vez de embutir os metadados em cada review. Embutir replicaria o documento de produto em cada uma das 152.410 avaliações — e, dada a concentração descrita em 1.9, um único produto teria seus metadados duplicados 36.863 vezes. A junção é feita sob demanda com `$lookup`. É a escolha alinhada ao padrão *reference* do MongoDB para relações 1:N com N alto.

### 1.9 Achados do perfilamento

Três características desta base afetam diretamente o projeto e foram descobertas antes de escrever qualquer consulta.

**(a) Distribuição de notas extremamente assimétrica**

| Nota | Avaliações | % |
|---|---|---|
| 1★ | 12.326 | 8,1% |
| 2★ | 1.873 | 1,2% |
| 3★ | 3.271 | 2,1% |
| 4★ | 6.692 | 4,4% |
| **5★** | **128.248** | **84,1%** |

É a distribuição em J, típica de e-commerce, mas aqui em versão extrema: **84,1% de 5 estrelas** contra ~61% do e-commerce em geral. Faz sentido para o produto — vale-presente ou funciona como esperado ou não chega. Não há meio-termo de "qualidade razoável" a avaliar.

**Implicação para o projeto:** uma nota média de 4,6 nesta base não significa "produto bom"; significa "quase tudo é 5, com uma minoria de 1". O LLM explicador precisa saber disso, ou vai produzir interpretações ingênuas de média.

**(b) Concentração extrema em um único produto**

O produto mais avaliado tem **36.863 avaliações — 24,2% de toda a base**. O mínimo é 1. A média de 134 avaliações por produto é, portanto, enganosa.

**Implicação:** qualquer ranking por volume é dominado por esse item. As Consultas 3 e 4 usam corte por volume mínimo (`$gte`) justamente para produzir resultado informativo apesar da cauda longa.

**(c) Índices maiores que os dados**

| | Tamanho |
|---|---|
| Dados | 23,0 MB |
| Índices | **28,5 MB** |
| **Total** | **51,6 MB** |

Os índices ocupam 124% do tamanho dos dados. O responsável é o índice de texto sobre `title` + `text`, que indexa cada termo de 152 mil avaliações. É o preço da Consulta 6 — e um bom lembrete de que índice não é grátis.

---

## 2. Importação do Arquivo JSON

### 2.1 Onde estão os arquivos no site

Na página inicial de https://amazon-reviews-2023.github.io/, seção **Basic Statistics → Grouped by Category**. A tabela lista as 33 categorias, e cada linha tem dois links: **`review`** e **`meta`**.

| Arquivo | URL |
|---|---|
| `Gift_Cards.jsonl.gz` | https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/review_categories/Gift_Cards.jsonl.gz |
| `meta_Gift_Cards.jsonl.gz` | https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/meta_categories/meta_Gift_Cards.jsonl.gz |

### 2.2 Formato: JSONL, não JSON

Ponto crítico: o arquivo é **JSON Lines** (`.jsonl`), comprimido em gzip. Cada linha é um documento JSON independente, **sem vírgulas entre eles e sem colchetes de array**:

```
{"rating": 5.0, "title": "Great gift", "asin": "B004LLIL5A", ...}
{"rating": 1.0, "title": "Never arrived", "asin": "B004LLIKVU", ...}
```

Duas consequências práticas:

1. `json.load(arquivo)` **falha** — é preciso iterar linha a linha com `json.loads(linha)`
2. No `mongoimport` é obrigatório `--type json` **sem** `--jsonArray`

### 2.3 Método de importação escolhido: PyMongo

Avaliamos três caminhos:

| Método | Vantagem | Decisão |
|---|---|---|
| MongoDB Compass | Interface gráfica | Não lê `.gz`. **Descartado** |
| `mongoimport` | Rápido, nativo | Não permite transformação durante a carga. **Plano B** |
| **PyMongo** | Streaming do `.gz`, transformação no meio do caminho, `insert_many` em lotes | **Escolhido** |

O fator decisivo foi a **transformação durante a carga**: `timestamp` vem como inteiro Unix em milissegundos, o que impede o uso dos operadores de data do MongoDB (`$year`, `$month`, `$dateTrunc`). Nosso script converte para `BSON Date` no campo `review_date` durante a ingestão — preenchido em 100% dos documentos, conforme verificado.

Sem isso, toda pergunta do tipo *"quantas avaliações por mês em 2022?"* exigiria aritmética manual no *pipeline*, e o LLM teria muito mais chance de errar.

O script também descomprime em *streaming* (`gzip.open`), sem materializar o arquivo descompactado em disco.

### 2.4 Comandos executados

```bash
# 1. Download
mkdir -p data
curl -L -o data/Gift_Cards.jsonl.gz \
  https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/review_categories/Gift_Cards.jsonl.gz
curl -L -o data/meta_Gift_Cards.jsonl.gz \
  https://mcauleylab.ucsd.edu/public_datasets/data/amazon_2023/raw/meta_categories/meta_Gift_Cards.jsonl.gz

# 2. Importação
python scripts/importar_mongo.py --arquivo data/Gift_Cards.jsonl.gz --colecao reviews --recriar
python scripts/importar_mongo.py --arquivo data/meta_Gift_Cards.jsonl.gz --colecao products --recriar

# 3. Perfilamento — extrai os números deste relatório
python scripts/perfilar.py > docs/perfil_base.txt
```

### 2.5 Plano B com mongoimport

```bash
gunzip -c data/Gift_Cards.jsonl.gz | \
  mongoimport --db datachat --collection reviews --type json --numInsertionWorkers 4
```
_(sem `--jsonArray`; não gera o campo `review_date`)_

### 2.6 Resumo da importação

| Item | Valor |
|---|---|
| Banco de dados | `datachat` |
| Coleção 1 | `reviews` — **152.410** documentos |
| Coleção 2 | `products` — **1.137** documentos |
| Arquivos de origem | `Gift_Cards.jsonl.gz`, `meta_Gift_Cards.jsonl.gz` |
| Método | PyMongo, `insert_many` em lotes de 5.000, `ordered=False` |
| Transformação | `timestamp` (int ms) → `review_date` (BSON Date) — 100% preenchido |
| Tamanho final | 23,0 MB de dados + 28,5 MB de índices = **51,6 MB** |
| Índices criados | 6 em `reviews`, 4 em `products` |

### 2.7 Comprovação de carga correta

```javascript
use datachat

db.reviews.countDocuments()     // → 152410
db.products.countDocuments()    // → 1137
db.reviews.findOne()            // → review_date presente como Date
db.reviews.getIndexes()         // → 6 índices
db.stats()                      // → 51,6 MB
```

**Evidências:**
1. Log do script de importação — _(colar print)_
2. Compass mostrando as duas coleções com as contagens — _(colar print)_
3. `findOne()` com `review_date` como `Date` — prova da transformação — _(colar print)_
4. Saída completa de `scripts/perfilar.py` — `docs/perfil_base.txt`

---

## 3. Criação da Base MongoDB + Testes das Consultas

Banco `datachat`, coleções `reviews` e `products`. As oito consultas abaixo estão implementadas e testadas em `scripts/consultas.py`. Cada uma exercita um recurso diferente do MongoDB e serve de **exemplo few-shot no prompt do LLM** na Semana 2.

### Consulta 1 — Filtro simples com projeção e ordenação
> *"Quais as avaliações 5 estrelas mais úteis de compras verificadas?"*

```javascript
db.reviews.find(
  { rating: 5.0, verified_purchase: true },
  { title: 1, helpful_vote: 1, parent_asin: 1, _id: 0 }
).sort({ helpful_vote: -1 }).limit(10)
```
**Exercita:** `find`, filtro composto, projeção, `sort`, `limit`.

### Consulta 2 — Agregação com agrupamento
> *"Qual a distribuição das notas na base?"*

```javascript
db.reviews.aggregate([
  { $group: { _id: "$rating", total: { $sum: 1 } } },
  { $sort: { _id: 1 } }
])
```
**Exercita:** `$group`, `$sum`. **Resultado medido:** 84,1% em 5 estrelas (ver 1.9a).

### Consulta 3 — Ranking com múltiplos acumuladores e `$match` pós-agrupamento
> *"Quais os 10 produtos com melhor nota média, entre os que têm pelo menos 50 avaliações?"*

```javascript
db.reviews.aggregate([
  { $group: {
      _id: "$parent_asin",
      nota_media: { $avg: "$rating" },
      total_avaliacoes: { $sum: 1 }
  }},
  { $match: { total_avaliacoes: { $gte: 50 } } },
  { $sort: { nota_media: -1 } },
  { $limit: 10 }
])
```
**Exercita:** `$avg`, `$match` depois de `$group` (equivalente ao `HAVING` do SQL).
**Calibração:** o corte de 50 foi escolhido a partir da média medida de 134 avaliações por produto. Sem o corte, produtos com 1 avaliação de 5 estrelas empatariam no topo com média 5,0.

### Consulta 4 — Junção entre coleções com `$lookup`
> *"Quais os produtos mais mal avaliados, com nome, loja e preço?"*

```javascript
db.reviews.aggregate([
  { $group: {
      _id: "$parent_asin",
      nota_media: { $avg: "$rating" },
      total: { $sum: 1 }
  }},
  { $match: { total: { $gte: 20 } } },
  { $sort: { nota_media: 1 } },
  { $limit: 10 },
  { $lookup: {
      from: "products",
      localField: "_id",
      foreignField: "parent_asin",
      as: "produto"
  }},
  { $unwind: "$produto" },
  { $project: {
      _id: 0,
      parent_asin: "$_id",
      nome: "$produto.title",
      loja: "$produto.store",
      preco: { $ifNull: ["$produto.price", "não informado"] },
      nota_media: { $round: ["$nota_media", 2] },
      total: 1
  }}
])
```
**Exercita:** `$lookup`, `$unwind`, `$ifNull`, `$project`. **É a consulta-chave do projeto:** demonstra que o modelo referenciado funciona e é o padrão mais difícil para o LLM gerar — por isso vai no prompt como exemplo.

**Decisão informada pelo perfilamento:** `price` existe em só 33,4% dos produtos. Filtrar por `price: { $ne: null }` descartaria dois terços do catálogo, então usamos `$ifNull` e exibimos "não informado". `store` (98,5%) entrou como atributo principal no lugar.

### Consulta 5 — Série temporal com operadores de data
> *"Como evoluiu o volume de avaliações e a nota média por ano, de 2018 em diante?"*

```javascript
db.reviews.aggregate([
  { $match: { review_date: { $gte: ISODate("2018-01-01") } } },
  { $group: {
      _id: { ano: { $year: "$review_date" } },
      total: { $sum: 1 },
      nota_media: { $avg: "$rating" }
  }},
  { $sort: { "_id.ano": 1 } }
])
```
**Exercita:** `$year` sobre o campo derivado no ETL, `$match` antes do `$group` (usa índice).
**Cobertura:** a base vai de 06/08/2008 a 06/09/2023 — o corte em 2018 pega os 6 anos finais. Note que 2023 está incompleto (a coleta parou em setembro).

### Consulta 6 — Busca textual
> *"O que reclamam os clientes que não receberam o vale-presente?"*

```javascript
db.reviews.find(
  { $text: { $search: "never received scam refund" }, rating: { $lte: 2.0 } },
  { score: { $meta: "textScore" }, title: 1, text: 1, rating: 1, _id: 0 }
).sort({ score: { $meta: "textScore" } }).limit(10)
```
**Exercita:** índice de texto, `$text`, `$meta: "textScore"`. Mostra que a base responde a perguntas qualitativas, não só numéricas. Os termos foram escolhidos a partir do modo de falha específico do produto: vale-presente digital falha por não-entrega ou código já resgatado, não por defeito físico.

### Consulta 7 — Descoberta dinâmica de esquema
> *"Quais atributos existem em `details` e com que frequência aparecem?"*

```javascript
db.products.aggregate([
  { $match: { details: { $exists: true, $ne: {} } } },
  { $project: { kv: { $objectToArray: "$details" } } },
  { $unwind: "$kv" },
  { $group: {
      _id: "$kv.k",
      produtos: { $sum: 1 },
      exemplo: { $first: "$kv.v" }
  }},
  { $sort: { produtos: -1 } },
  { $limit: 15 }
])
```
**Exercita:** `$objectToArray`, `$unwind`, `$group`.

**É a consulta que justifica a escolha por NoSQL.** Ela não assume nenhum campo: **descobre** quais atributos existem. Em SQL isso é impossível sem conhecer as colunas de antemão — aqui, o esquema é descoberto em tempo de consulta.

**Resultado medido:** 20 chaves distintas em 1.104 produtos, com frequências de 1.093 (`Date First Available`) a 5 (`Batteries required`). `Brand` aparece em apenas 30. Uma tabela relacional com essas 20 colunas seria 97% nula.

### Consulta 8 — Concentração da base
> *"Quais produtos concentram mais avaliações, e que fatia da base representam?"*

```javascript
db.reviews.aggregate([
  { $group: {
      _id: "$parent_asin",
      avaliacoes: { $sum: 1 },
      nota_media: { $avg: "$rating" }
  }},
  { $sort: { avaliacoes: -1 } },
  { $limit: 5 },
  { $lookup: { from: "products", localField: "_id",
               foreignField: "parent_asin", as: "p" } },
  { $unwind: "$p" },
  { $project: {
      _id: 0,
      nome: "$p.title",
      avaliacoes: 1,
      nota_media: { $round: ["$nota_media", 2] },
      pct_da_base: { $round: [
        { $multiply: [ { $divide: ["$avaliacoes", 152410] }, 100 ] }, 1] }
  }}
])
```
**Exercita:** `$divide`, `$multiply`, `$round`, `$lookup`. Quantifica o achado 1.9b: o produto mais avaliado detém **24,2%** de toda a base.

### 3.1 Índices criados e justificativa

```javascript
db.reviews.createIndex({ parent_asin: 1 })                       // $lookup e agrupamento (C3, C4, C8)
db.reviews.createIndex({ user_id: 1 })                           // consultas por usuário
db.reviews.createIndex({ rating: 1 })                            // filtros por nota (C6)
db.reviews.createIndex({ review_date: -1 })                      // série temporal (C5)
db.reviews.createIndex({ verified_purchase: 1, rating: -1 })     // índice composto (C1)
db.reviews.createIndex({ title: "text", text: "text" })          // busca textual (C6)
db.products.createIndex({ parent_asin: 1 }, { unique: true })    // lado "1" do $lookup
db.products.createIndex({ store: 1 })
db.products.createIndex({ price: 1 })
db.products.createIndex({ main_category: 1 })
```

**Custo medido:** 28,5 MB de índices contra 23,0 MB de dados (124%). O índice de texto responde pela maior parte. É uma troca consciente: sem ele, a Consulta 6 varreria 152 mil documentos.

**Validação:** `scripts/consultas.py` roda `.explain("executionStats")` na Consulta 1 e reporta o estágio. Deve mostrar `IXSCAN`, não `COLLSCAN`.

---

## 4. Definição da Arquitetura da Solução

### 4.1 Visão em camadas

```
┌───────────────────────────────────────────────────────────────────┐
│  CAMADA DE APRESENTAÇÃO                                           │
│  Streamlit — app/main.py                                          │
│  · campo de pergunta · botão Consultar · abas de resultado        │
│  · histórico em st.session_state                                  │
└──────────────────────────┬────────────────────────────────────────┘
                           │ chamada de função Python (mono-processo)
                           │ evolução: HTTP/JSON → FastAPI
┌──────────────────────────▼────────────────────────────────────────┐
│  CAMADA DE ORQUESTRAÇÃO — core/orquestrador.py                    │
│  Coordena o fluxo e trata falhas de cada etapa                    │
└─┬────────────┬────────────┬────────────┬─────────────┬────────────┘
  │            │            │            │             │
  ▼            ▼            ▼            ▼             ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Contexto │ │ Tradutor │ │ Validador│ │ Executor │ │Explicador│
│ de       │ │ NL→Query │ │ de       │ │ MongoDB  │ │ de       │
│ Esquema  │ │          │ │ Segurança│ │          │ │Resultados│
│          │ │ (LLM #1) │ │          │ │          │ │ (LLM #2) │
└──────────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘
                  │            │            │            │
                  └────────────┴──────┬─────┴────────────┘
                                      │
              ┌───────────────────────┴──────────────────┐
              ▼                                          ▼
      ┌───────────────┐                          ┌───────────────┐
      │  LLM Provider │                          │   MongoDB     │
      │  (API externa)│                          │   datachat    │
      └───────────────┘                          │ · reviews     │
                                                 │ · products    │
                                                 └───────────────┘
```

Diagrama detalhado em `docs/arquitetura.mermaid`.

### 4.2 Componentes e responsabilidades

| # | Componente | Responsabilidade | Entrada → Saída |
|---|---|---|---|
| 1 | **Interface (Streamlit)** | Capturar a pergunta, exibir query, resultados, explicação e histórico | texto → render |
| 2 | **Orquestrador** | Sequenciar etapas, capturar erros, medir tempo | pergunta → objeto de resposta |
| 3 | **Contexto de Esquema** | Descrição das coleções, campos, tipos, **preenchimento real** e exemplos few-shot | — → string de contexto |
| 4 | **Tradutor NL→Query (LLM #1)** | Gerar o *pipeline* ou filtro `find` em JSON | pergunta + esquema → JSON |
| 5 | **Validador de Segurança** | Rejeitar operações destrutivas, forçar `$limit`, checar coleções/campos | JSON → JSON validado ou erro |
| 6 | **Executor MongoDB** | Executar via PyMongo com timeout, serializar `ObjectId`/`Date` | JSON → lista de documentos |
| 7 | **Explicador (LLM #2)** | Redigir resposta em linguagem natural | pergunta + resultados → texto |
| 8 | **Cache** | Evitar chamada ao LLM para perguntas repetidas | hash(pergunta) → query |

### 4.3 Fluxo detalhado de uma requisição

1. Usuário digita: *"Quais os 5 produtos com pior avaliação média?"* e clica em **Consultar**
2. Orquestrador monta o prompt: **esquema + estatísticas reais + 3 exemplos few-shot + pergunta**
3. LLM #1 devolve o *pipeline* em JSON
4. **Validador** verifica: sem `$out`/`$merge`/`update`/`drop`; coleção permitida; `$limit ≤ 100` (injeta se ausente); campos existem no esquema
5. Se inválido → **retry único** com o erro devolvido ao LLM (autocorreção). Falhando de novo → erro amigável
6. **Executor** roda com `maxTimeMS = 15000`
7. Resultados vão para o LLM #2, que redige a explicação
8. Interface exibe as três áreas + grava no histórico

### 4.4 Decisões de arquitetura

**(a) O Validador é um componente separado, não um trecho dentro do executor.**
Isolar a segurança em um módulo com testes próprios é o que impede que *"apague todas as avaliações"* vire um `deleteMany`. Um LLM **vai** gerar isso um dia — o projeto não pode depender do LLM se comportar bem.

**(b) Dois LLMs (ou duas chamadas) em vez de um.**
Gerar a query e explicar o resultado têm prompts, temperaturas e até modelos diferentes. Tradução exige temperatura ~0 e saída estruturada; explicação se beneficia de temperatura mais alta. Separar também permite usar um modelo mais barato na explicação.

**(c) O Contexto de Esquema inclui estatísticas, não só nomes de campos.**
Esta decisão veio direto do perfilamento. Se o prompt disser apenas que `price` existe, o LLM vai gerar consultas que filtram por preço e devolvem dois terços a menos de resultado, sem avisar ninguém. O contexto precisa informar que `price` está em 33,4% e que `bought_together` não existe. **O perfilamento não foi só para o relatório — ele alimenta o prompt.**

**(d) Retry com autocorreção.**
Muita acurácia por pouquíssimo código: devolver o erro do MongoDB ao LLM e pedir correção resolve boa parte das falhas de sintaxe.

**(e) Conexão MongoDB via `@st.cache_resource`.**
Sem isso o Streamlit abre uma conexão nova a cada rerun e estoura o pool — erro clássico que derruba a demo.

**(f) A interface fala com o orquestrador por chamada de função, não HTTP.**
Para a Semana 1 um monólito é mais simples e rápido. A fronteira entre `app/` e `core/` fica desenhada, de modo que trocar para FastAPI depois seja mudar a camada de chamada, sem reescrever a lógica.

---

## 5. Análise das Tecnologias

### 5.1 Quadro-resumo

| Camada | Sugerida no projeto | Decisão | Justificativa |
|---|---|---|---|
| Banco | MongoDB | ✅ Manter | Requisito e adequado ao dado |
| Interface | Streamlit | ✅ Manter | Protótipo em horas |
| Driver | PyMongo | ✅ Manter | Driver oficial |
| LLM | (a definir) | ⚠️ Definir com fallback | Ver 5.4 |
| Orquestração LLM | LangChain | ❌ **Não usar** | Ver 5.5 |
| Validação | — | ➕ **Adicionar** | Lacuna crítica do desenho original |
| Config | — | ➕ python-dotenv | Chave de API fora do repositório |

### 5.2 MongoDB — vai dar certo

Sim, e é a escolha certa por três motivos concretos:

1. O dado **já é JSON** — não há impedância objeto-relacional a resolver
2. `details` tem **esquema aberto** — medimos 20 chaves distintas com frequência de 1.093 a 5 produtos. Uma tabela relacional com essas colunas seria ~97% nula; em SQL viraria EAV ou coluna JSON, ambos piores. **A Consulta 7 é a prova executável disso**
3. O *Aggregation Framework* é composicional: um *pipeline* é uma **lista de estágios JSON**, estrutura que um LLM gera com muito mais confiabilidade do que uma string SQL. **É uma vantagem real do MongoDB para este projeto** e merece ser dita na apresentação

**Sobre capacidade:** o banco ocupa 51,6 MB, o que representa 10% da cota de 512 MB do *free tier* do Atlas. Não há restrição de espaço neste recorte. _(Nota: com categorias maiores como `Electronics`, 43,9 M de reviews, a cota estouraria e seria necessário MongoDB local ou o script em modo `--enxuto`.)_

### 5.3 Streamlit — vai dar certo, com ressalvas

**A favor:** protótipo funcional em poucas horas, sem HTML/CSS/JS; `st.dataframe`, `st.json` e `st.chat_message` resolvem quase tudo; deploy gratuito no Streamlit Community Cloud.

**Contra (e como mitigamos):**
- **Rerun total do script a cada interação.** Sem `@st.cache_resource` na conexão e `st.session_state` no histórico, a aplicação reconecta e perde estado a cada clique. Já previsto no protótipo.
- **Single-threaded por sessão.** Irrelevante para uma demo acadêmica.

**Alternativa considerada:** Gradio. Mais simples, mas menos flexível para layout de múltiplas áreas. **Streamlit vence.**

### 5.4 LLM — a decisão mais importante

| Opção | Custo | Qualidade em NL→Query | Risco |
|---|---|---|---|
| API comercial (Claude / GPT / Gemini) | Baixo p/ demo | Alta | Depende de chave e internet |
| Gemini API (*free tier*) | Zero | Alta | Limite de requisições/min |
| Open-source local (Ollama + Llama 3 / Mistral) | Zero | Média-baixa em JSON estruturado | Precisa de GPU; erra sintaxe de `$lookup` |

**Nossa escolha: API comercial como principal + modo demo em cache como fallback.**

Justificativa: o núcleo do projeto é a **tradução para uma DSL estruturada com aninhamento** (`$lookup` + `$unwind` + `$project`, ou `$objectToArray` + `$unwind` + `$group`). Modelos pequenos rodando local erram esse tipo de saída com frequência alta, e o time gastaria a Semana 2 depurando o modelo em vez do sistema. Uma demo de 7 minutos com ~30 chamadas custa centavos.

**Mitigação de risco — a apresentação não pode depender de internet.** Manteremos um **modo demo com respostas em cache**: um dicionário `pergunta → query` gravado em disco para as perguntas da demonstração. Se a API cair na hora, a demo continua. Não é trapaça, é engenharia defensiva, e vale dizer isso em voz alta.

> A decisão final entre os candidatos acima — com comparação medida, não estimada — está em `docs/RELATORIO_SEMANA2.md`, Seção 2.

### 5.5 LangChain — recomendamos NÃO usar

Esta é a nossa crítica principal ao stack sugerido.

O LangChain adiciona uma camada de abstração pesada sobre o que, no fundo, são **duas chamadas HTTP e um `db.collection.aggregate()`**. Os custos:

- **Depuração opaca:** quando o prompt final não é o esperado, é preciso escavar a biblioteca para descobrir o que ela injetou
- **API instável:** *breaking changes* frequentes entre versões
- **Contradiz o objetivo pedagógico:** a disciplina quer que a equipe demonstre que **entende** o pipeline NL→Query. Esconder isso atrás de um agente pronto enfraquece a defesa do trabalho

**O que usamos no lugar:** o SDK oficial do provedor + `json.loads()` + PyMongo. São ~50 linhas que a equipe inteira entende e consegue defender na arguição.

**Ressalva justa:** se o projeto evoluir para RAG com busca vetorial sobre o texto das avaliações, uma biblioteca de orquestração passa a valer a pena. Para NL→Query, não vale.

### 5.6 Stack final

```
Python 3.11
├── pymongo          — driver oficial MongoDB
├── streamlit        — interface
├── anthropic/openai/google-genai  — SDK do LLM (um deles)
├── python-dotenv    — variáveis de ambiente
├── pandas           — exibição tabular
└── pytest           — testes do validador de segurança

MongoDB 7.x — local via Docker em dev; Atlas Free (M0) para a demo
```

Deliberadamente **fora do stack**: LangChain, LlamaIndex, FastAPI (por ora), Docker Compose (por ora). Cada dependência é um ponto de falha; a Semana 1 não precisa deles.

---

## Referências

- Hou, Y.; Li, J.; He, Z.; Yan, A.; Chen, X.; McAuley, J. **Bridging Language and Items for Retrieval and Recommendation**. arXiv:2403.03952, 2024.
- McAuley Lab. **Amazon Reviews 2023**. https://amazon-reviews-2023.github.io/
- MongoDB Inc. **Aggregation Pipeline Stages**. https://www.mongodb.com/docs/manual/reference/operator/aggregation-pipeline/
- MongoDB Inc. **Data Model Design — Embedded vs. References**. https://www.mongodb.com/docs/manual/core/data-model-design/
