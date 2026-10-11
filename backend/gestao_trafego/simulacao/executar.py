"""Corre uma simulação no SUMO via TraCI e grava as métricas.

Uso (a partir de backend/):
    uv run python -m gestao_trafego.simulacao.executar --cenario fixo

O cenário `fixo` deixa os semáforos com os programas de tempo fixo que o netconvert gerou: é o
cenário de referência (o funcionamento actual em Maputo) contra o qual se mede o sistema inteligente.
"""

import argparse
import csv
import json
from pathlib import Path

import sumo
import traci

from gestao_trafego.controlo.coordenador.anti_bloqueio import CoordenadorAntiBloqueio, ParametrosDoCoordenador
from gestao_trafego.controlo.local.max_pressure import ControladorLocal, ParametrosLocais
from gestao_trafego.simulacao.eventos import GestorDeIncidente, carregar_incidente
from gestao_trafego.simulacao.metricas import PREFIXO_VEICULO_DO_INCIDENTE, Amostra, ler_viagens, resumir
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
PASTA_RESULTADOS = RAIZ / "dados" / "resultados"

INTERVALO_AMOSTRA_S = 10  # a cada passo seria CSV enorme sem ganho para os gráficos
# Depois de a procura acabar, deixa-se a rede esvaziar. Sem tecto, uma rede bloqueada nunca terminava.
MARGEM_PARA_ESVAZIAR_S = 3600


