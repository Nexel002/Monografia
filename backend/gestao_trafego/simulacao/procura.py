"""Gera o ficheiro de procura (veículos) do SUMO a partir de um cenário em JSON.

O JSON guarda os fluxos em veículos/hora por par origem->destino; este módulo só o traduz para
o formato do SUMO. Mantê-los separados permite trocar os números assumidos pelos observados em
campo sem tocar em código.
"""

import json
from pathlib import Path
from xml.etree import ElementTree as ET


def gerar_ficheiro_de_procura(cenario_json: Path, destino: Path, escala: float = 1.0) -> Path:
    """Escreve `destino` (.rou.xml). `escala` multiplica todos os fluxos (ex.: 0.5 = hora normal)."""
    cenario = json.loads(cenario_json.read_text(encoding="utf-8"))

    raiz = ET.Element("routes")
    distribuicao = ET.SubElement(raiz, "vTypeDistribution", id="mistura")
    for tipo in cenario["tipos"]:
        ET.SubElement(
            distribuicao,
            "vType",
            id=tipo["id"],
            probability=str(tipo["proporcao"]),
            length=str(tipo["comprimento"]),
            vClass=tipo["vclass"],
            maxSpeed=str(tipo["vel_max"]),
            accel=str(tipo["aceleracao"]),
            decel=str(tipo["desaceleracao"]),
            sigma=str(tipo["sigma"]),
            color=tipo["cor"],
        )

    for fluxo in cenario["fluxos"]:
        # `probability` (e não `vehsPerHour`) dá chegadas aleatórias de Poisson, mais
        # parecidas com o tráfego real do que veículos espaçados à régua. O resultado
        # continua repetível porque a semente do SUMO é fixa.
        veiculos_por_segundo = fluxo["veiculos_por_hora"] * escala / 3600
        ET.SubElement(
            raiz,
            "flow",
            id=fluxo["id"],
            type="mistura",
            attrib={"from": fluxo["de"], "to": fluxo["para"]},
            begin="0",
            end=str(cenario["duracao_s"]),
            probability=f"{veiculos_por_segundo:.6f}",
            departLane="best",
            departSpeed="max",
        )

    ET.indent(raiz)
    destino.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(raiz).write(destino, encoding="utf-8", xml_declaration=True)
    return destino
