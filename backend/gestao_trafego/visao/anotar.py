"""Desenho sobre o vídeo: caixas, linha de contagem e painel de totais.

Convenção de cores (a do autor do tutorial): verde = veículo já contado; amarelo = ainda por contar.
Se um veículo atravessa a linha e continua amarelo, a contagem falhou e vê-se logo no vídeo.
"""

import cv2
import numpy as np

from gestao_trafego.visao.contagem import ContadorDeLinha, Deteccao

VERDE = (0, 200, 0)
AMARELO = (0, 220, 255)
BRANCO = (255, 255, 255)
PRETO = (0, 0, 0)

ROTULOS_DOS_TIPOS = {"carro": "Carros", "mota": "Motas", "autocarro": "Autocarros", "camiao": "Camiões"}


def _cantos(imagem: np.ndarray, x1: int, y1: int, x2: int, y2: int, cor, espessura: int) -> None:
    """Só os quatro cantos da caixa: mais limpo do que um rectângulo inteiro com muitos veículos."""
    comprimento_x = max(8, (x2 - x1) // 4)
    comprimento_y = max(8, (y2 - y1) // 4)
    for x, y, dx, dy in ((x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)):
        cv2.line(imagem, (x, y), (x + dx * comprimento_x, y), cor, espessura)
        cv2.line(imagem, (x, y), (x, y + dy * comprimento_y), cor, espessura)


def desenhar(imagem: np.ndarray, deteccoes: list[Deteccao], contador: ContadorDeLinha) -> np.ndarray:
    quadro = imagem.copy()
    espessura = max(2, quadro.shape[1] // 600)

    a, b = (int(v) for v in contador.a), (int(v) for v in contador.b)
    cv2.line(quadro, tuple(a), tuple(b), BRANCO, espessura + 1)

    for d in deteccoes:
        cor = VERDE if contador.foi_contado(d.id_veiculo) else AMARELO
        c = d.caixa
        _cantos(quadro, int(c.x1), int(c.y1), int(c.x2), int(c.y2), cor, espessura + 1)
        cv2.circle(quadro, (int(c.base[0]), int(c.base[1])), espessura + 2, cor, -1)  # ponto de contagem
        cv2.putText(quadro, f"{d.tipo} #{d.id_veiculo}", (int(c.x1), int(c.y1) - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, cor, 1, cv2.LINE_AA)

    _painel(quadro, contador)
    return quadro


def _painel(quadro: np.ndarray, contador: ContadorDeLinha) -> None:
    por_tipo = contador.por_tipo()
    linhas = [f"Total contado: {contador.total()}"]
    linhas += [f"{rotulo}: {por_tipo.get(tipo, 0)}" for tipo, rotulo in ROTULOS_DOS_TIPOS.items()]
    sentidos = contador.por_sentido()
    linhas.append(f"Sentido ida/volta: {sentidos['ida']}/{sentidos['volta']}")

    # O painel escala com a largura do vídeo: com tamanho fixo ocupava metade de um vídeo de 640 px.
    escala = max(0.5, quadro.shape[1] / 1280)
    altura_linha = int(28 * escala)
    margem = int(10 * escala)
    cv2.rectangle(quadro, (margem, margem), (int(330 * escala), margem + int(10 * escala) + altura_linha * len(linhas)), PRETO, -1)
    for i, texto in enumerate(linhas):
        cv2.putText(quadro, texto, (2 * margem, int(38 * escala) + altura_linha * i), cv2.FONT_HERSHEY_SIMPLEX, 0.65 * escala,
                    BRANCO if i else VERDE, 2 if i == 0 and escala >= 1 else 1, cv2.LINE_AA)
