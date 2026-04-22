"""Smoke test — verifica se a conexão com o Gemini está funcionando."""
from agent import send_message, extract_text


def test_gemini_conectado():
    messages = [{"role": "user", "content": "responda apenas: ok"}]
    response = send_message(messages)
    text = extract_text(response)
    assert text
    print(f"\nResposta: {text}")
