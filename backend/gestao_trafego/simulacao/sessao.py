"""Uma simulação SUMO que se avança passo a passo.

`executar.py` usa-a para correr a simulação inteira e gravar métricas; a API usa-a para mostrar a
simulação ao vivo. Estar aqui, e não dentro de uma função de «correr tudo», é o que permite as duas
coisas sem duplicar a lógica de controlo.
"""

import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import sumo
import traci
import traci.constants as tc

from gestao_trafego.controlo.coordenador.anti_bloqueio import CoordenadorAntiBloqueio, ParametrosDoCoordenador
from gestao_trafego.controlo.local.max_pressure import ControladorLocal, ParametrosLocais
from gestao_trafego.simulacao.eventos import GestorDeIncidente, carregar_incidente
from gestao_trafego.simulacao.metricas import PREFIXO_VEICULO_DO_INCIDENTE, Amostra
from gestao_trafego.simulacao.ponte import PonteSumo
from gestao_trafego.simulacao.procura import gerar_ficheiro_de_procura
from gestao_trafego.simulacao.rotas_alternativas import RecomendadorDeRotas

# fixo = semáforos como hoje; local = Max-Pressure em cada cruzamento, sem coordenação entre nós;
# coordenado = local + camada 2 (coordenador anti-bloqueio).
CENARIOS = ("fixo", "local", "coordenado")

RAIZ = Path(__file__).resolve().parents[3]
REDE = RAIZ / "dados" / "cenarios" / "corredor_24_de_julho.net.xml"
CENARIO_PROCURA = RAIZ / "dados" / "cenarios" / "procura_hora_de_ponta.json"
CENARIO_INCIDENTE = RAIZ / "dados" / "cenarios" / "incidente_24_de_julho.json"

_VARIAVEIS_DO_VEICULO = [tc.VAR_POSITION, tc.VAR_ANGLE, tc.VAR_SPEED, tc.VAR_TYPE]
_LIMIAR_DE_PARADO_MS = 0.1  # o mesmo que o SUMO usa para o «tempo de espera»


@dataclass
class VeiculoVisto:
    x: float
    y: float
    angulo: float
    velocidade: float
    tipo: str

    @property
    def parado(self) -> bool:
        return self.velocidade < _LIMIAR_DE_PARADO_MS


@dataclass
class Instantaneo:
    """O que se vê num instante: veículos, estado de cada semáforo e indicadores até agora."""

    tempo_s: int
    veiculos: dict[str, VeiculoVisto]
    semaforos: dict[str, str]  # no -> estado de cada sinal (G/g verde, y amarelo, r vermelho)
    na_rede: int
    parados: int
    velocidade_media_ms: float
    chegados: int
    espera_media_dos_chegados_s: float


