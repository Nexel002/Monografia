"""Estimativa da fila e agregação das contagens por janela de tempo.

Lógica pura. A fila é o número de veículos parados na zona a montante da linha de contagem: é o que
o Max-Pressure usa (`LeituraDeFaixa.parados`), por isso a câmara tem de o poder fornecer.
"""

from dataclasses import dataclass, field

from gestao_trafego.comum.tipos import ContagemPorVia
from gestao_trafego.visao.contagem import Deteccao, Passagem

Zona = tuple[float, float, float, float]  # x1, y1, x2, y2 em píxeis


@dataclass
class EstimadorDeFila:
    zona: Zona
    # Um veículo está «parado» se se mexeu menos do que esta fracção da sua própria altura por
    # fotograma. Em fracção da altura (e não em píxeis) para valer para carros perto e longe.
    limiar_alturas_por_fotograma: float = 0.004
    _ultimo: dict[int, tuple[int, float, float]] = field(default_factory=dict)  # id -> (fotograma, x, y)

    def _na_zona(self, ponto: tuple[float, float]) -> bool:
        x1, y1, x2, y2 = self.zona
        return x1 <= ponto[0] <= x2 and y1 <= ponto[1] <= y2

    def actualizar(self, fotograma: int, deteccoes: list[Deteccao]) -> int:
        """Devolve quantos veículos estão parados dentro da zona neste fotograma."""
        parados = 0
        for d in deteccoes:
            x, y = d.caixa.base
            anterior = self._ultimo.get(d.id_veiculo)
            self._ultimo[d.id_veiculo] = (fotograma, x, y)
            # Sem posição anterior não há velocidade: não se pode dizer que está parado.
            if anterior is None or fotograma <= anterior[0] or not self._na_zona((x, y)):
                continue
            altura = d.caixa.y2 - d.caixa.y1
            deslocamento = ((x - anterior[1]) ** 2 + (y - anterior[2]) ** 2) ** 0.5
            if altura > 0 and deslocamento / (altura * (fotograma - anterior[0])) < self.limiar_alturas_por_fotograma:
                parados += 1
        return parados


def agregar_por_janela(
    via: str,
    passagens: list[Passagem],
    filas: list[tuple[int, int]],  # (fotograma, veículos parados)
    fps: float,
    duracao_s: float,
    janela_s: float = 10.0,
) -> list[ContagemPorVia]:
    """Corta a contagem em janelas de `janela_s` segundos (a última pode ser mais curta)."""
    if janela_s <= 0 or fps <= 0:
        raise ValueError("janela e fps têm de ser positivos.")
    contagens = []
    inicio = 0.0
    while inicio < duracao_s:
        fim = min(inicio + janela_s, duracao_s)
        por_tipo: dict[str, int] = {}
        for p in passagens:
            if inicio <= p.fotograma / fps < fim:
                por_tipo[p.tipo] = por_tipo.get(p.tipo, 0) + 1
        filas_da_janela = [n for f, n in filas if inicio <= f / fps < fim]
        fila_media = sum(filas_da_janela) / len(filas_da_janela) if filas_da_janela else 0.0
        contagens.append(ContagemPorVia(via, inicio, fim, por_tipo, fila_media))
        inicio = fim
    return contagens
