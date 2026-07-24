"""Testes do validador de segurança — RF07.

Roda sem MongoDB, sem LLM. É o item que a banca mais testa ao vivo
("apague todas as avaliações"), por isso os casos adversariais vêm primeiro.

Uso:
    pytest tests/test_validador.py -v
"""

import pytest

from core.validador import LIMITE_MAXIMO, ValidadorError, validar


# ─────────────────────────────────────────────────────────────────────
# Casos adversariais — o pipeline DEVE ser rejeitado
# ─────────────────────────────────────────────────────────────────────

def test_bloqueia_delete_many_disfarcado_de_estagio():
    with pytest.raises(ValidadorError):
        validar("reviews", [{"$match": {}}, {"deleteMany": {}}])


def test_bloqueia_drop_collection():
    with pytest.raises(ValidadorError):
        validar("reviews", [{"dropCollection": "reviews"}])


def test_bloqueia_out():
    with pytest.raises(ValidadorError):
        validar("reviews", [{"$match": {"rating": 5}}, {"$out": "reviews_copia"}])


def test_bloqueia_merge():
    with pytest.raises(ValidadorError):
        validar("reviews", [{"$match": {}}, {"$merge": {"into": "reviews"}}])


def test_bloqueia_function_javascript_arbitrario():
    with pytest.raises(ValidadorError):
        validar("reviews", [{"$match": {"$expr": {"$function": {
            "body": "function() { return true; }", "args": [], "lang": "js"}}}}])


def test_bloqueia_where():
    with pytest.raises(ValidadorError):
        validar("reviews", [{"$match": {"$where": "this.rating > 0"}}])


def test_bloqueia_colecao_fora_da_allowlist():
    with pytest.raises(ValidadorError):
        validar("usuarios_admin", [{"$match": {}}])


def test_bloqueia_lookup_para_colecao_nao_permitida():
    with pytest.raises(ValidadorError):
        validar("reviews", [
            {"$lookup": {"from": "system.users", "localField": "a",
                         "foreignField": "b", "as": "x"}},
        ])


def test_bloqueia_palavra_proibida_em_letras_maiusculas():
    """RF07 não deve depender de case sensitivity."""
    with pytest.raises(ValidadorError):
        validar("reviews", [{"UPDATE": {"rating": 1}}])


def test_bloqueia_estagio_proibido_aninhado_dentro_de_outro_estagio():
    with pytest.raises(ValidadorError):
        validar("reviews", [
            {"$facet": {"a": [{"$out": "cópia"}]}},
        ])


# ─────────────────────────────────────────────────────────────────────
# Casos válidos — o pipeline DEVE passar
# ─────────────────────────────────────────────────────────────────────

def test_permite_pipeline_de_leitura_simples():
    resultado = validar("reviews", [{"$match": {"rating": 5.0}}, {"$limit": 10}])
    assert resultado[-1] == {"$limit": 10}


def test_permite_lookup_entre_colecoes_permitidas():
    pipeline = [
        {"$group": {"_id": "$parent_asin", "total": {"$sum": 1}}},
        {"$lookup": {"from": "products", "localField": "_id",
                     "foreignField": "parent_asin", "as": "produto"}},
        {"$limit": 10},
    ]
    resultado = validar("reviews", pipeline)
    assert resultado == pipeline


def test_injeta_limit_quando_ausente():
    resultado = validar("reviews", [{"$match": {"rating": 5.0}}])
    assert resultado[-1] == {"$limit": LIMITE_MAXIMO}


def test_reduz_limit_acima_do_maximo():
    resultado = validar("reviews", [{"$match": {}}, {"$limit": 99999}])
    assert resultado[-1]["$limit"] == LIMITE_MAXIMO


def test_nao_injeta_limit_duplicado_quando_ja_existe():
    resultado = validar("reviews", [{"$match": {}}, {"$limit": 5}])
    assert sum(1 for e in resultado if "$limit" in e) == 1


def test_rejeita_pipeline_vazio():
    with pytest.raises(ValidadorError):
        validar("reviews", [])


def test_rejeita_pipeline_nao_lista():
    with pytest.raises(ValidadorError):
        validar("reviews", {"$match": {}})
