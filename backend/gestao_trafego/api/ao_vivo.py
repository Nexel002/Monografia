"""Simulação ao vivo por WebSocket: duas simulações lado a lado, com a mesma procura.

O cliente liga-se a `/ws/simulacao` e recebe, várias vezes por segundo, o estado das duas (veículos,
semáforos, indicadores). A comparação é justa porque as duas usam a mesma semente: entram os mesmos
veículos, à mesma hora; só muda quem controla os semáforos.

Mensagens do servidor: `inicio`, `estado` (repetida), `fim`. Do cliente (JSON):
    {"accao": "velocidade", "valor": 20}   segundos simulados por segundo real
    {"accao": "pausa"} / {"accao": "retomar"}
"""

import asyncio
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from gestao_trafego.dados.repositorio import CONFIGURACOES
from gestao_trafego.simulacao.sessao import Instantaneo, SessaoDeSimulacao

router = APIRouter()

_TIPOS = {"carro": 0, "chapa": 1, "mota": 2, "camiao": 3, "avariado": 4}
INTERVALO_ENTRE_MENSAGENS_S = 0.15
MAXIMO_DE_PASSOS_POR_MENSAGEM = 60  # se o computador não acompanhar, atrasa em vez de acumular dívida
VELOCIDADE_MAXIMA = 60.0
LIMITE_POR_OMISSAO_S = 4500


def _parametros_da_configuracao(nome: str) -> tuple[str, bool]:
    if nome not in CONFIGURACOES:
        raise ValueError(f"Configuração desconhecida: {nome!r} (existem: {', '.join(CONFIGURACOES)}).")
    cenario, _, vias = nome.partition("+")
    return cenario, bool(vias)


def _estado_para_json(i: Instantaneo) -> dict:
    return {
        # [x, y, ângulo, tipo, parado]: arrays em vez de objectos para a mensagem ficar pequena
        "v": [[round(v.x, 1), round(v.y, 1), round(v.angulo), _TIPOS.get(v.tipo, 0), int(v.parado)] for v in i.veiculos.values()],
        "s": i.semaforos,
        "k": {
            "na_rede": i.na_rede,
            "parados": i.parados,
            "velocidade_media_ms": round(i.velocidade_media_ms, 2),
            "chegados": i.chegados,
            "espera_media_s": round(i.espera_media_dos_chegados_s, 1),
        },
    }


def _avancar(sessoes: dict[str, SessaoDeSimulacao], passos: int) -> dict:
    """Corre em thread (bloqueia no SUMO). Avança as duas sessões o mesmo número de passos."""
    for sessao in sessoes.values():
        for _ in range(passos):
            if sessao.terminou():
                break
            sessao.passo()
    estados = {lado: _estado_para_json(s.instantaneo()) for lado, s in sessoes.items()}
    return {"tipo": "estado", "t": max(s.tempo_s for s in sessoes.values()), **estados}


async def _receber_comandos(ws: WebSocket, controlo: dict) -> None:
    try:
        while True:
            mensagem = await ws.receive_json()
            accao = mensagem.get("accao")
            if accao == "pausa":
                controlo["pausado"] = True
            elif accao == "retomar":
                controlo["pausado"] = False
            elif accao == "velocidade":
                controlo["velocidade"] = min(max(float(mensagem.get("valor", 1)), 0.5), VELOCIDADE_MAXIMA)
    except (WebSocketDisconnect, RuntimeError):
        controlo["ligado"] = False


@router.websocket("/ws/simulacao")
async def simulacao_ao_vivo(
    ws: WebSocket,
    semente: int = 42,
    velocidade: float = 10.0,
    incidente: bool = True,
    esquerda: str = "fixo",
    direita: str = "coordenado+vias",
    escala: float = 1.0,
    limite: int = LIMITE_POR_OMISSAO_S,
) -> None:
    await ws.accept()
    try:
        configuracoes = {"esquerda": esquerda, "direita": direita}
        sessoes = {}
        for lado, nome in configuracoes.items():
            cenario, vias = _parametros_da_configuracao(nome)
            sessoes[lado] = SessaoDeSimulacao(cenario, semente, escala, incidente, vias, observar=True)
    except ValueError as erro:
        await ws.send_json({"tipo": "erro", "mensagem": str(erro)})
        await ws.close()
        return

    controlo = {"velocidade": min(max(velocidade, 0.5), VELOCIDADE_MAXIMA), "pausado": False, "ligado": True}
    receptor = asyncio.create_task(_receber_comandos(ws, controlo))
    try:
        for sessao in sessoes.values():
            await asyncio.to_thread(sessao.abrir)
        await ws.send_json({"tipo": "inicio", "configuracoes": configuracoes, "semente": semente, "incidente": incidente})

        dever_s, ultimo = 0.0, time.perf_counter()
        while controlo["ligado"]:
            agora = time.perf_counter()
            if not controlo["pausado"]:
                dever_s += (agora - ultimo) * controlo["velocidade"]
            ultimo = agora
            passos = min(int(dever_s), MAXIMO_DE_PASSOS_POR_MENSAGEM)
            dever_s = 0.0 if passos == MAXIMO_DE_PASSOS_POR_MENSAGEM else dever_s - passos
            if passos:
                mensagem = await asyncio.to_thread(_avancar, sessoes, passos)
                await ws.send_json(mensagem)
                if all(s.terminou() for s in sessoes.values()) or mensagem["t"] >= limite:
                    await ws.send_json({"tipo": "fim", "t": mensagem["t"]})
                    break
            await asyncio.sleep(INTERVALO_ENTRE_MENSAGENS_S)
    except WebSocketDisconnect:
        pass
    finally:
        receptor.cancel()
        for sessao in sessoes.values():
            await asyncio.to_thread(sessao.fechar)
