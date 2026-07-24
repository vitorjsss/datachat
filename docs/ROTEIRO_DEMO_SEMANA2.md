# Roteiro da Demo Prática — Semana 2

> Guia de "mãos na massa": comandos exatos, na ordem certa, e o que falar
> enquanto roda. Usar depois do Slide 9 de `docs/slides_semana2.html`
> (ver `docs/ROTEIRO_APRESENTACAO_SEMANA2.md`).
>
> **Escopo desta demo, de propósito:** só os três itens da Semana 2 —
> prompt, geração automática de consulta (RF04), validação do resultado.
> Não entra: interface Streamlit, histórico, bloqueio de operação
> destrutiva (RF07) — isso é Semana 3/4 e está listado como "fora do
> escopo" no Slide 8, então não faz sentido demonstrar como se já fosse
> entrega desta semana.

**Responsável:** Vitor Jesus Mamede Soares.
**Tempo estimado:** ~3–4 min.

---

## 1. Pré-voo — fazer 30–60 min antes da sala

```bash
cd datachat   # ou o nome da pasta do projeto
source .venv/bin/activate

# 1. Docker + MongoDB de pé
docker start mongo-datachat
docker ps --filter name=mongo-datachat        # deve mostrar "Up"

# 2. Confirmar que os dados ainda estão carregados
python3 -c "
from pymongo import MongoClient
db = MongoClient('mongodb://localhost:27017')['datachat']
print('reviews:', db.reviews.count_documents({}))
print('products:', db.products.count_documents({}))
"
# esperado: reviews: 152410 / products: 1137

# 3. Chave do Gemini configurada
grep GOOGLE_API_KEY .env      # não pode estar vazia

# 4. Teste completo do que vamos mostrar ao vivo: gerar + validar
python3 -c "
from dotenv import load_dotenv; load_dotenv()
from pymongo import MongoClient
from google import genai
import os
from core.esquema import contexto_esquema
from core.tradutor import traduzir
from core.executor import executar

db = MongoClient('mongodb://localhost:27017')['datachat']
cliente = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))
esquema = contexto_esquema(db)

dados = traduzir('Qual a distribuição das notas na base?', esquema, cliente)
print('gerado:', dados)

resultados = executar(db, dados['colecao'], dados['pipeline'])
print('validado — documentos retornados:', len(resultados))
"
# esperado: imprime {"colecao": ..., "pipeline": [...]} e depois um número > 0
```

Se algum desses falhar, ver a Seção 5 (Plano B) **antes** de subir no palco.

## 2. 5 minutos antes de começar

Deixar aberto: um terminal com fonte grande, e uma aba com
`docs/slides_semana2.html` pronta pro Slide 1. Não precisa do Streamlit
rodando — a demo desta semana é toda em terminal.

---

## 3. Roteiro da demo (o que fazer, o que falar)

### Passo 1 — Mostrar o prompt sendo montado (30s)

```bash
python3 -c "
from dotenv import load_dotenv; load_dotenv()
from pymongo import MongoClient
from core.esquema import contexto_esquema
db = MongoClient('mongodb://localhost:27017')['datachat']
print(contexto_esquema(db))
"
```

**Falar enquanto roda:** "Isso é o contexto de esquema que entra no prompt
— gerado agora, consultando o MongoDB, não é uma string fixa no código.
Reparem no `%` de preenchimento ao lado de cada campo — é isso que evita o
LLM filtrar por um campo que só existe em um terço dos documentos sem
avisar ninguém."

### Passo 2 — Gerar uma consulta ao vivo (RF04) (1 min)

