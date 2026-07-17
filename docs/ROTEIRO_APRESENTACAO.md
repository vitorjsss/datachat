# Roteiro de Apresentação — Semana 1 (7–10 min)

> Checklist de pré-voo e o que falar em cada um dos 7 itens exigidos.
> Todos os números abaixo foram validados rodando o projeto de ponta a ponta.

---

## Antes de começar (fazer 5 min antes da sala)

```bash
# 1. Confirmar que o MongoDB está de pé
docker ps                      # deve aparecer "mongo-datachat" em Up

# 2. Ativar o ambiente e confirmar a carga
cd datachat
source .venv/bin/activate
python scripts/consultas.py --numero 1     # se rodar sem erro, está tudo pronto

# 3. Deixar já aberto em abas do navegador:
#    - o repositório no GitHub
#    - docs/arquitetura.mermaid renderizado (cole em https://mermaid.live ou
#      use a extensão Mermaid do VS Code / preview do GitHub)

# 4. Deixar um terminal pronto para subir o Streamlit sob demanda
streamlit run app/main.py
```

Se o Docker não estiver rodando: `docker start mongo-datachat`.

---

## 1. Estudo da Base de Dados — ~1,5 min

**Falar:**
- Base: **Amazon Reviews 2023** (McAuley Lab / UCSD), recorte da categoria **Gift_Cards**.
- Objetivo original da base: sistemas de recomendação e mineração de opinião; hoje também alimenta LLMs — por isso serve bem ao projeto.
- Números medidos (não estimados — mostrar `docs/RELATORIO_SEMANA1.md` seção 1.4):
  - `reviews`: **152.410** documentos
  - `products`: **1.137** documentos
  - Faixa temporal: 06/08/2008 a 06/09/2023
  - Tamanho total: **51,6 MB** (23,0 MB dados + 28,5 MB índices)
- Achado forte para citar: distribuição de notas em **J extremo** — 84,1% são 5★, só 8,1% são 1★. Não existe "nota mediana" porque vale-presente ou funciona ou falha.
- Outro achado: um único produto (**Amazon Reload**) concentra **24,2%** de todas as avaliações — cauda longa extrema.

**Mostrar na tela:** seção 1 do `docs/RELATORIO_SEMANA1.md` (esquema simplificado, item 1.8).

---

## 2. Importação do Arquivo JSON — ~1 min

**Falar:**
- Arquivos `Gift_Cards.jsonl.gz` e `meta_Gift_Cards.jsonl.gz` — **JSON Lines comprimido**, um documento por linha (não é um array JSON).
- Método escolhido: **PyMongo**, não `mongoimport` nem Compass — porque precisávamos transformar o dado durante a carga (o `timestamp` vem como inteiro Unix em milissegundos; convertido para `BSON Date` no campo `review_date`, senão os operadores `$year`/`$month` não funcionam).
- `scripts/importar_mongo.py`: lê o `.gz` em streaming (sem descompactar em disco), insere em lotes de 5.000, cria os índices ao final.

**Mostrar na tela (comando ao vivo):**
```bash
mongosh datachat --eval "db.reviews.countDocuments()"   # → 152410
mongosh datachat --eval "db.products.countDocuments()"  # → 1137
mongosh datachat --eval "db.reviews.findOne()"           # mostra review_date como Date
```

---

## 3. Criação da Base MongoDB + Testes das Consultas — ~2,5 min

**Falar:** 8 consultas implementadas em `scripts/consultas.py`, cada uma exercitando um recurso diferente.

**Mostrar na tela (comando ao vivo — roda tudo em ~2s):**
```bash
python scripts/consultas.py
```

Destacar 3 delas ao vivo (não precisa ler as 8):

- **Consulta 4** (`$lookup`): junção `reviews × products` por `parent_asin` — prova que o modelo referenciado funciona, usa `$ifNull` porque `price` só existe em 33,4% dos produtos.
- **Consulta 6** (`$text`): busca textual por reclamações de vale-presente que não chegou.
- **Consulta 7** (`$objectToArray`): descoberta dinâmica de esquema dentro de `details` — **o argumento central a favor do NoSQL**: impossível de escrever em SQL sem conhecer as colunas de antemão.

Se sobrar tempo, mostrar o `EXPLAIN` no final da saída: o filtro usa o índice composto (**IXSCAN**, sem `COLLSCAN`), mas a ordenação por `helpful_vote` não está coberta pelo índice, então aparece um `SORT` em memória por cima. É um ponto técnico honesto — mostra que vocês entendem o plano de execução, não só que "tem índice".

