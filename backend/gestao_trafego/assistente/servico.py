"""O assistente: tenta o Gemini e, se falhar, responde em modo de segurança.

O resto do sistema só fala com esta classe. A chave e o modelo vêm de `backend/.env` (ver `.env.example`).
"""

from dataclasses import dataclass, field

import psycopg

from gestao_trafego.assistente import ferramentas, seguranca
from gestao_trafego.assistente.gemini import ClienteGemini, ErroDoAssistente
from gestao_trafego.comum.configuracao import ler

MAXIMO_DE_MENSAGENS_NO_HISTORICO = 10  # contexto a mais só aumenta o custo e o risco de o modelo se perder

PEDIDO_DO_RELATORIO = (
    "Escreve um relatório curto (no máximo 8 frases) para um júri de monografia, sobre o estado do sistema: compara as "
    "configurações de semáforos (cenário com via cortada), diz quanto erra a previsão, o que a visão computacional contou e "
    "o que NÃO está provado ou medido. Consulta as ferramentas que precisares."
)


@dataclass
class Resposta:
    texto: str
    modo: str  # "gemini" ou "seguranca"
    ferramentas_usadas: list[str] = field(default_factory=list)
    aviso: str | None = None


def _para_conteudos(historico: list[dict]) -> list[dict]:
    """Converte {papel, texto} do cliente para o formato do Gemini (a seguir às últimas mensagens)."""
    papeis = {"utilizador": "user", "assistente": "model"}
    return [
        {"role": papeis[m["papel"]], "parts": [{"text": m["texto"]}]}
        for m in historico[-MAXIMO_DE_MENSAGENS_NO_HISTORICO:]
        if m.get("papel") in papeis and m.get("texto")
    ]


class ServicoDoAssistente:
    def __init__(self, cliente: ClienteGemini | None = None):
        self._cliente_fixo = cliente

    def _cliente(self) -> ClienteGemini | None:
        if self._cliente_fixo is not None:
            return self._cliente_fixo
        chave, modelo = ler("GEMINI_API_KEY"), ler("GEMINI_MODEL")
        return ClienteGemini(chave, modelo) if chave and modelo else None

    @property
    def gemini_configurado(self) -> bool:
        return self._cliente_fixo is not None or bool(ler("GEMINI_API_KEY") and ler("GEMINI_MODEL"))

    def _com_gemini(self, ligacao: psycopg.Connection, pedido: str, historico: list[dict]) -> Resposta | str:
        """A resposta do Gemini, ou o texto do aviso a mostrar se não foi possível."""
        cliente = self._cliente()
        if cliente is None:
            return "O Gemini não está configurado (faltam GEMINI_API_KEY e GEMINI_MODEL em backend/.env)."
        try:
            r = cliente.conversar(
                pedido,
                [f.declaracao() for f in ferramentas.FERRAMENTAS],
                lambda nome, args: ferramentas.executar(ligacao, nome, args),
                _para_conteudos(historico),
            )
        except ErroDoAssistente as erro:
            return str(erro)
        return Resposta(r.texto, "gemini", r.ferramentas_usadas)

    def perguntar(self, ligacao: psycopg.Connection, pergunta: str, historico: list[dict] | None = None) -> Resposta:
        resultado = self._com_gemini(ligacao, pergunta, historico or [])
        if isinstance(resultado, Resposta):
            return resultado
        texto, usadas = seguranca.responder(ligacao, pergunta)
        return Resposta(texto, "seguranca", usadas, f"{resultado} A responder em modo de segurança (sem modelo de linguagem).")

    def relatorio(self, ligacao: psycopg.Connection) -> Resposta:
        resultado = self._com_gemini(ligacao, PEDIDO_DO_RELATORIO, [])
        if isinstance(resultado, Resposta):
            return resultado
        texto, usadas = seguranca.relatorio(ligacao)
        return Resposta(texto, "seguranca", usadas, f"{resultado} Relatório em modo de segurança (sem modelo de linguagem).")
