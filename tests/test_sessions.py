"""Smoke test — verifica se o Redis está de pé e as sessões funcionam."""
import pytest
from sessions import get_session, append_message, update_context, _get_redis


def test_redis_conectado():
    r = _get_redis()
    assert r is not None, "Redis não está acessível — rode: docker compose up redis"
    assert r.ping()
    print("\nRedis: OK")


def test_session_persiste_no_redis():
    r = _get_redis()
    assert r is not None, "Redis não está acessível"

    sid = "test-smoke-redis"
    r.delete(f"session:{sid}")  # limpa antes

    append_message(sid, "user", "olá")
    update_context(sid, search_id="abc-123")

    session = get_session(sid)
    assert session["messages"][0]["content"] == "olá"
    assert session["context"]["search_id"] == "abc-123"
    print(f"\nSessão {sid}: {len(session['messages'])} mensagem(s), context={session['context']}")
