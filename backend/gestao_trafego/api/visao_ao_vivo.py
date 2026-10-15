"""Visão ao vivo por WebSocket: o browser reproduz o vídeo e este servidor envia-lhe o que o algoritmo vê.

O cliente liga-se a `/ws/visao?video=<ficheiro>.webm` e recebe `a_preparar`, `pronto` (com a resolução e a
linha de contagem), várias vezes por segundo `deteccoes`, e por fim `fim` (com o resumo) ou `erro`.

Comandos do cliente (JSON): {"accao": "iniciar", "t": 0}, {"accao": "sincronizar", "t": <segundo do vídeo>},
{"accao": "pausar"}, {"accao": "retomar", "t": <segundo>}, {"accao": "parar"}.
"""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from gestao_trafego.api.rotas_visao import resolver_video
from gestao_trafego.visao.sessao_ao_vivo import SessaoDeVisaoAoVivo

router = APIRouter()

TAMANHOS_DE_IMAGEM = (320, 416, 480, 640, 960)


def _ler_linha(texto: str) -> tuple[float, float, float, float]:
    valores = [float(v) for v in texto.split(",")]
    if len(valores) != 4 or any(not 0 <= v <= 1 for v in valores):
        raise ValueError("A linha são 4 números entre 0 e 1: x1,y1,x2,y2.")
    return valores[0], valores[1], valores[2], valores[3]


async def _receber_comandos(ws: WebSocket, sessao: SessaoDeVisaoAoVivo) -> None:
    try:
        while True:
            mensagem = await ws.receive_json()
            accao, t = mensagem.get("accao"), float(mensagem.get("t", 0) or 0)
            if accao == "iniciar":
                sessao.iniciar(t)
            elif accao == "sincronizar":
                sessao.sincronizar(t)
            elif accao == "pausar":
                sessao.pausar()
            elif accao == "retomar":
                sessao.retomar(t)
            elif accao == "parar":
                return
    except (WebSocketDisconnect, RuntimeError):
        return


@router.websocket("/ws/visao")
async def visao_ao_vivo(ws: WebSocket, video: str, segundos: float | None = None, imgsz: int = 480, linha: str = "0,0.7,1,0.7") -> None:
    await ws.accept()
    ficheiro = resolver_video(video)
    try:
        if ficheiro is None:
            raise ValueError(f"Não existe o vídeo {video!r}.")
        if imgsz not in TAMANHOS_DE_IMAGEM:
            raise ValueError(f"Tamanho de imagem inválido: use um de {TAMANHOS_DE_IMAGEM}.")
        if segundos is not None and segundos <= 0:
            raise ValueError("`segundos` tem de ser positivo.")
        fila: asyncio.Queue[dict] = asyncio.Queue()
        ciclo = asyncio.get_running_loop()
        sessao = SessaoDeVisaoAoVivo(
            ficheiro, lambda m: ciclo.call_soon_threadsafe(fila.put_nowait, m),
            linha=_ler_linha(linha), tamanho_imagem=imgsz, max_segundos=segundos,
        )
    except ValueError as erro:
        await ws.send_json({"tipo": "erro", "mensagem": str(erro)})
        await ws.close()
        return

    comandos = None
    try:
        await ws.send_json({"tipo": "a_preparar"})
        # carregar o modelo e fazer a primeira análise demora (segundos): em thread, para o servidor não parar
        informacao = await asyncio.to_thread(sessao.abrir)
        await ws.send_json({"tipo": "pronto", **informacao})
        comandos = asyncio.create_task(_receber_comandos(ws, sessao))
        while not comandos.done():
            try:
                mensagem = await asyncio.wait_for(fila.get(), timeout=0.25)
            except TimeoutError:
                continue
            await ws.send_json(mensagem)
            if mensagem["tipo"] in ("fim", "erro"):
                break
    except WebSocketDisconnect:
        pass
    except Exception as erro:  # noqa: BLE001 — o cliente tem de saber porque parou
        try:
            await ws.send_json({"tipo": "erro", "mensagem": f"Não foi possível preparar a análise: {erro}"})
        except Exception:  # noqa: BLE001 — já se perdeu a ligação
            pass
    finally:
        if comandos is not None:
            comandos.cancel()
        await asyncio.to_thread(sessao.parar)
        try:
            await ws.close()
        except Exception:  # noqa: BLE001 — já estava fechada
            pass
