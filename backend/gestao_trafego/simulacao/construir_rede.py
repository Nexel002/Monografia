"""Constrói a rede SUMO do corredor da Av. 24 de Julho a partir do OpenStreetMap.

Uso (a partir de backend/):
    uv run python -m gestao_trafego.simulacao.construir_rede

Descarrega por quadrantes porque a API do OSM recusa áreas com mais de 50 000 nós e o Overpass
devolveu 406/500/504 nas tentativas de 10/10/2026. Os ficheiros .osm ficam em dados/mapas/
(fora do Git); só a rede .net.xml, pequena, é versionada em dados/cenarios/.
"""

import subprocess
import urllib.request
from pathlib import Path

import sumo

RAIZ = Path(__file__).resolve().parents[3]
PASTA_MAPAS = RAIZ / "dados" / "mapas"
REDE_SAIDA = RAIZ / "dados" / "cenarios" / "corredor_24_de_julho.net.xml"

# (oeste, sul, este, norte). A zona do Alto-Maé é tão densa que o quadrante do meio-norte
# tem de ser repartido em quatro; os outros três cabem inteiros.
QUADRANTES = {
    "q1": (32.560, -25.980, 32.580, -25.962),
    "q2_1": (32.560, -25.962, 32.570, -25.953),
    "q2_2": (32.560, -25.953, 32.570, -25.944),
    "q2_3": (32.570, -25.962, 32.580, -25.953),
    "q2_4": (32.570, -25.953, 32.580, -25.944),
    "q3": (32.580, -25.980, 32.600, -25.962),
    "q4": (32.580, -25.962, 32.600, -25.944),
}

# Recorte final: Av. 24 de Julho entre a Tanzânia (C4) e a Vladimir Lenine, mais a Eduardo Mondlane
# paralela, que serve de via alternativa. Em lon/lat: oeste,sul,este,norte.
RECORTE_GEO = "32.558,-25.972,32.582,-25.955"


def descarregar_quadrantes() -> list[Path]:
    PASTA_MAPAS.mkdir(parents=True, exist_ok=True)
    ficheiros = []
    for nome, (oeste, sul, este, norte) in QUADRANTES.items():
        destino = PASTA_MAPAS / f"{nome}.osm"
        ficheiros.append(destino)
        if destino.exists() and destino.stat().st_size > 1000:
            continue
        url = f"https://api.openstreetmap.org/api/0.6/map?bbox={oeste},{sul},{este},{norte}"
        # A API do OSM exige um User-Agent identificável.
        pedido = urllib.request.Request(url, headers={"User-Agent": "monografia-maputo/0.1"})
        with urllib.request.urlopen(pedido, timeout=180) as resposta:
            destino.write_bytes(resposta.read())
    return ficheiros


def converter(ficheiros_osm: list[Path]) -> None:
    sumo_home = Path(sumo.SUMO_HOME)
    REDE_SAIDA.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(sumo_home / "bin" / "netconvert.exe"),
            "--osm-files", ",".join(str(f) for f in ficheiros_osm),
            "-o", str(REDE_SAIDA),
            "--type-files", str(sumo_home / "data" / "typemap" / "osmNetconvert.typ.xml"),
            "--keep-edges.in-geo-boundary", RECORTE_GEO,
            "--keep-edges.by-vclass", "passenger",
            "--remove-edges.isolated",
            "--geometry.remove",
            "--roundabouts.guess",
            "--ramps.guess",
            "--junctions.join",
            # Os semáforos do OSM são incompletos; adivinhar e juntar os clusters evita
            # um semáforo por cada ramo do mesmo cruzamento.
            "--tls.guess-signals",
            "--tls.discard-simple",
            "--tls.join",
            # Sem isto as arestas perdem o nome e não se consegue localizar C4/C5 por avenida.
            "--output.street-names",
            "--no-warnings",
        ],
        check=True,
    )


if __name__ == "__main__":
    converter(descarregar_quadrantes())
    print(f"Rede escrita em {REDE_SAIDA}")
