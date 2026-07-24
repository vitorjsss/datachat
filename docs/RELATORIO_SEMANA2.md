# DataChat NoSQL — Relatório da Semana 2

**Equipe:** Gabriel Azevedo Lira de Farias, João Pedro de Queiroz Dantas, Vitor Jesus Mamede Soares, Vítor Raimundo Fernandes Gabínio
**Disciplina:** _(preencher)_
**Data:** _(preencher)_
**Repositório:** _(link do GitHub)_

> Continuação de `docs/RELATORIO_SEMANA1.md`. O cronograma do enunciado do
> projeto define a Semana 2 como: **"desenvolver consultas MongoDB; criar
> prompts; implementar geração automática de consultas; validar
> resultados."** As consultas MongoDB já foram entregues na Semana 1 (8
> consultas em `scripts/consultas.py`). Este relatório cobre os três itens
> restantes — e só eles. Integração completa de backend, histórico e
> tratamento de erros são Semana 3 no próprio cronograma; interface é
> Semana 4. Ver Seção 4 para o que foi deliberadamente deixado de fora
> desta entrega.

---

## 1. Objetivo da semana

| Item do cronograma | O que foi feito | Onde |
|---|---|---|
| Criar prompts | Prompt de sistema com contexto de esquema real + 3 exemplos few-shot | `core/esquema.py`, `core/tradutor.py` |
| Implementar geração automática de consultas | Pergunta em português → pipeline MongoDB, via LLM (RF04) | `core/tradutor.py` |
| Validar resultados | Metodologia de validação em duas etapas (JSON válido + execução real no Mongo), aplicada às 7 perguntas mais difíceis do projeto | `scripts/comparar_llms.py` |

---

## 2. Criar prompts

### 2.1 Contexto de esquema (`core/esquema.py`)

O prompt não pode listar só nomes de campo — teria o mesmo problema já
identificado na Seção 1.5 do relatório da Semana 1: se o prompt disser
apenas que `price` existe, o LLM filtra por preço como se fosse universal e
descarta dois terços do catálogo sem avisar (o campo está preenchido em só
33,4% dos produtos). Por isso `contexto_esquema()` consulta o MongoDB **na
hora** e devolve, para cada campo, o tipo e o % de preenchimento real —
o mesmo dado medido em `scripts/perfilar.py`.

### 2.2 Estrutura do prompt (`core/tradutor.py`)

O prompt de sistema é montado em três partes:

1. **Contexto de esquema** — gerado dinamicamente (Seção 2.1)
2. **Formato de saída exigido** — sempre um objeto
   `{"colecao": "reviews"|"products", "pipeline": [...]}`, mesmo para
   filtros simples (um único estágio `$match` em vez de `find()`), para
   manter uma única forma de execução
3. **3 exemplos few-shot**, escolhidos por cobrirem os padrões mais difíceis
   de gerar corretamente: filtro simples, `$lookup`+`$unwind` (junção entre
   coleções) e `$objectToArray`+`$unwind` (descoberta de esquema aberto em
   `details`)

```python
# core/tradutor.py — formato de saída exigido
"""
Responda APENAS com um objeto JSON no formato:
{"colecao": "reviews" ou "products", "pipeline": [...]}
...
Sempre inclua $limit (no máximo 100) a menos que a pergunta peça
uma contagem/agregação de valor único.
"""
```

---

## 3. Escolha do LLM — comparação medida, não estimada

Antes de fixar o LLM que os prompts da Seção 2 chamariam, medimos em vez de
estimar — a Semana 1 tinha deixado a escolha em aberto ("a definir", ver
Seção 5.4 do relatório anterior).

### 3.1 Restrição real de hardware

O notebook usado no projeto é um **MacBook Air M1 com 8 GB de RAM**,
compartilhada entre sistema, Docker (MongoDB) e o resto da stack. Isso
descarta um modelo local grande como o Llama 3 8B (~4,7 GB só o modelo). O
maior modelo local viável é o **Llama 3.2 3B** (~2 GB quantizado, via
Ollama).

### 3.2 Metodologia

`scripts/comparar_llms.py` roda as mesmas 7 perguntas do projeto (as mais
difíceis da Seção 3 da Semana 1, incluindo `$lookup`+`$unwind` e
`$objectToArray`+`$unwind`) em dois candidatos gratuitos — **Gemini** (API
Google, *free tier*) e **Llama 3.2 3B local** — com o mesmo prompt de
sistema. Cada resposta é avaliada em duas etapas objetivas: o JSON veio
válido? o pipeline executa sem erro contra o MongoDB carregado? O log bruto
está em `docs/comparacao_llms.txt`.

