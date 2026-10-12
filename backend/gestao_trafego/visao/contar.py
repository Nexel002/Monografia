"""Conta veículos num vídeo e escreve o vídeo anotado e o resumo das contagens.

Uso (a partir de backend/):
    uv run python -m gestao_trafego.visao.contar --video ../dados/videos/ficheiro.mp4
    uv run python -m gestao_trafego.visao.contar --video ../dados/videos/ficheiro.mp4 --ao-vivo

Sem `--ao-vivo` analisa todos os fotogramas (referência de precisão, lento em CPU). Com `--ao-vivo`
mostra o vídeo à velocidade real e analisa em paralelo (ver `ao_vivo.py`).

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
from gestao_trafego.visao.fila import EstimadorDeFila, agregar_por_janela

RAIZ = Path(__file__).resolve().parents[3]
PASTA_RESULTADOS = RAIZ / "dados" / "resultados"


def _ler_linha(texto: str) -> tuple[float, float, float, float]:
    valores = [float(v) for v in texto.split(",")]
    if len(valores) != 4 or any(not 0 <= v <= 1 for v in valores):
        raise argparse.ArgumentTypeError("a linha são 4 números entre 0 e 1: x1,y1,x2,y2")
    return tuple(valores)  # type: ignore[return-value]


def _zona_por_omissao(linha: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    """Faixa de imagem a montante de uma linha horizontal: 40 % da altura acima dela."""
    topo = min(linha[1], linha[3])
    return (0.0, max(0.0, topo - 0.4), 1.0, topo)


def contar_video(
    video: Path,
    linha: tuple[float, float, float, float],
    saida: Path,
    modelo: str = "yolov8n.pt",
    guardar_video: bool = True,
    max_fotogramas: int | None = None,
    tamanho_imagem: int = 960,
    janela_s: float = 10.0,
    zona: tuple[float, float, float, float] | None = None,
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
    zona = zona or _zona_por_omissao(linha)
    estimador = EstimadorDeFila((zona[0] * largura, zona[1] * altura, zona[2] * largura, zona[3] * altura))
    filas: list[tuple[int, int]] = []
    saida.mkdir(parents=True, exist_ok=True)
    escritor = (
        cv2.VideoWriter(str(saida / "anotado.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), fps, (largura, altura))
        if guardar_video
        else None
    )

    inicio = time.perf_counter()
    processados = 0
    try:
        for fotograma in seguir_veiculos(video, modelo, tamanho_imagem=tamanho_imagem):
            contador.actualizar(fotograma.indice, fotograma.deteccoes)
            filas.append((fotograma.indice, estimador.actualizar(fotograma.indice, fotograma.deteccoes)))
            if escritor:
                escritor.write(desenhar(fotograma.imagem, fotograma.deteccoes, contador))
            processados += 1
            if max_fotogramas and processados >= max_fotogramas:
                break
    finally:
        if escritor:
            escritor.release()
    decorrido = time.perf_counter() - inicio

    janelas = agregar_por_janela("via_principal", contador.passagens, filas, fps, processados / fps, janela_s)
    resumo = {
        "modo": "fotograma_a_fotograma",
        "video": video.name,
        "resolucao": [largura, altura],
        "fps_do_video": fps,
        "fotogramas_processados": processados,
        "fotogramas_do_video": total_fotogramas,
        "duracao_processada_s": processados / fps,
        "fps_de_processamento": processados / decorrido if decorrido else 0.0,
        "modelo": modelo,
        "tamanho_imagem": tamanho_imagem,
        "linha": list(linha),
        "total": contador.total(),
        "por_tipo": contador.por_tipo(),
        "por_sentido": contador.por_sentido(),
        "janelas": [
            {"via": j.via, "inicio_s": j.inicio_s, "fim_s": j.fim_s, "por_tipo": j.por_tipo, "total": j.total,
             "fluxo_veiculos_por_hora": j.fluxo_veiculos_por_hora, "fila_media_veiculos": j.fila_media_veiculos}
            for j in janelas
        ],
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
    parser.add_argument("--janela", type=float, default=10.0, help="duração, em segundos, de cada janela de contagem")
    parser.add_argument("--zona", type=_ler_linha, default=None, help="zona da fila x1,y1,x2,y2 em fracções (por omissão, a montante da linha)")
    parser.add_argument("--ao-vivo", action="store_true", help="janela com o vídeo à velocidade real (q sai, espaço pausa)")
    parser.add_argument("--imgsz", type=int, default=None, help="tamanho da imagem para o YOLO (960 offline, 480 ao vivo)")
    argumentos = parser.parse_args()
    saida = argumentos.saida or PASTA_RESULTADOS / f"visao_{argumentos.video.stem}"
    if argumentos.ao_vivo:
        from gestao_trafego.visao.ao_vivo import executar_ao_vivo

        resumo = executar_ao_vivo(argumentos.video, argumentos.linha, saida, argumentos.modelo, argumentos.imgsz or 480)
    else:
        resumo = contar_video(
            argumentos.video, argumentos.linha, saida, argumentos.modelo, not argumentos.sem_video,
            argumentos.max_fotogramas, argumentos.imgsz or 960, argumentos.janela, argumentos.zona,
        )
        resumo.pop("passagens")
    print(json.dumps(resumo, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