def executar_simulacao(
    cenario: str = "fixo",
    semente: int = 42,
    escala: float = 1.0,
    limite_s: int | None = None,
    pasta_saida: Path | None = None,
    parametros_locais: ParametrosLocais | None = None,
    parametros_coordenador: ParametrosDoCoordenador | None = None,
    incidente: bool = False,
    vias_alternativas: bool = False,
) -> dict:
    """Devolve o resumo de KPIs e deixa tripinfo.xml, serie.csv e resumo.json em `pasta_saida`."""
    if cenario not in CENARIOS:
        raise ValueError(f"Cenário desconhecido: {cenario!r} (existem: {', '.join(CENARIOS)}).")

    duracao_procura_s = json.loads(CENARIO_PROCURA.read_text(encoding="utf-8"))["duracao_s"]
    # Um limite explícito (ensaios curtos) vai no nome da pasta: sem isso, um ensaio de 30 minutos
    # sobrescrevia os resultados da corrida completa com o mesmo cenário, semente e escala.
    sufixo_limite = f"_lim{limite_s}" if limite_s else ""
    limite_s = limite_s or duracao_procura_s + MARGEM_PARA_ESVAZIAR_S
    sufixo_eventos = ("_incidente" if incidente else "") + ("_vias" if vias_alternativas else "")
    pasta = pasta_saida or PASTA_RESULTADOS / f"{cenario}_s{semente}_x{escala}{sufixo_eventos}{sufixo_limite}"
    pasta.mkdir(parents=True, exist_ok=True)

    procura = gerar_ficheiro_de_procura(CENARIO_PROCURA, pasta / "procura.rou.xml", escala)
    tripinfo = pasta / "tripinfo.xml"

    comando = [
        str(Path(sumo.SUMO_HOME) / "bin" / "sumo.exe"),
        "-n", str(REDE),
        "-r", str(procura),
        "--seed", str(semente),
        "--tripinfo-output", str(tripinfo),
        "--no-step-log",
        "--no-warnings",
    ]

    amostras: list[Amostra] = []
    teleportes = colisoes = 0
    nome_ligacao = f"{cenario}_{semente}"
    traci.start(comando, label=nome_ligacao)
    ligacao = traci.getConnection(nome_ligacao)
    ponte = PonteSumo(ligacao)
    controladores: dict[str, ControladorLocal] = {}
    coordenador: CoordenadorAntiBloqueio | None = None
    if cenario in ("local", "coordenado"):
        topologias = ponte.descobrir_topologias()
        ponte.subscrever_faixas(topologias)
        for no_id, topologia in topologias.items():
            controladores[no_id] = ControladorLocal(topologia, parametros_locais)
            ponte.assumir_controlo(no_id, controladores[no_id].estado)
        if cenario == "coordenado":
            coordenador = CoordenadorAntiBloqueio(topologias, parametros_coordenador)
    estados_aplicados = {no_id: c.estado for no_id, c in controladores.items()}
    gestor_incidente = GestorDeIncidente(ligacao, carregar_incidente(CENARIO_INCIDENTE)) if incidente else None
    recomendador = RecomendadorDeRotas(ligacao) if vias_alternativas else None
    try:
        tempo = 0
        while tempo < limite_s and ligacao.simulation.getMinExpectedNumber() > 0:
            ligacao.simulationStep()
            tempo = int(ligacao.simulation.getTime())
            if gestor_incidente:
                gestor_incidente.passo(tempo)
            if recomendador:
                recomendador.passo(tempo)
            if controladores:
                leitura = ponte.ler_faixas()
                ordens = coordenador.passo(tempo, leitura) if coordenador else {}
                for no_id, controlador in controladores.items():
                    if coordenador:
                        controlador.receber_ordem(ordens[no_id])
                    estado = controlador.passo(tempo, leitura)
                    # Só se fala com o SUMO quando o estado muda: poupa milhares de chamadas.
                    if estado != estados_aplicados[no_id]:
                        ponte.aplicar_estado(no_id, estado)
                        estados_aplicados[no_id] = estado
            teleportes += ligacao.simulation.getStartingTeleportNumber()
            colisoes += ligacao.simulation.getCollidingVehiclesNumber()
            if tempo % INTERVALO_AMOSTRA_S == 0:
                ids = [i for i in ligacao.vehicle.getIDList() if not i.startswith(PREFIXO_VEICULO_DO_INCIDENTE)]
                velocidades = [ligacao.vehicle.getSpeed(i) for i in ids]
                amostras.append(
                    Amostra(
                        tempo_s=tempo,
                        veiculos_na_rede=len(ids),
                        veiculos_parados=sum(1 for v in velocidades if v < 0.1),
                        velocidade_media_ms=sum(velocidades) / len(velocidades) if velocidades else 0.0,
                    )
                )
        nao_concluidos = len([i for i in ligacao.vehicle.getIDList() if not i.startswith(PREFIXO_VEICULO_DO_INCIDENTE)])
    finally:
        # O tripinfo só fica completo quando o SUMO fecha.
        ligacao.close()

    resumo = resumir(ler_viagens(tripinfo), amostras, nao_concluidos, teleportes, colisoes, tempo)
    resumo.update(
        {"cenario": cenario, "semente": semente, "escala": escala, "incidente": incidente,
         "vias_alternativas": vias_alternativas}
    )

    with (pasta / "serie.csv").open("w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["tempo_s", "veiculos_na_rede", "veiculos_parados", "velocidade_media_ms"])
        for a in amostras:
            escritor.writerow([a.tempo_s, a.veiculos_na_rede, a.veiculos_parados, f"{a.velocidade_media_ms:.3f}"])
    (pasta / "resumo.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    return resumo


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cenario", default="fixo", choices=CENARIOS)
    parser.add_argument("--semente", type=int, default=42)
    parser.add_argument("--escala", type=float, default=1.0, help="multiplica a procura (0,5 = hora normal)")
    parser.add_argument("--limite", type=int, default=None, help="tempo máximo simulado, em segundos")
    parser.add_argument("--incidente", action="store_true", help="corta a Av. 24 de Julho durante 10 minutos")
    parser.add_argument("--vias-alternativas", action="store_true", help="recomenda rotas alternativas a 50 %% dos condutores")
    parser.add_argument("--verde-minimo", type=float, default=ParametrosLocais.verde_minimo_s)
    parser.add_argument("--histerese", type=float, default=ParametrosLocais.histerese)
    argumentos = parser.parse_args()
    parametros = ParametrosLocais(verde_minimo_s=argumentos.verde_minimo, histerese=argumentos.histerese)
    resumo = executar_simulacao(
        argumentos.cenario, argumentos.semente, argumentos.escala, argumentos.limite, parametros_locais=parametros,
        incidente=argumentos.incidente, vias_alternativas=argumentos.vias_alternativas,
    )
    print(json.dumps(resumo, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
