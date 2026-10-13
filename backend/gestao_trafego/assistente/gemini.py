"""Cliente mínimo do Gemini (API REST) com chamada de funções.

O modelo recebe a pergunta e as declarações das ferramentas de `ferramentas.py`. Quando quer um dado, devolve
um `functionCall`; este módulo executa a ferramenta, devolve o resultado como `functionResponse` e repete,
até o modelo escrever a resposta final. A chave vai no cabeçalho (nunca no URL, que fica nos registos) e só
existe no servidor.
"""

from collections.abc import Callable
from dataclasses import dataclass, field

import httpx

URL = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
MAXIMO_DE_VOLTAS = 5  # um modelo que pede ferramentas sem parar não pode prender o pedido para sempre

INSTRUCCAO_DO_SISTEMA = """És o assistente de análise do sistema de gestão de tráfego com IA para Maputo (protótipo de uma monografia).
Respondes SEMPRE em português europeu, de forma curta, clara e para quem não é técnico.

Regras:
- Usa só os resultados das ferramentas. Não inventes números, vias, horas nem acidentes. Se uma ferramenta não tem o dado, di-lo.
- Repete os avisos que as ferramentas devolvem (valores assumidos, resultados de simulação, dados que não existem, precisão não medida).
- Os resultados vêm de simulações e de vídeos de teste (não são de Maputo): nunca os apresentes como medições reais da cidade.
- Não há dados de acidentes reais. Não digas que o sistema reduz acidentes; podes falar de colisões simuladas e bloqueios.
- Não consegues alterar semáforos nem correr simulações; só consultar resultados.
- Quando compares configurações, diz os números (espera média em segundos e a variação face ao tempo fixo) e a honestidade da conclusão.
"""


class ErroDoAssistente(Exception):
    """Falha ao falar com o Gemini (rede, chave, modelo, resposta inesperada). A mensagem é para o utilizador."""


@dataclass
class RespostaDoModelo:
    texto: str
    ferramentas_usadas: list[str] = field(default_factory=list)


class ClienteGemini:
    def __init__(self, chave: str, modelo: str, transporte: httpx.BaseTransport | None = None, tempo_limite_s: float = 60.0):
        self._chave, self._modelo = chave, modelo
        self._http = httpx.Client(transport=transporte, timeout=tempo_limite_s)

    def _pedir(self, corpo: dict) -> dict:
        try:
            resposta = self._http.post(URL.format(modelo=self._modelo), json=corpo, headers={"x-goog-api-key": self._chave})
        except httpx.HTTPError as erro:
            raise ErroDoAssistente(f"Não foi possível falar com o Gemini: {type(erro).__name__}.") from erro
        if resposta.status_code != 200:
            # Só se mostra o código e a mensagem curta: o corpo pode repetir a chave ou detalhes do pedido.
            detalhe = ""
            try:
                detalhe = resposta.json().get("error", {}).get("message", "")[:200]
            except ValueError:
                pass
            raise ErroDoAssistente(f"O Gemini recusou o pedido (HTTP {resposta.status_code}). {detalhe}".strip())
        return resposta.json()

    def conversar(
        self,
        pergunta: str,
        declaracoes: list[dict],
        executar_ferramenta: Callable[[str, dict], dict],
        historico: list[dict] | None = None,
        sistema: str = INSTRUCCAO_DO_SISTEMA,
    ) -> RespostaDoModelo:
        conteudos = [*(historico or []), {"role": "user", "parts": [{"text": pergunta}]}]
        usadas: list[str] = []
        for _ in range(MAXIMO_DE_VOLTAS):
            dados = self._pedir(
                {
                    "systemInstruction": {"parts": [{"text": sistema}]},
                    "contents": conteudos,
                    "tools": [{"functionDeclarations": declaracoes}],
                    "generationConfig": {"temperature": 0.2},
                }
            )
            try:
                partes = dados["candidates"][0]["content"]["parts"]
            except (KeyError, IndexError, TypeError) as erro:
                raise ErroDoAssistente("O Gemini devolveu uma resposta vazia (pode ter sido bloqueada).") from erro
            chamadas = [p["functionCall"] for p in partes if "functionCall" in p]
            if not chamadas:
                texto = "".join(p.get("text", "") for p in partes).strip()
                if not texto:
                    raise ErroDoAssistente("O Gemini não escreveu nenhuma resposta.")
                return RespostaDoModelo(texto, usadas)
            conteudos.append({"role": "model", "parts": partes})
            respostas = []
            for chamada in chamadas:
                nome = chamada.get("name", "")
                usadas.append(nome)
                respostas.append({"functionResponse": {"name": nome, "response": {"resultado": executar_ferramenta(nome, chamada.get("args") or {})}}})
            conteudos.append({"role": "user", "parts": respostas})
        raise ErroDoAssistente("O Gemini pediu ferramentas demasiadas vezes sem chegar a uma resposta.")
