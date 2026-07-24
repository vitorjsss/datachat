# Roteiro de Apresentação — Semana 2

> Script de fala mapeado slide a slide (`docs/slides_semana2.html`, 9 slides,
> tema claro fixo). Escopo desta semana, conforme o cronograma do projeto:
> **criar prompts; implementar geração automática de consultas; validar
> resultados** ("desenvolver consultas MongoDB" já foi entregue na Semana 1).
> Para a demo ao vivo, use `docs/ROTEIRO_DEMO_SEMANA2.md` — o Slide 9 é a
> deixa para abrir o terminal.

**Tempo estimado desta parte:** ~4 min (a demo prática soma mais ~3-4 min).

## Divisão de falas

| Integrante | Responsável por |
|---|---|
| **Gabriel Azevedo Lira de Farias** | Slides 1–3 — título, objetivo da semana, criação de prompts |
| **João Pedro de Queiroz Dantas** | Slides 4–6 — comparativo de LLM, por que o Llama perdeu, geração automática de consultas |
| **Vítor Raimundo Fernandes Gabínio** | Slides 7–9 — validar resultados, delimitação de escopo, próximos passos e transição para a demo |
| **Vitor Jesus Mamede Soares** | Demonstração prática ao vivo — `docs/ROTEIRO_DEMO_SEMANA2.md` |

Cada seção abaixo já indica "Quem fala" — combinar a ordem de entrada antes
de subir no palco, pra não perder tempo passando o notebook de mão em mão.

---

## Antes de abrir o slide

```bash
open docs/slides_semana2.html
```

Navegação: setas ← → do teclado, ou os botões no canto inferior direito.
`Cmd+P` no navegador exporta para PDF (cada seção já quebra em uma página).

---

## Slide 1 — Título

**Quem fala:** Gabriel Azevedo Lira de Farias

**Falar:**
- "Na Semana 1 entregamos base, esquema, consultas e a arquitetura no
  papel. O cronograma do projeto define a Semana 2 como três coisas: criar
  prompts, implementar geração automática de consultas, e validar
  resultados. É só isso que vamos apresentar hoje — o resto (backend
  integrado, histórico, tratamento de erro, interface) é Semana 3 e 4 no
  próprio cronograma, e não queremos nos adiantar."

---

## Slide 2 — Objetivo da semana

**Quem fala:** Gabriel Azevedo Lira de Farias

**Falar:**
- "'Desenvolver consultas MongoDB' já foi entregue na Semana 1 — são as 8
  consultas de `scripts/consultas.py`. O que restava são estes três itens."
- Apontar cada célula: "criar prompts — como montamos o contexto que vai
  pro LLM; geração automática de consultas — RF04, a pergunta virando
  pipeline; validar resultados — confirmar que o que o LLM gera realmente
  funciona contra o banco."
- "Mais pra frente, no Slide 8, mostramos explicitamente o que ficou de
  fora de propósito."

---

## Slide 3 — Criar prompts

**Quem fala:** Gabriel Azevedo Lira de Farias *(última fala antes de passar para João Pedro)*

**Falar:**
- "O prompt tem três partes. Primeiro, o contexto de esquema — e aqui vale
  destacar que não é uma string fixa, é gerado consultando o MongoDB na
  hora, com o percentual de preenchimento real de cada campo. Isso vem
  direto de um achado da Semana 1: se o prompt só disser que `price`
  existe, sem dizer que só 33% dos produtos têm esse campo preenchido, o
  LLM filtra por preço e descarta dois terços do catálogo sem avisar."
- "Segundo, o formato de saída exigido — sempre `{colecao, pipeline}`, pra
  ter uma única forma de executar depois."
- "Terceiro, três exemplos few-shot, escolhidos pelos padrões mais difíceis
  de acertar: junção entre coleções e descoberta de esquema aberto."

---

## Slide 4 — Comparativo de LLM

**Quem fala:** João Pedro de Queiroz Dantas

