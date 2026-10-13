"""Contagem ao vivo para o dashboard: o vídeo corre no browser e o algoritmo corre aqui, ao mesmo ritmo.

O browser reproduz o vídeo original (fluido, 30 fotogramas por segundo) e desenha por cima as caixas
que este servidor lhe envia. O servidor lê o mesmo vídeo em tempo real, entrega ao analisador o
fotograma mais recente e emite, a cada análise, as caixas, os identificadores e os totais.

Para as duas pontas não se afastarem, o browser diz de vez em quando em que segundo do vídeo está
(`sincronizar`) e o servidor acerta o seu relógio por esse segundo, em vez de confiar em dois
relógios independentes.
"""

import threading
import time
from collections.abc import Callable
from pathlib import Path

import cv2

from gestao_trafego.visao.analisador import Analisador
from gestao_trafego.visao.contagem import ContadorDeLinha, Deteccao
from gestao_trafego.visao.detector import SeguidorDeVeiculos

# Largura a que se analisa o vídeo (ver `ao_vivo.py`): acima disto o detector perde análises por segundo.
LARGURA_DE_TRABALHO = 960


class SessaoDeVisaoAoVivo:
    def __init__(
        self,
        video: Path,
        emitir: Callable[[dict], None],
        linha: tuple[float, float, float, float] = (0.0, 0.7, 1.0, 0.7),
        modelo: str = "yolov8n.pt",
        tamanho_imagem: int = 480,
        max_segundos: float | None = None,
        seguidor=None,
    ):
        self._video, self._emitir, self._linha_fraccoes = video, emitir, linha
        self._modelo, self._tamanho_imagem, self._max_segundos = modelo, tamanho_imagem, max_segundos
        self._seguidor = seguidor  # injectável nos testes: o YOLO real demora a carregar
        self._captura: cv2.VideoCapture | None = None
        self._analisador: Analisador | None = None
        self._contador: ContadorDeLinha | None = None
        self._bloqueio = threading.Lock()
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None
        # estado do relógio, protegido por `_relogio`
        self._relogio = threading.Lock()
        self._a_correr = False
        self._ancora_s = 0.0
        self._ancora_indice = 0
        self._indice_lido = -1
        self.fps = 30.0
        self.fotogramas_lidos = 0
        self._inicio_s = 0.0

    # --- preparação ----------------------------------------------------------------------------

    def abrir(self) -> dict:
        """Abre o vídeo, carrega e aquece o modelo (lento na primeira vez) e devolve a informação para o cliente."""
        captura = cv2.VideoCapture(str(self._video))
        largura = int(captura.get(cv2.CAP_PROP_FRAME_WIDTH))
        altura = int(captura.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if not captura.isOpened() or largura <= 0 or altura <= 0:  # o OpenCV 5 devolve -1 (não 0) quando o ficheiro não abre
            raise FileNotFoundError(f"Não foi possível abrir o vídeo: {self._video}")
        self.fps = captura.get(cv2.CAP_PROP_FPS) or 30.0
        total = int(captura.get(cv2.CAP_PROP_FRAME_COUNT))
        self._escala = min(1.0, LARGURA_DE_TRABALHO / largura)
        self.largura, self.altura = int(largura * self._escala), int(altura * self._escala)
        self._total_de_fotogramas = total
        self._captura = captura

        x1, y1, x2, y2 = self._linha_fraccoes
        self.linha = (x1 * self.largura, y1 * self.altura, x2 * self.largura, y2 * self.altura)
        self._contador = ContadorDeLinha((self.linha[0], self.linha[1]), (self.linha[2], self.linha[3]))

        if self._seguidor is None:
            self._seguidor = SeguidorDeVeiculos(self._modelo, tamanho_imagem=self._tamanho_imagem)
        ok, primeira = captura.read()
        if ok and hasattr(self._seguidor, "aquecer"):
            self._seguidor.aquecer(self._reduzir(primeira))
        captura.set(cv2.CAP_PROP_POS_FRAMES, 0)

        self._analisador = Analisador(self._seguidor, self._contador, self._bloqueio, self._ao_resultado)
        duracao = total / self.fps if total else 0.0
        return {
            "largura": self.largura, "altura": self.altura, "fps": self.fps,
            "duracao_s": duracao, "ate_s": min(duracao, self._max_segundos) if self._max_segundos else duracao,
            "linha": list(self.linha), "modelo": self._modelo, "tamanho_imagem": self._tamanho_imagem,
        }

    def _reduzir(self, imagem):
        return cv2.resize(imagem, (self.largura, self.altura), interpolation=cv2.INTER_AREA) if self._escala < 1.0 else imagem

    # --- controlo ------------------------------------------------------------------------------

    def iniciar(self, t_s: float = 0.0) -> None:
        if self._thread is not None:
            self.retomar(t_s)
            return
        self._inicio_s = time.perf_counter()
        self._analisador.start()
        with self._relogio:
            self._a_correr, self._ancora_s, self._ancora_indice = True, time.perf_counter(), int(t_s * self.fps)
        self._thread = threading.Thread(target=self._ritmo, daemon=True)
        self._thread.start()

    def sincronizar(self, t_s: float) -> None:
        """O browser está no segundo `t_s` do vídeo: acerta-se o relógio do servidor por ele."""
        indice = int(t_s * self.fps)
        with self._relogio:
            self._ancora_s, self._ancora_indice = time.perf_counter(), indice
            if indice <= self._indice_lido and self._captura is not None:
                # O utilizador recuou o vídeo: volta a ler a partir daí (a contagem ignora quem já foi contado).
                self._captura.set(cv2.CAP_PROP_POS_FRAMES, indice)
                self._indice_lido = indice - 1

    def pausar(self) -> None:
        with self._relogio:
            self._a_correr = False

    def retomar(self, t_s: float) -> None:
        with self._relogio:
            self._a_correr, self._ancora_s, self._ancora_indice = True, time.perf_counter(), int(t_s * self.fps)

    def parar(self) -> None:
        self._parar.set()
        if self._analisador is not None:
            self._analisador.parar()
        if self._thread is not None:
            self._thread.join(timeout=5)
        if self._captura is not None:
            self._captura.release()

    # --- resultados ----------------------------------------------------------------------------

    def _resumo(self) -> dict:
        with self._bloqueio:
            c = self._contador
            analisados = self._analisador.analisados
            return {
                "total": c.total(), "por_tipo": c.por_tipo(), "por_sentido": c.por_sentido(),
                "analises": analisados, "fotogramas_lidos": self.fotogramas_lidos,
                "latencia_media_ms": 1000 * self._analisador.tempo_de_analise_s / analisados if analisados else 0.0,
            }

    def _ao_resultado(self, indice: int, deteccoes: list[Deteccao]) -> None:
        """Corre na thread do analisador, com o bloqueio tomado: monta a mensagem para o cliente."""
        c = self._contador
        decorrido = time.perf_counter() - self._inicio_s
        analisados = self._analisador.analisados + 1
        self._emitir(
            {
                "tipo": "deteccoes",
                "indice": indice,
                "t_video": indice / self.fps,
                # [id, x1, y1, x2, y2, tipo, contado] em píxeis da resolução de trabalho
                "veiculos": [
                    [d.id_veiculo, round(d.caixa.x1, 1), round(d.caixa.y1, 1), round(d.caixa.x2, 1), round(d.caixa.y2, 1),
                     d.tipo, int(c.foi_contado(d.id_veiculo))]
                    for d in deteccoes
                ],
                "totais": {"total": c.total(), "por_tipo": c.por_tipo(), "por_sentido": c.por_sentido()},
                "analises_por_s": analisados / decorrido if decorrido > 0 else 0.0,
                "latencia_media_ms": 1000 * (self._analisador.tempo_de_analise_s) / max(1, self._analisador.analisados),
            }
        )

    # --- ritmo ---------------------------------------------------------------------------------

    def _ritmo(self) -> None:
        """Lê o vídeo ao ritmo do relógio (saltando fotogramas se for preciso) e entrega o mais recente."""
        captura = self._captura
        try:
            while not self._parar.is_set():
                if self._analisador.erro is not None:
                    self._emitir({"tipo": "erro", "mensagem": f"O analisador falhou: {self._analisador.erro}"})
                    return
                with self._relogio:
                    a_correr, ancora_s, ancora_i = self._a_correr, self._ancora_s, self._ancora_indice
                    lido = self._indice_lido
                if not a_correr:
                    time.sleep(0.02)
                    continue
                devido = ancora_i + int((time.perf_counter() - ancora_s) * self.fps)
                fim_s = devido / self.fps
                if (self._max_segundos and fim_s >= self._max_segundos) or (self._total_de_fotogramas and devido >= self._total_de_fotogramas):
                    break
                if lido >= devido:
                    time.sleep(0.004)
                    continue
                while lido < devido - 1:  # atrasado: salta (grab não descodifica a imagem)
                    if not captura.grab():
                        break
                    lido += 1
                ok, imagem = captura.read()
                if not ok:
                    break
                lido += 1
                with self._relogio:
                    self._indice_lido = lido
                self.fotogramas_lidos += 1
                self._analisador.submeter(lido, self._reduzir(imagem))
            # Deixa o analisador terminar a análise em curso para o total final incluir o último fotograma.
            time.sleep(0.5)
            self._emitir({"tipo": "fim", "resumo": self._resumo()})
        except Exception as erro:  # noqa: BLE001 — o cliente tem de saber que parou
            self._emitir({"tipo": "erro", "mensagem": f"A leitura do vídeo falhou: {erro}"})
