"""Deteção e seguimento de veículos num vídeo com YOLOv8 + ByteTrack (ambos dentro do `ultralytics`).

Só aqui se importa o `ultralytics`: o resto do módulo de visão trabalha com `Deteccao` e testa-se
sem modelo. Usa-se o seguimento integrado em vez do SORT do tutorial original: é um módulo a menos
para descarregar à parte e não obriga a fixar versões antigas do numpy.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from ultralytics import YOLO

from gestao_trafego.visao.contagem import Caixa, Deteccao

# Classes do COCO que interessam ao trânsito. As restantes (pessoas, bicicletas, semáforos...) ficam fora.
CLASSES_DE_VEICULOS = {2: "carro", 3: "mota", 5: "autocarro", 7: "camiao"}


@dataclass(frozen=True)
class Fotograma:
    indice: int
    imagem: np.ndarray  # BGR, como o OpenCV a usa
    deteccoes: list[Deteccao]


def seguir_veiculos(
    video: Path,
    modelo: str = "yolov8n.pt",
    confianca: float = 0.3,
    tamanho_imagem: int = 960,
) -> Iterator[Fotograma]:
    """Percorre o vídeo e devolve, por fotograma, os veículos com identificador estável.

    `yolov8n` (a versão mais pequena) corre em CPU; `tamanho_imagem` acima do padrão (640) ajuda a
    ver veículos pequenos e distantes, ao custo de menos fotogramas por segundo.
    """
    detector = YOLO(modelo)
    resultados = detector.track(
        source=str(video),
        stream=True,
        persist=True,
        tracker="bytetrack.yaml",
        classes=list(CLASSES_DE_VEICULOS),
        conf=confianca,
        imgsz=tamanho_imagem,
        verbose=False,
    )
    for indice, resultado in enumerate(resultados):
        caixas = resultado.boxes
        deteccoes = []
        # Sem identificador (o seguimento ainda não confirmou o objecto) não se conta: contava-se
        # o mesmo veículo mais do que uma vez quando ganhasse identificador.
        if caixas is not None and caixas.id is not None:
            for xyxy, id_, conf, classe in zip(
                caixas.xyxy.tolist(), caixas.id.int().tolist(), caixas.conf.tolist(), caixas.cls.int().tolist()
            ):
                deteccoes.append(Deteccao(id_, Caixa(*xyxy), CLASSES_DE_VEICULOS[classe], conf))
        yield Fotograma(indice, resultado.orig_img, deteccoes)
