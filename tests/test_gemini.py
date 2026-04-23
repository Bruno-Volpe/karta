"""Smoke test — verifica se a conexão com o Gemini está funcionando."""
from agent import run


def test_gemini_conectado():
    messages = [{"role": "user", "content": "reply with just: ok"}]
    text = run(messages)
    assert text
    print(f"\nResposta: {text}")
