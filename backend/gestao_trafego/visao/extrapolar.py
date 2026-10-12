"""Posição estimada das caixas entre duas análises do detector.

No modo ao vivo o YOLO corre em CPU a poucos fotogramas por segundo, mas o vídeo é mostrado à
velocidade real. Entre duas análises as caixas ficariam paradas e depois «saltavam». Aqui, cada caixa
avança à velocidade que o veículo mostrou entre as duas últimas análises, o que as mantém coladas aos
carros. É só apresentação: a contagem usa sempre as posições reais do detector, nunca as estimadas.

Lógica pura, sem OpenCV.
"""

from gestao_trafego.visao.contagem import Caixa, Deteccao


class ExtrapoladorDeCaixas:
    def __init__(self, maximo_de_fotogramas: int = 15):
        # Passado este limite a estimativa já é palpite: melhor parar as caixas do que deixá-las fugir.
        self._maximo = maximo_de_fotogramas
        self._indice = 0
        self._deteccoes: list[Deteccao] = []
        self._centros: dict[int, tuple[int, float, float]] = {}  # id -> (fotograma, cx, cy)
        self._velocidades: dict[int, tuple[float, float]] = {}  # id -> píxeis por fotograma

    def actualizar(self, indice: int, deteccoes: list[Deteccao]) -> None:
        novos_centros, novas_velocidades = {}, {}
        for d in deteccoes:
            cx, cy = d.caixa.centro
            novos_centros[d.id_veiculo] = (indice, cx, cy)
            anterior = self._centros.get(d.id_veiculo)
            if anterior and indice > anterior[0]:
                dt = indice - anterior[0]
                v = ((cx - anterior[1]) / dt, (cy - anterior[2]) / dt)
                antiga = self._velocidades.get(d.id_veiculo)
                # Média com a velocidade anterior: uma só medição é ruidosa (a caixa do YOLO treme).
                novas_velocidades[d.id_veiculo] = (
                    ((v[0] + antiga[0]) / 2, (v[1] + antiga[1]) / 2) if antiga else v
                )
        self._indice, self._deteccoes = indice, list(deteccoes)
        self._centros, self._velocidades = novos_centros, novas_velocidades

    def prever(self, indice_actual: int) -> list[Deteccao]:
        passos = max(0, min(indice_actual - self._indice, self._maximo))
        previstas = []
        for d in self._deteccoes:
            vx, vy = self._velocidades.get(d.id_veiculo, (0.0, 0.0))
            dx, dy = vx * passos, vy * passos
            c = d.caixa
            previstas.append(Deteccao(d.id_veiculo, Caixa(c.x1 + dx, c.y1 + dy, c.x2 + dx, c.y2 + dy), d.tipo, d.confianca))
        return previstas
