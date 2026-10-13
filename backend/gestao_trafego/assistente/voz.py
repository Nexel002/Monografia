"""Síntese de voz (texto para áudio) no servidor, para o assistente poder falar.

Por ordem: Google Cloud Text-to-Speech, depois ElevenLabs. Se nenhuma chave existir, devolve `None` e o
browser usa a voz que já traz (`speechSynthesis`), sem custo. As chaves só existem no servidor.
"""

import base64

import httpx

from gestao_trafego.comum.configuracao import ler

LIMITE_DE_CARACTERES = 1500  # as respostas longas cortam-se: o áudio custa dinheiro e demora
URL_GOOGLE = "https://texttospeech.googleapis.com/v1/text:synthesize"
URL_ELEVENLABS = "https://api.elevenlabs.io/v1/text-to-speech/{voz}"


def preparar_texto(texto: str) -> str:
    """Limpa o markdown e limita o tamanho. Cortar a meio de uma frase soa mal: corta-se no último ponto."""
    limpo = texto.replace("**", "").replace("`", "").replace("#", "")
    limpo = " ".join(linha.lstrip("-• ").strip() for linha in limpo.splitlines() if linha.strip())
    if len(limpo) <= LIMITE_DE_CARACTERES:
        return limpo
    corte = limpo[:LIMITE_DE_CARACTERES]
    ultimo_ponto = corte.rfind(". ")
    return corte[: ultimo_ponto + 1] if ultimo_ponto > LIMITE_DE_CARACTERES // 2 else corte


def _google(texto: str, chave: str, http: httpx.Client) -> bytes | None:
    resposta = http.post(
        URL_GOOGLE,
        json={"input": {"text": texto}, "voice": {"languageCode": "pt-PT", "ssmlGender": "FEMALE"}, "audioConfig": {"audioEncoding": "MP3"}},
        headers={"x-goog-api-key": chave},
    )
    if resposta.status_code != 200:
        return None
    return base64.b64decode(resposta.json().get("audioContent", "")) or None


def _elevenlabs(texto: str, chave: str, voz: str, http: httpx.Client) -> bytes | None:
    resposta = http.post(
        URL_ELEVENLABS.format(voz=voz),
        params={"output_format": "mp3_44100_128"},
        json={"text": texto, "model_id": "eleven_multilingual_v2"},
        headers={"xi-api-key": chave},
    )
    return resposta.content if resposta.status_code == 200 and resposta.content else None


def sintetizar(texto: str, transporte: httpx.BaseTransport | None = None) -> tuple[bytes, str] | None:
    """(áudio MP3, tipo MIME), ou None se não houver voz de servidor disponível (o cliente usa a do browser)."""
    texto = preparar_texto(texto)
    if not texto:
        return None
    chave_google, chave_eleven, voz_eleven = ler("GOOGLE_TTS_API_KEY"), ler("ELEVEN_LABS_API_KEY"), ler("ELEVEN_LABS_VOICE_ID")
    with httpx.Client(transport=transporte, timeout=30) as http:
        for tentativa in (
            (lambda: _google(texto, chave_google, http)) if chave_google else None,
            (lambda: _elevenlabs(texto, chave_eleven, voz_eleven, http)) if chave_eleven and voz_eleven else None,
        ):
            if tentativa is None:
                continue
            try:
                audio = tentativa()
            except httpx.HTTPError:
                continue  # uma voz que falha não impede a seguinte
            if audio:
                return audio, "audio/mpeg"
    return None