### 3.3 Resultado

| | Gemini (`gemini-flash-lite-latest`) | Llama 3.2 3B (local) |
|---|---|---|
| JSON válido | **7/7** | 4/7 |
| Executou sem erro no MongoDB | **7/7** | 1/7 |
| Tempo médio de resposta | 4,6s | 7,3s |

O Llama local errou de formas específicas e reproduzíveis: JSON malformado
(esqueceu aspas em operadores como `$gt`/`$avg`, cortou a resposta no
meio), inventou uma opção inexistente do MongoDB (`preserveNullValues` em
`$unwind`), e confundiu variável dentro de `$objectToArray` (`$$value`
indefinida). É o padrão de falha em "saída estruturada com aninhamento" que
a Seção 5.4 da Semana 1 já antecipava para modelos pequenos.

### 3.4 Decisão

**Gemini, via `google-genai`.** Ajuste feito dentro da própria família: o
alias `gemini-flash-latest` aponta hoje para um modelo cuja cota gratuita é
de só 20 requisições/dia — trocamos para `gemini-flash-lite-latest`, que
mantém a mesma taxa de acerto com uma cota muito mais generosa.

---

## 4. Implementar geração automática de consultas (RF04)

`core/tradutor.py` expõe uma função `traduzir(pergunta, esquema_contexto,
cliente)` que chama o Gemini com `response_mime_type="application/json"` e
temperatura 0, usando o prompt descrito na Seção 2. A resposta é
desserializada e validada estruturalmente (tem `colecao`? tem `pipeline`?
`pipeline` é uma lista não vazia?) antes de ser considerada válida — essa é
a primeira camada da validação de resultados descrita a seguir.

---

## 5. Validar resultados

"Validar resultados" nesta etapa significa: **confirmar que a consulta
gerada automaticamente pelo LLM é sintaticamente válida e produz um
resultado real ao rodar contra o MongoDB** — não confundir com um validador
de segurança contra operação destrutiva, que é uma preocupação de backend
tratada formalmente na Semana 3 (ver Seção 4 do cronograma: "tratamento de
erros").

A validação foi feita em duas frentes:

1. **Automatizada, nas 7 perguntas mais difíceis** — `scripts/comparar_llms.py`
   (Seção 3), com o resultado 7/7 já reportado.
2. **Manual, em casos extras** — reverificamos à mão os dois padrões mais
   difíceis (`$objectToArray`+`$unwind` e `$lookup`+`$unwind`) depois de
   trocar de `gemini-flash-latest` para `gemini-flash-lite-latest` (Seção
   3.4), para confirmar que a troca de modelo não perdeu qualidade.

Em ambos os casos, "resultado válido" significa: o JSON parseia, o
`aggregate()` roda sem lançar erro do MongoDB, e o pipeline gerado
corresponde semanticamente à pergunta feita (conferido manualmente contra
o pipeline de referência de `scripts/consultas.py`, quando aplicável).

---

## 6. Fora do escopo desta entrega

Para não antecipar o cronograma, os itens abaixo **não** são reivindicados
como entrega da Semana 2, mesmo que uma versão inicial já exista no
repositório — foi necessário um executor mínimo (`core/executor.py`) só
para poder *rodar* as consultas na validação da Seção 5. A formalização de
cada um fica para as semanas indicadas no próprio cronograma do projeto:

| Item | Onde já existe um protótipo | Semana prevista no cronograma |
|---|---|---|
| Integração completa MongoDB + LLM em um backend único | `core/orquestrador.py` | Semana 3 — "integrar MongoDB + LLM; desenvolver backend" |
| Bloqueio formal de operação destrutiva (RF07) | `core/validador.py` | Semana 3 — "desenvolver backend" |
| Histórico de consultas (RF08) | protótipo em `app/main.py` | Semana 3 — "implementar histórico" |
| Tratamento de erros / retry (RF09) | protótipo em `core/orquestrador.py` | Semana 3 — "tratamento de erros" |
| Interface final religada ao backend | protótipo em `app/main.py` | Semana 4 — "desenvolver interface" |

---

## 7. Próximos passos (Semana 3, conforme cronograma)

- Integrar MongoDB + LLM em um fluxo de backend único e testado
- Formalizar o bloqueio de operações destrutivas (RF07), com testes
  adversariais
- Implementar histórico persistente de consultas (RF08)
- Tratamento de erros — pergunta ambígua, campo inexistente, consulta sem
  resultado (RF09)
