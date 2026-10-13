"""Analisador numa thread: detecta, segue e conta sempre o fotograma MAIS RECENTE.

Em CPU o YOLO analisa poucos fotogramas por segundo. Quem mostra o vídeo (a janela do OpenCV ou o
browser) não pode esperar por ele: entrega fotogramas ao analisador e continua. O analisador guarda
uma só vaga, por isso um fotograma novo substitui o que ainda não foi analisado (analisar fotogramas
velhos só aumentava o atraso das caixas). Partilhado pelo modo de janela (`ao_vivo.py`) e pelo do
dashboard (`sessao_ao_vivo.py`).
"""

import threading
import time
from collections.abc import Callable

from gestao_trafego.visao.contagem import ContadorDeLinha, Deteccao
from gestao_trafego.visao.detector import SeguidorDeVeiculos


class Analisador(threading.Thread):
    def __init__(
        self,
        seguidor: SeguidorDeVeiculos,
        contador: ContadorDeLinha,
        bloqueio: threading.Lock,
        ao_resultado: Callable[[int, list[Deteccao]], None],
    ):
        """`ao_resultado(indice, deteccoes)` corre na thread do analisador, com `bloqueio` tomado, logo
        depois de a contagem ser actualizada: é onde se actualiza o que o resto do sistema mostra."""
        super().__init__(daemon=True)
        self._seguidor, self._contador, self._bloqueio, self._ao_resultado = seguidor, contador, bloqueio, ao_resultado
        self._pedido: tuple[int, object] | None = None
        self._condicao = threading.Condition()
        self._a_correr = True
        self.analisados = 0
        self.tempo_de_analise_s = 0.0
        self.erro: BaseException | None = None

    def submeter(self, indice: int, imagem) -> None:
        with self._condicao:
            self._pedido = (indice, imagem)
            self._condicao.notify()

    def parar(self) -> None:
        with self._condicao:
            self._a_correr = False
            self._condicao.notify()

    def run(self) -> None:
        try:
            while True:
                with self._condicao:
                    while self._pedido is None and self._a_correr:
                        self._condicao.wait()
                    if not self._a_correr:
                        return
                    indice, imagem = self._pedido
                    self._pedido = None
                inicio = time.perf_counter()
                deteccoes = self._seguidor.seguir(imagem)
                self.tempo_de_analise_s += time.perf_counter() - inicio
                with self._bloqueio:
                    self._contador.actualizar(indice, deteccoes)
                    self._ao_resultado(indice, deteccoes)
                self.analisados += 1
        except BaseException as erro:  # noqa: BLE001 — guarda-se para quem controla a thread o relançar
            self.erro = erro