@dataclass
class SessaoDeSimulacao:
    cenario: str = "fixo"
    semente: int = 42
    escala: float = 1.0
    incidente: bool = False
    vias_alternativas: bool = False
    pasta: Path | None = None  # onde guardar o tripinfo (e a procura); sem pasta, não se grava tripinfo
    parametros_locais: ParametrosLocais | None = None
    parametros_coordenador: ParametrosDoCoordenador | None = None
    # Só a simulação ao vivo precisa de ver cada veículo a cada segundo; ligar isto nas corridas em
    # lote gastaria tempo à toa. Sem `observar`, `instantaneo()` não está disponível.
    observar: bool = False

    tempo_s: int = field(init=False, default=0)
    teleportes: int = field(init=False, default=0)
    colisoes: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        if self.cenario not in CENARIOS:
            raise ValueError(f"Cenário desconhecido: {self.cenario!r} (existem: {', '.join(CENARIOS)}).")
        self._ligacao = None
        self._ponte: PonteSumo | None = None
        self._temporario: tempfile.TemporaryDirectory | None = None
        self._controladores: dict[str, ControladorLocal] = {}
        self._coordenador: CoordenadorAntiBloqueio | None = None
        self._estados_aplicados: dict[str, str] = {}
        self._gestor_incidente: GestorDeIncidente | None = None
        self._recomendador: RecomendadorDeRotas | None = None
        self._veiculos: dict[str, VeiculoVisto] = {}
        # Espera acumulada de cada veículo em andamento, para a espera média «ao vivo». Bate com o
        # `waitingTime` do tripinfo (tempo com velocidade < 0,1 m/s), que só existe no fim da corrida.
        self._espera_s: dict[str, int] = {}
        self._espera_dos_chegados_s = 0
        self.chegados = 0
        self._nome_da_ligacao = f"{self.cenario}_{self.semente}_{id(self)}"

    # --- ciclo de vida -------------------------------------------------------------------------

    def __enter__(self) -> "SessaoDeSimulacao":
        self.abrir()
        return self

    def __exit__(self, *_) -> None:
        self.fechar()

    def abrir(self) -> None:
        pasta = self.pasta
        comando = [
            str(Path(sumo.SUMO_HOME) / "bin" / "sumo.exe"), "-n", str(REDE),
            "--seed", str(self.semente), "--no-step-log", "--no-warnings",
        ]
        # O SUMO lê a procura de um ficheiro: sem pasta de resultados, vai para um directório temporário.
        if pasta is None:
            self._temporario = tempfile.TemporaryDirectory(prefix="sessao_sumo_", ignore_cleanup_errors=True)  # no Windows o SUMO ainda pode ter o ficheiro aberto
            procura_pasta = Path(self._temporario.name)
        else:
            procura_pasta = pasta
        procura_pasta.mkdir(parents=True, exist_ok=True)
        procura = gerar_ficheiro_de_procura(CENARIO_PROCURA, procura_pasta / "procura.rou.xml", self.escala)
        comando += ["-r", str(procura)]
        if pasta:
            pasta.mkdir(parents=True, exist_ok=True)
            comando += ["--tripinfo-output", str(pasta / "tripinfo.xml")]

        traci.start(comando, label=self._nome_da_ligacao)
        self._ligacao = traci.getConnection(self._nome_da_ligacao)
        self._ponte = PonteSumo(self._ligacao)
        if self.cenario in ("local", "coordenado"):
            topologias = self._ponte.descobrir_topologias()
            self._ponte.subscrever_faixas(topologias)
            for no_id, topologia in topologias.items():
                controlador = ControladorLocal(topologia, self.parametros_locais)
                self._controladores[no_id] = controlador
                self._ponte.assumir_controlo(no_id, controlador.estado)
            if self.cenario == "coordenado":
                self._coordenador = CoordenadorAntiBloqueio(topologias, self.parametros_coordenador)
        self._estados_aplicados = {no_id: c.estado for no_id, c in self._controladores.items()}
        if self.incidente:
            self._gestor_incidente = GestorDeIncidente(self._ligacao, carregar_incidente(CENARIO_INCIDENTE))
        if self.vias_alternativas:
            self._recomendador = RecomendadorDeRotas(self._ligacao)

    def fechar(self) -> None:
        """Fecha o SUMO. O tripinfo só fica completo depois disto."""
        if self._ligacao is not None:
            self._ligacao.close()
            self._ligacao = None
        if self._temporario is not None:
            self._temporario.cleanup()
            self._temporario = None

    # --- avançar -------------------------------------------------------------------------------

    def terminou(self) -> bool:
        return self._ligacao is None or self._ligacao.simulation.getMinExpectedNumber() <= 0

    def passo(self) -> None:
        """Avança 1 s: SUMO, eventos, controlo dos semáforos e contabilidade."""
        ligacao = self._ligacao
        ligacao.simulationStep()
        self.tempo_s = int(ligacao.simulation.getTime())
        if self._gestor_incidente:
            self._gestor_incidente.passo(self.tempo_s)
        if self._recomendador:
            self._recomendador.passo(self.tempo_s)
        if self._controladores:
            leitura = self._ponte.ler_faixas()
            ordens = self._coordenador.passo(self.tempo_s, leitura) if self._coordenador else {}
            for no_id, controlador in self._controladores.items():
                if self._coordenador:
                    controlador.receber_ordem(ordens[no_id])
                estado = controlador.passo(self.tempo_s, leitura)
                # Só se fala com o SUMO quando o estado muda: poupa milhares de chamadas.
                if estado != self._estados_aplicados[no_id]:
                    self._ponte.aplicar_estado(no_id, estado)
                    self._estados_aplicados[no_id] = estado
        self.teleportes += ligacao.simulation.getStartingTeleportNumber()
        self.colisoes += ligacao.simulation.getCollidingVehiclesNumber()
        if self.observar:
            self._actualizar_veiculos()

    def _actualizar_veiculos(self) -> None:
        """Lê os veículos por subscrição (um pedido para todos) em vez de uma chamada por veículo."""
        ligacao = self._ligacao
        for id_ in ligacao.simulation.getDepartedIDList():
            ligacao.vehicle.subscribe(id_, _VARIAVEIS_DO_VEICULO)
            self._espera_s[id_] = 0
        for id_ in ligacao.simulation.getArrivedIDList():
            espera = self._espera_s.pop(id_, 0)
            if not id_.startswith(PREFIXO_VEICULO_DO_INCIDENTE):
                self._espera_dos_chegados_s += espera
                self.chegados += 1
        vistos = {}
        for id_, dados in ligacao.vehicle.getAllSubscriptionResults().items():
            (x, y), velocidade = dados[tc.VAR_POSITION], dados[tc.VAR_SPEED]
            # Os veículos avariados do incidente são carros parados por desenho: marcam-se à parte
            # para o mapa os desenhar como obstáculo e para não entrarem nos indicadores.
            tipo = "avariado" if id_.startswith(PREFIXO_VEICULO_DO_INCIDENTE) else dados[tc.VAR_TYPE]
            vistos[id_] = VeiculoVisto(x, y, dados[tc.VAR_ANGLE], velocidade, tipo)
            if velocidade < _LIMIAR_DE_PARADO_MS and id_ in self._espera_s:
                self._espera_s[id_] += 1
        self._veiculos = vistos

    # --- observar ------------------------------------------------------------------------------

    def veiculos_da_rede(self) -> list[VeiculoVisto]:
        return [v for v in self._veiculos.values() if v.tipo != "avariado"]

    def amostra(self) -> Amostra:
        """Uma linha da série temporal (a mesma medida que sempre se gravou em `serie.csv`)."""
        ids = [i for i in self._ligacao.vehicle.getIDList() if not i.startswith(PREFIXO_VEICULO_DO_INCIDENTE)]
        velocidades = [self._ligacao.vehicle.getSpeed(i) for i in ids]
        return Amostra(
            tempo_s=self.tempo_s,
            veiculos_na_rede=len(ids),
            veiculos_parados=sum(1 for v in velocidades if v < _LIMIAR_DE_PARADO_MS),
            velocidade_media_ms=sum(velocidades) / len(velocidades) if velocidades else 0.0,
        )

    def nao_concluidos(self) -> int:
        return len([i for i in self._ligacao.vehicle.getIDList() if not i.startswith(PREFIXO_VEICULO_DO_INCIDENTE)])

    def instantaneo(self) -> Instantaneo:
        """Estado para mostrar (mapa ao vivo). Exige `observar=True`."""
        if not self.observar:
            raise RuntimeError("instantaneo() só funciona com observar=True.")
        reais = self.veiculos_da_rede()
        # Para os semáforos que o SUMO controla (tempo fixo) lê-se o estado; para os nossos, o último aplicado.
        if self._controladores:
            semaforos = dict(self._estados_aplicados)
        else:
            semaforos = {n: self._ligacao.trafficlight.getRedYellowGreenState(n) for n in self._ligacao.trafficlight.getIDList()}
        return Instantaneo(
            tempo_s=self.tempo_s,
            veiculos=dict(self._veiculos),
            semaforos=semaforos,
            na_rede=len(reais),
            parados=sum(1 for v in reais if v.parado),
            velocidade_media_ms=sum(v.velocidade for v in reais) / len(reais) if reais else 0.0,
            chegados=self.chegados,
            espera_media_dos_chegados_s=self._espera_dos_chegados_s / self.chegados if self.chegados else 0.0,
        )