**Falar:**
- "Antes de escrever esses prompts, precisávamos decidir pra qual modelo
  eles seriam escritos. Em vez de estimar, medimos: rodamos as mesmas 7
  perguntas mais difíceis do projeto em dois candidatos gratuitos — Gemini
  na nuvem, e Llama 3.2 3B local — e conferimos duas coisas objetivas: o
  JSON veio válido? o pipeline rodou sem erro no MongoDB de verdade?"
- "Gemini acertou 7 de 7 nas duas métricas. O Llama local só acertou 1 de 7
  execuções, e ainda foi mais lento."

---

## Slide 5 — Por que o Llama perdeu

**Quem fala:** João Pedro de Queiroz Dantas

**Falar:**
- "Vale mostrar os erros específicos, porque não é 'o modelo é ruim' de
  forma vaga — são falhas concretas, reproduzíveis, e estão no log completo
  em `docs/comparacao_llms.txt`."
- Ler os três: "esqueceu aspas no meio do JSON", "inventou uma opção que
  não existe no MongoDB", "confundiu uma variável dentro de um operador
  mais complexo."
- "Isso decidiu pra qual modelo os prompts do Slide 3 foram escritos:
  Gemini."

---

## Slide 6 — Geração automática de consultas (RF04)

**Quem fala:** João Pedro de Queiroz Dantas *(última fala antes de passar para Vítor Raimundo)*

**Falar:**
- "Isso é o RF04 do enunciado: gerar consultas automaticamente via LLM.
  `core/tradutor.py` é uma função só — recebe a pergunta e o contexto de
  esquema, chama o Gemini com temperatura zero e saída forçada em JSON, e
  devolve sempre no mesmo formato: coleção mais pipeline."
- "Temperatura zero porque aqui não queremos criatividade, queremos
  previsibilidade — é a mesma lógica que já estava desenhada na arquitetura
  da Semana 1."

---

## Slide 7 — Validar resultados

**Quem fala:** Vítor Raimundo Fernandes Gabínio

**Falar:**
- "Este é o terceiro item do cronograma, e é importante não confundir com
  segurança — validar resultados aqui significa confirmar que o pipeline
  gerado automaticamente é executável e corresponde à pergunta, não
  bloquear operação destrutiva. Isso é outra validação, que fica pra
  Semana 3."
- "Os números: 7 de 7 respostas com JSON válido, 7 de 7 rodando sem erro
  contra o MongoDB carregado de verdade — não é simulação."

---

## Slide 8 — O que fica para a Semana 3 e 4

**Quem fala:** Vítor Raimundo Fernandes Gabínio

**Falar:**
- "Pra sermos transparentes sobre o que é entrega desta semana e o que não
  é: já existe um protótipo inicial de backend integrado, de bloqueio de
  operação destrutiva, de histórico e de interface no repositório — foi
  necessário um executor mínimo só pra poder rodar a validação do Slide 7."
- "Mas nenhum desses itens está sendo apresentado como entrega formal da
  Semana 2, porque o cronograma do próprio projeto coloca cada um deles
  explicitamente nas semanas seguintes. Preferimos mostrar exatamente o que
  foi pedido, e não misturar trabalho adiantado como se fosse desta etapa."

---

## Slide 9 — Próximos passos (deixa para a demo)

**Quem fala:** Vítor Raimundo Fernandes Gabínio

**Falar:**
- "Pra Semana 3: integrar tudo isso num backend único, formalizar o
  bloqueio de operação destrutiva com testes adversariais, implementar
  histórico persistente, e tratamento de erro pra pergunta ambígua, campo
  inexistente e consulta sem resultado."
- **Transição para a demo:** "Mas em vez de só mostrar print, vamos rodar a
  geração de consulta e a validação ao vivo agora. Passo a palavra pro
  Vitor Jesus." → entregar o terminal e seguir
  `docs/ROTEIRO_DEMO_SEMANA2.md`.
