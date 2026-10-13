"""Contagem ao vivo: o vídeo corre à velocidade real e o detector analisa em paralelo.

Em CPU o YOLO analisa poucos fotogramas por segundo. Em vez de abrandar o vídeo, há duas linhas de
trabalho: a principal mostra o vídeo ao ritmo certo (saltando fotogramas se o computador não chegar) e
um analisador numa thread pega sempre no fotograma MAIS RECENTE, deteta, segue e conta. A imagem
mostra as últimas deteções com as caixas deslocadas à velocidade dos veículos (`extrapolar.py`).

Compromisso a conhecer: o detector vê só uma parte dos fotogramas, por isso a contagem ao vivo pode
diferir um pouco da contagem fotograma-a-fotograma (`contar.py`), que é a de referência.
"""

import json
import threading
import time
from pathlib import Path

import cv2

from gestao_trafego.visao.anotar import desenhar
from gestao_trafego.visao.analisador import Analisador
from gestao_trafego.visao.contagem import ContadorDeLinha
from gestao_trafego.visao.detector import SeguidorDeVeiculos
from gestao_trafego.visao.extrapolar import ExtrapoladorDeCaixas

JANELA = "Contagem de veículos (ao vivo)"
# Largura a que o vídeo é reduzido antes de ser analisado e desenhado. A 1080p, só desenhar e mostrar
# cada fotograma gastava tanto CPU que o detector, que partilha os 4 núcleos, caía de 6 para 1 análise
# por segundo (medido em 12/10/2026) e a contagem ficava a metade.
LARGURA_DE_TRABALHO = 960


def executar_ao_vivo(
    video: Path,
    linha: tuple[float, float, float, float],
    saida: Path,
    modelo: str = "yolov8n.pt",
    tamanho_imagem: int = 480,
    max_segundos: float | None = None,
) -> dict:
    captura = cv2.VideoCapture(str(video))
    largura = int(captura.get(cv2.CAP_PROP_FRAME_WIDTH))
    altura = int(captura.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = captura.get(cv2.CAP_PROP_FPS) or 30.0
    if not captura.isOpened() or largura <= 0 or altura <= 0:  # o OpenCV 5 devolve -1 (não 0) quando o ficheiro não abre
        raise FileNotFoundError(f"Não foi possível abrir o vídeo: {video}")

    escala = min(1.0, LARGURA_DE_TRABALHO / largura)
    largura, altura = int(largura * escala), int(altura * escala)  # a partir daqui tudo está à resolução de trabalho
    contador = ContadorDeLinha((linha[0] * largura, linha[1] * altura), (linha[2] * largura, linha[3] * altura))
    extrapolador = ExtrapoladorDeCaixas()
    bloqueio = threading.Lock()
    print("A carregar e a aquecer o modelo (a primeira análise é lenta)...", flush=True)
    seguidor = SeguidorDeVeiculos(modelo, tamanho_imagem=tamanho_imagem)
    ok, primeira = captura.read()
    if ok:
        seguidor.aquecer(cv2.resize(primeira, (largura, altura), interpolation=cv2.INTER_AREA) if escala < 1.0 else primeira)
        captura.set(cv2.CAP_PROP_POS_FRAMES, 0)  # o vídeo recomeça do princípio: o relógio só arranca depois do aquecimento
    analisador = Analisador(seguidor, contador, bloqueio, extrapolador.actualizar)
    analisador.start()

    cv2.namedWindow(JANELA, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(JANELA, 1100, 620)
    indice = -1
    fotogramas_mostrados = 0
    inicio = time.perf_counter()
    try:
        while analisador.erro is None:
            devido = int((time.perf_counter() - inicio) * fps)
            # Atrasado em relação ao relógio: salta fotogramas (grab é barato) em vez de ficar em câmara lenta.
            while indice < devido - 1:
                if not captura.grab():
                    devido = -1
                    break
                indice += 1
            if devido == -1:
                break
            ok, imagem = captura.read()
            if not ok:
                break
            indice += 1
            if max_segundos and indice / fps >= max_segundos:
                break
            if escala < 1.0:
                imagem = cv2.resize(imagem, (largura, altura), interpolation=cv2.INTER_AREA)
            analisador.submeter(indice, imagem)

            with bloqueio:
                quadro = desenhar(imagem, extrapolador.prever(indice), contador)
            fotogramas_mostrados += 1
            decorrido = time.perf_counter() - inicio
            analises_por_s = analisador.analisados / decorrido if decorrido else 0.0
            cv2.putText(
                quadro, f"video {fotogramas_mostrados / decorrido:.0f} fps | deteccao {analises_por_s:.1f} analises/s | q sair, espaco pausa",
                (20, altura - 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA,
            )
            cv2.imshow(JANELA, quadro)

            espera_ms = int(((indice + 1) / fps - (time.perf_counter() - inicio)) * 1000)
            tecla = cv2.waitKey(max(1, espera_ms)) & 0xFF
            if tecla == ord("q"):
                break
            if tecla == ord(" "):
                pausa = time.perf_counter()
                cv2.waitKey(0)
                inicio += time.perf_counter() - pausa  # o tempo parado não conta para o relógio do vídeo
    finally:
        analisador.parar()
        analisador.join(timeout=30)
        captura.release()
        cv2.destroyAllWindows()
    if analisador.erro is not None:
        raise analisador.erro

    duracao = time.perf_counter() - inicio
    resumo = {
        "modo": "ao_vivo",
        "video": video.name,
        "modelo": modelo,
        "tamanho_imagem": tamanho_imagem,
        "resolucao_de_trabalho": [largura, altura],
        "linha": list(linha),
        "fotogramas_mostrados": fotogramas_mostrados,
        "fotogramas_analisados": analisador.analisados,
        "analises_por_segundo": analisador.analisados / duracao if duracao else 0.0,
        "latencia_media_da_analise_ms": 1000 * analisador.tempo_de_analise_s / analisador.analisados if analisador.analisados else 0.0,
        "total": contador.total(),
        "por_tipo": contador.por_tipo(),
        "por_sentido": contador.por_sentido(),
    }
    saida.mkdir(parents=True, exist_ok=True)
    (saida / "contagem_ao_vivo.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    return resumo
