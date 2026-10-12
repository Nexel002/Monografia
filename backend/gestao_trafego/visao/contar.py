"""Conta veículos num vídeo e escreve o vídeo anotado e o resumo das contagens.

Uso (a partir de backend/):
    uv run python -m gestao_trafego.visao.contar --video ../dados/videos/ficheiro.mp4

A linha de contagem dá-se em fracções da imagem (0 a 1), e não em píxeis, para servir qualquer
resolução e qualquer local: `--linha 0,0.7,1,0.7` é uma linha horizontal a 70 % da altura.
"""

import argparse
import json
import time
from pathlib import Path

import cv2

from gestao_trafego.visao.anotar import desenhar
from gestao_trafego.visao.contagem import ContadorDeLinha
from gestao_trafego.visao.detector import seguir_veiculos

RAIZ = Path(__file__).resolve().parents[3]
PASTA_RESULTADOS = RAIZ / "dados" / "resultados"


def _ler_linha(texto: str) -> tuple[float, float, float, float]:
    valores = [float(v) for v in texto.split(",")]
    if len(valores) != 4 or any(not 0 <= v <= 1 for v in valores):
        raise argparse.ArgumentTypeError("a linha são 4 números entre 0 e 1: x1,y1,x2,y2")
    return tuple(valores)  # type: ignore[return-value]


def contar_video(
    video: Path,
    linha: tuple[float, float, float, float],
    saida: Path,
    modelo: str = "yolov8n.pt",
    guardar_video: bool = True,
    max_fotogramas: int | None = None,
) -> dict:
    captura = cv2.VideoCapture(str(video))
    largura = int(captura.get(cv2.CAP_PROP_FRAME_WIDTH))
    altura = int(captura.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = captura.get(cv2.CAP_PROP_FPS) or 30.0
    total_fotogramas = int(captura.get(cv2.CAP_PROP_FRAME_COUNT))
    captura.release()
    if not largura or not altura:
        raise FileNotFoundError(f"Não foi possível abrir o vídeo: {video}")

    contador = ContadorDeLinha(
        (linha[0] * largura, linha[1] * altura), (linha[2] * largura, linha[3] * altura), ponto="base"
    )
    saida.mkdir(parents=True, exist_ok=True)
    escritor = (
        cv2.VideoWriter(str(saida / "anotado.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps, (largura, altura))
        if guardar_video
        else None
    )

    inicio = time.perf_counter()
    processados = 0
    try:
        for fotograma in seguir_veiculos(video, modelo):
            contador.actualizar(fotograma.indice, fotograma.deteccoes)
            if escritor:
                escritor.write(desenhar(fotograma.imagem, fotograma.deteccoes, contador))
            processados += 1
            if max_fotogramas and processados >= max_fotogramas:
                break
    finally:
        if escritor:
            escritor.release()
    decorrido = time.perf_counter() - inicio

    resumo = {
        "video": video.name,
        "resolucao": [largura, altura],
        "fps_do_video": fps,
        "fotogramas_processados": processados,
        "fotogramas_do_video": total_fotogramas,
        "duracao_processada_s": processados / fps,
        "fps_de_processamento": processados / decorrido if decorrido else 0.0,
        "modelo": modelo,
        "linha": list(linha),
        "total": contador.total(),
        "por_tipo": contador.por_tipo(),
        "por_sentido": contador.por_sentido(),
        "passagens": [
            {"id": p.id_veiculo, "tipo": p.tipo, "sentido": p.sentido, "fotograma": p.fotograma,
             "tempo_s": p.fotograma / fps}
            for p in contador.passagens
        ],
    }
    (saida / "contagem.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    return resumo


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--linha", type=_ler_linha, default=(0.0, 0.7, 1.0, 0.7), help="x1,y1,x2,y2 em fracções")
    parser.add_argument("--saida", type=Path, default=None, help="pasta de saída (por omissão, dados/resultados/visao_<video>)")
    parser.add_argument("--modelo", default="yolov8n.pt")
    parser.add_argument("--sem-video", action="store_true", help="só conta, não escreve o vídeo anotado")
    parser.add_argument("--max-fotogramas", type=int, default=None)
    argumentos = parser.parse_args()
    saida = argumentos.saida or PASTA_RESULTADOS / f"visao_{argumentos.video.stem}"
    resumo = contar_video(
        argumentos.video, argumentos.linha, saida, argumentos.modelo, not argumentos.sem_video, argumentos.max_fotogramas
    )
    resumo.pop("passagens")
    print(json.dumps(resumo, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
