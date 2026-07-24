"""
DataChat NoSQL — Validador de segurança (RF07).

Componente separado do executor, de propósito. Um LLM vai gerar um
`deleteMany` ou um `$out` sobre `reviews` um dia — o projeto não pode depender
do modelo se comportar bem (ver Seção 4.4a do RELATORIO_SEMANA1.md). Tudo que
chega aqui é tratado como não confiável, mesmo vindo do próprio tradutor.

Regras:
  - só as coleções em COLECOES_PERMITIDAS podem ser lidas (via $lookup também);
  - nenhum estágio/operador de escrita ou execução arbitrária de código;
  - nenhuma das palavras de comando bloqueadas do RF07 em qualquer chave;
  - todo pipeline sai daqui com $limit <= LIMITE_MAXIMO.
"""

COLECOES_PERMITIDAS = {"reviews", "products"}

ESTAGIOS_PROIBIDOS = {
    "$out", "$merge",                          # escrevem no banco
    "$function", "$accumulator", "$where",     # executam JavaScript arbitrário
    "$currentOp", "$indexStats", "$listSessions", "$listLocalSessions",
    "$planCacheStats", "$collStats",
}

# RF07: bloquear literalmente estes comandos, caso apareçam como chave em
# qualquer nível do pipeline (defesa extra além dos estágios proibidos acima).
PALAVRAS_PROIBIDAS = {
    "insert", "insertone", "insertmany",
    "update", "updateone", "updatemany",
    "delete", "deleteone", "deletemany", "remove",
    "drop", "dropcollection", "dropdatabase",
    "createcollection", "renamecollection",
}

LIMITE_MAXIMO = 100


class ValidadorError(Exception):
    """Pipeline rejeitado. A mensagem é devolvida ao LLM no retry de autocorreção."""


def _varrer(valor, caminho: str = "$"):
    """Percorre o pipeline inteiro (dicts e listas aninhadas) procurando chaves proibidas."""
    if isinstance(valor, dict):
        for chave, sub in valor.items():
            chave_normalizada = chave.lower().lstrip("$")
            if chave in ESTAGIOS_PROIBIDOS:
                raise ValidadorError(f'Estágio "{chave}" não é permitido (RF07 — apenas leitura).')
            if chave_normalizada in PALAVRAS_PROIBIDAS:
                raise ValidadorError(f'Operação "{chave}" não é permitida (RF07 — apenas leitura).')
            _varrer(sub, f"{caminho}.{chave}")
    elif isinstance(valor, list):
        for item in valor:
            _varrer(item, caminho)


def _checar_colecoes_referenciadas(pipeline: list[dict]):
    """$lookup pode referenciar outra coleção — também precisa estar na allowlist."""
    for estagio in pipeline:
        lookup = estagio.get("$lookup") if isinstance(estagio, dict) else None
        if isinstance(lookup, dict) and "from" in lookup:
            colecao = lookup["from"]
            if colecao not in COLECOES_PERMITIDAS:
                raise ValidadorError(
                    f'$lookup referencia coleção não permitida: "{colecao}". '
                    f"Coleções permitidas: {sorted(COLECOES_PERMITIDAS)}."
                )


def _forcar_limite(pipeline: list[dict]) -> list[dict]:
    tem_limit = False
    for estagio in pipeline:
        if isinstance(estagio, dict) and "$limit" in estagio:
            tem_limit = True
            if estagio["$limit"] > LIMITE_MAXIMO:
                estagio["$limit"] = LIMITE_MAXIMO
    if not tem_limit:
        pipeline = [*pipeline, {"$limit": LIMITE_MAXIMO}]
    return pipeline


def validar(colecao: str, pipeline: list[dict]) -> list[dict]:
    """Valida e devolve o pipeline (possivelmente com $limit ajustado/injetado).

    Levanta ValidadorError com uma mensagem clara caso o pipeline seja rejeitado.
    """
    if colecao not in COLECOES_PERMITIDAS:
        raise ValidadorError(
            f'Coleção não permitida: "{colecao}". Coleções permitidas: {sorted(COLECOES_PERMITIDAS)}.'
        )
    if not isinstance(pipeline, list) or not pipeline:
        raise ValidadorError("Pipeline vazio ou em formato inválido.")

    _varrer(pipeline)
    _checar_colecoes_referenciadas(pipeline)

    return _forcar_limite(pipeline)