---

## 4. Definição da Arquitetura da Solução — ~1 min

**Mostrar:** `docs/arquitetura.mermaid` renderizado.

**Falar o fluxo:**
```
Usuário → Streamlit → Orquestrador → Esquema + few-shot → LLM (tradutor)
   → Validador de segurança (bloqueia $out/$merge/drop/update, força $limit)
   → Executor PyMongo → MongoDB → LLM (explicador) → resposta em português
```
- Cache por hash da pergunta evita chamar o LLM duas vezes para a mesma pergunta.
- Validador tem *retry* único: se a query gerada for reprovada, o erro volta pro LLM antes de desistir.

---

## 5. Análise das Tecnologias — ~1 min

| Componente | Escolha | Por quê |
|---|---|---|
| Banco | MongoDB 7 | dado já é JSON; `details` tem esquema aberto (20 chaves variáveis) |
| Driver | PyMongo | oficial, permite transformação durante o ETL |
| Interface | Streamlit | protótipo funcional em horas, sem escrever frontend |
| LLM | SDK oficial do provedor, **sem LangChain** | NL→Query são 2 chamadas HTTP + um `aggregate()`; abstração de framework custaria depuração opaca justamente no ponto que o projeto precisa demonstrar |

**Falar:** essa é uma decisão deliberada, não falta de conhecimento — justificar em uma frase o porquê de dispensar LangChain deixa boa impressão (mostra pensamento crítico sobre a stack sugerida, que é exatamente o que o item pede).

---

## 6. Organização do GitHub — ~1 min

**Mostrar:** o repositório aberto no navegador — README, estrutura de pastas, histórico de commits.

**Falar:**
- Estrutura separada por responsabilidade: `app/` (interface), `core/` (Semana 2 — orquestração e LLM), `scripts/` (ETL e consultas), `docs/` (relatório e arquitetura), `tests/`.
- Status da entrega documentado no próprio README (tabela de checklist).

> **Atenção:** o commit inicial local já foi feito. Ainda falta: criar o repositório remoto no GitHub, dar `git push`, e cada integrante (Gabriel, João Pedro, Vitor, Vítor) fazer pelo menos um commit próprio — o item pede commits de **todos os integrantes**, não só de quem organizou o repo.

---

## 7. Protótipo Inicial da Interface — ~1,5–2 min

**Mostrar (comando ao vivo):**
```bash
streamlit run app/main.py
```

**Roteiro da demo:**
1. Mostrar a tela inicial e o aviso "Modo protótipo — dados simulados".
2. Digitar (ou escolher no selectbox) a pergunta **"qual a distribuição das notas?"** e clicar **Consultar**.
3. Mostrar as 3 abas do resultado: **Explicação** (texto em português), **Consulta MongoDB** (pipeline de agregação gerado) e **Resultados** (tabela + gráfico).
4. Mostrar o histórico na barra lateral — clicar numa pergunta anterior e mostrar que ela recarrega o resultado.

**Falar:** os dados são mockados propositalmente — o objetivo desta etapa é validar navegação e organização das telas antes de plugar o backend real (`core/`) na Semana 2. Os números do mock já são os números reais medidos na base (não inventados), então a demo já "parece" com o que a Semana 2 vai produzir de verdade.

---

## Perguntas prováveis da professora (preparar resposta)

- **"Por que MongoDB e não relacional?"** → `details` tem esquema aberto e variável por produto (20 chaves distintas, frequências muito diferentes); modelar isso em SQL exigiria uma tabela EAV ou muitas colunas nulas. Consulta 7 descobre esse esquema em tempo de consulta.
- **"Por que duas coleções e não uma só embutida?"** → um produto (Amazon Reload) tem 36.863 avaliações; embutir replicaria o documento de produto 36.863 vezes. Referência por `parent_asin` + `$lookup` sob demanda é o padrão recomendado do Mongo para 1:N com N alto.
- **"O índice está sendo usado?"** → sim para o filtro (IXSCAN no composto `verified_purchase+rating`), mas não para o `sort` por `helpful_vote` — por isso aparece um SORT em memória. Ponto de melhoria conhecido, não escondido.
- **"Como vai integrar o LLM na Semana 2?"** → `core/orquestrador.py` chama o tradutor (LLM #1, temperatura 0, saída em JSON de pipeline), valida contra a lista de operadores proibidos, executa, e passa o resultado para o explicador (LLM #2, temperatura 0,7).