Pedir pra alguém da plateia sugerir uma pergunta em português sobre a base
(ou usar uma pronta, tipo "quais os produtos com pior nota média, com pelo
menos 20 avaliações?").

```bash
python3 -c "
from dotenv import load_dotenv; load_dotenv()
from pymongo import MongoClient
from google import genai
import os, json
from core.esquema import contexto_esquema
from core.tradutor import traduzir

db = MongoClient('mongodb://localhost:27017')['datachat']
cliente = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))
esquema = contexto_esquema(db)

dados = traduzir('PERGUNTA AQUI', esquema, cliente)
print(json.dumps(dados, indent=2, ensure_ascii=False))
"
```

(Trocar `PERGUNTA AQUI` pela pergunta escolhida, ao vivo, na frente da
turma.)

**Falar:** "Essa chamada só faz uma coisa — pergunta em português entra,
`{colecao, pipeline}` sai, sempre nesse formato, com temperatura zero pra
ser previsível. Isso é o `core/tradutor.py`, o RF04 do enunciado."

### Passo 3 — Validar o resultado (1 min)

Pegar o pipeline que acabou de ser gerado no Passo 2 e rodar de verdade:

```bash
python3 -c "
from dotenv import load_dotenv; load_dotenv()
from pymongo import MongoClient
from google import genai
import os
from core.esquema import contexto_esquema
from core.tradutor import traduzir
from core.executor import executar

db = MongoClient('mongodb://localhost:27017')['datachat']
cliente = genai.Client(api_key=os.getenv('GOOGLE_API_KEY'))
esquema = contexto_esquema(db)

dados = traduzir('PERGUNTA AQUI', esquema, cliente)
resultados = executar(db, dados['colecao'], dados['pipeline'])
print(f'{len(resultados)} documento(s) retornado(s)')
for r in resultados[:3]:
    print(' ', r)
"
```

**Falar:** "Isso é a validação — não é só olhar se o JSON tem a cara certa,
é rodar de verdade contra o banco carregado e conferir que volta
resultado. Fizemos isso sistematicamente nas 7 perguntas mais difíceis do
projeto, não só nessa aqui."

### Passo 4 — Mostrar a evidência agregada

```bash
open docs/comparacao_llms.txt   # ou: cat docs/comparacao_llms.txt | less
```

**Falar:** "Esse é o log completo da validação nas 7 perguntas — pergunta
enviada, resposta bruta de cada modelo, se o JSON veio válido, se rodou
sem erro. 7 de 7 no Gemini, 1 de 7 no Llama local — é o que já mostramos
nos Slides 4 e 5."

### Passo 5 — Fechar (15s)

"Isso cobre os três itens da Semana 2: prompt, geração automática, e
validação — com dados reais, chave de API real, sem mock. Semana 3 é
juntar isso num backend integrado de verdade."

---

## 4. Bônus (só se sobrar tempo e perguntarem)

Já existe um protótipo mais completo no repositório — interface Streamlit,
bloqueio de operação destrutiva, explicação em linguagem natural — mas
isso é conteúdo de Semana 3/4, não estamos reivindicando como entrega de
hoje (ver Slide 8). Se a banca perguntar ou sobrar tempo:

```bash
streamlit run app/main.py
```

Deixar claro ao mostrar: "isso é um protótipo adiantado, ainda não é a
entrega formal — vamos apresentar ele com o devido peso na Semana 3."

---

## 5. Perguntas que a banca pode fazer (e a resposta rápida)

| Pergunta | Resposta |
|---|---|
| "Por que Gemini e não GPT/Claude?" | `docs/RELATORIO_SEMANA2.md` Seção 3 — testamos e medimos nas 7 perguntas mais difíceis, não decidimos por custo |
| "'Validar resultados' aqui é o mesmo que bloquear operação perigosa?" | Não — isso é RF07, fica pra Semana 3. Validar aqui é confirmar que o pipeline gerado roda e faz sentido, não segurança |
| "Cadê a interface?" | Existe um protótipo (RF08/RF09/interface), mas é escopo de Semana 3/4 no cronograma — não incluímos na entrega desta semana de propósito |
| "Testaram sem internet?" | Sim — por isso testamos o Llama local também; log completo em `docs/comparacao_llms.txt` |
| "Quanto custa rodar isso?" | Zero — Gemini free tier; única ressalva é o limite de requisições/dia do modelo, documentado no relatório |

---

## 6. Plano B — se algo falhar na hora

**Docker/MongoDB não sobe:**
```bash
docker start mongo-datachat
# se não existir o container:
docker run -d --name mongo-datachat -p 27017:27017 mongo:7
# (nesse caso os dados precisam ser reimportados — ver README.md)
```

**Gemini retorna erro de cota (429) ou sem internet no local:**
Não tente debugar ao vivo. Usar o log já salvo como evidência:
```bash
open docs/comparacao_llms.txt
```
Falar: "aqui está o log de uma execução real, com o pipeline completo
gerado pra cada pergunta — a lógica é a mesma, só não estamos chamando a
API ao vivo agora por [motivo]."

**Esqueceram de rodar o pré-voo:** priorizar, nesta ordem: Docker de pé →
confirmar contagem de documentos → só depois tentar a chamada ao Gemini.
