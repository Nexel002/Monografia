"""Contagem de veículos por linha virtual.

Lógica pura: recebe caixas já seguidas (cada veículo com um identificador estável) e conta quando o
ponto de contagem de um veículo cruza a linha. Não importa `cv2` nem `ultralytics`, por isso testa-se
sem vídeo nem modelo.

Origem: a ideia vem do tutorial de ANPR com YOLOv8 (deteção COCO + seguimento com identificadores),
a que se junta a linha de contagem. O autor do tutorial notou que o ponto de contagem deve ser a
base da caixa e não o centro: num vídeo de câmara baixa, os carros da frente tapam os de trás e o
centro da caixa fica coberto ou salta de posição; a base (onde o carro toca o asfalto) é estável.
"""

from dataclasses import dataclass, field

Ponto = tuple[float, float]

SENTIDO_IDA = "ida"  # o ponto passa do lado positivo da linha para o negativo
SENTIDO_VOLTA = "volta"


@dataclass(frozen=True)
class Caixa:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def base(self) -> Ponto:
        """Centro da aresta de baixo: onde o veículo toca o asfalto."""
        return ((self.x1 + self.x2) / 2, self.y2)

    @property
    def centro(self) -> Ponto:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)


@dataclass(frozen=True)
class Deteccao:
    id_veiculo: int  # identificador atribuído pelo seguimento; estável entre fotogramas
    caixa: Caixa
    tipo: str  # carro, mota, autocarro, camiao
    confianca: float = 1.0


@dataclass(frozen=True)
class Passagem:
    id_veiculo: int
    tipo: str
    sentido: str
    fotograma: int


def _lado(a: Ponto, b: Ponto, p: Ponto) -> float:
    """Positivo de um lado da recta a-b, negativo do outro, zero em cima dela."""
    return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])


@dataclass
class ContadorDeLinha:
    """Conta cada veículo uma só vez, quando o seu ponto de contagem atravessa o segmento a-b."""

    a: Ponto
    b: Ponto
    ponto: str = "base"  # "base" (recomendado) ou "centro"
    passagens: list[Passagem] = field(default_factory=list)
    _ultimo_ponto: dict[int, Ponto] = field(default_factory=dict)
    _contados: set[int] = field(default_factory=set)

    def __post_init__(self) -> None:
        if self.ponto not in ("base", "centro"):
            raise ValueError(f"ponto de contagem inválido: {self.ponto!r}")
        if self.a == self.b:
            raise ValueError("a linha de contagem tem de ter comprimento.")

    def foi_contado(self, id_veiculo: int) -> bool:
        return id_veiculo in self._contados

    def actualizar(self, fotograma: int, deteccoes: list[Deteccao]) -> list[Passagem]:
        """Processa um fotograma e devolve as passagens novas."""
        novas = []
        for d in deteccoes:
            actual = d.caixa.base if self.ponto == "base" else d.caixa.centro
            anterior = self._ultimo_ponto.get(d.id_veiculo)
            self._ultimo_ponto[d.id_veiculo] = actual
            # Sem posição anterior não há movimento: um veículo que aparece já do outro lado da linha
            # não atravessou nada. Contá-lo seria inventar uma passagem.
            if anterior is None or d.id_veiculo in self._contados:
                continue
            sentido = self._atravessou(anterior, actual)
            if sentido:
                passagem = Passagem(d.id_veiculo, d.tipo, sentido, fotograma)
                self._contados.add(d.id_veiculo)
                self.passagens.append(passagem)
                novas.append(passagem)
        return novas

    def _atravessou(self, anterior: Ponto, actual: Ponto) -> str | None:
        antes, depois = _lado(self.a, self.b, anterior), _lado(self.a, self.b, actual)
        if antes == 0 or depois == 0 or (antes > 0) == (depois > 0):
            return None
        # O movimento cruza a RECTA; falta saber se cruza o SEGMENTO (e não passa para lá das pontas).
        a_lado, b_lado = _lado(anterior, actual, self.a), _lado(anterior, actual, self.b)
        if (a_lado > 0) == (b_lado > 0):
            return None
        return SENTIDO_IDA if antes > 0 else SENTIDO_VOLTA

    def total(self) -> int:
        return len(self.passagens)

    def por_tipo(self) -> dict[str, int]:
        contagem: dict[str, int] = {}
        for p in self.passagens:
            contagem[p.tipo] = contagem.get(p.tipo, 0) + 1
        return contagem

    def por_sentido(self) -> dict[str, int]:
        contagem = {SENTIDO_IDA: 0, SENTIDO_VOLTA: 0}
        for p in self.passagens:
            contagem[p.sentido] += 1
        return contagem
