"""Corre uma simulação no SUMO via TraCI e grava as métricas.

Uso (a partir de backend/):
    uv run python -m gestao_trafego.simulacao.executar --cenario fixo

O cenário `fixo` deixa os semáforos com os programas de tempo fixo que o netconvert gerou: é o
cenário de referência (o funcionamento actual em Maputo) contra o qual se mede o sistema inteligente.
"""

import argparse
import csv
import json
import subprocess
from pathlib import Path

import sumo
import traci

from gestao_trafego.simulacao.metricas import Amostra, ler_viagens, resumir
from gestao_trafego.simulacao.procura import gerar_ficheiro_de_procura

RAIZ = Path(__file__).resolve().parents[3]
REDE = RAIZ / "dados" / "cenarios" / "corredor_24_de_julho.net.xml"
CENARIO_PROCURA = RAIZ / "dados" / "cenarios" / "procura_hora_de_ponta.json"
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
) -> dict:
    """Devolve o resumo de KPIs e deixa tripinfo.xml, serie.csv e resumo.json em `pasta_saida`."""
    if cenario != "fixo":
        raise ValueError(f"Cenário desconhecido: {cenario!r} (por agora só existe 'fixo').")

    duracao_procura_s = json.loads(CENARIO_PROCURA.read_text(encoding="utf-8"))["duracao_s"]
    limite_s = limite_s or duracao_procura_s + MARGEM_PARA_ESVAZIAR_S
    pasta = pasta_saida or PASTA_RESULTADOS / f"{cenario}_s{semente}_x{escala}"
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
    try:
        tempo = 0
        while tempo < limite_s and ligacao.simulation.getMinExpectedNumber() > 0:
            ligacao.simulationStep()
            tempo = int(ligacao.simulation.getTime())
            teleportes += ligacao.simulation.getStartingTeleportNumber()
            colisoes += ligacao.simulation.getCollidingVehiclesNumber()
            if tempo % INTERVALO_AMOSTRA_S == 0:
                ids = ligacao.vehicle.getIDList()
                velocidades = [ligacao.vehicle.getSpeed(i) for i in ids]
                amostras.append(
                    Amostra(
                        tempo_s=tempo,
                        veiculos_na_rede=len(ids),
                        veiculos_parados=sum(1 for v in velocidades if v < 0.1),
                        velocidade_media_ms=sum(velocidades) / len(velocidades) if velocidades else 0.0,
                    )
                )
        nao_concluidos = len(ligacao.vehicle.getIDList())
    finally:
        # O tripinfo só fica completo quando o SUMO fecha.
        ligacao.close()

    resumo = resumir(ler_viagens(tripinfo), amostras, nao_concluidos, teleportes, colisoes, tempo)
    resumo.update({"cenario": cenario, "semente": semente, "escala": escala})

    with (pasta / "serie.csv").open("w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(["tempo_s", "veiculos_na_rede", "veiculos_parados", "velocidade_media_ms"])
        for a in amostras:
            escritor.writerow([a.tempo_s, a.veiculos_na_rede, a.veiculos_parados, f"{a.velocidade_media_ms:.3f}"])
    (pasta / "resumo.json").write_text(json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8")
    return resumo


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cenario", default="fixo", choices=["fixo"])
    parser.add_argument("--semente", type=int, default=42)
    parser.add_argument("--escala", type=float, default=1.0, help="multiplica a procura (0,5 = hora normal)")
    parser.add_argument("--limite", type=int, default=None, help="tempo máximo simulado, em segundos")
    argumentos = parser.parse_args()
    resumo = executar_simulacao(argumentos.cenario, argumentos.semente, argumentos.escala, argumentos.limite)
    print(json.dumps(resumo, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
