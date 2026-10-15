"""Testes estatísticos exactos para comparações emparelhadas (a mesma semente nas duas configurações).

A hipótese H3 da monografia fala de melhorias «estatisticamente significativas»: aqui testam-se. Com 8
sementes, as distribuições exactas enumeram-se por completo (2^8 = 256 combinações de sinais), o que dispensa
aproximações e dependências. Não se assume normalidade: um teste de Wilcoxon e um teste de permutação de sinais.
"""

from itertools import product
from statistics import mean


def _postos(valores: list[float]) -> list[float]:
    """Postos (1, 2, ...) com a média dos postos nos empates."""
    ordem = sorted(range(len(valores)), key=lambda i: valores[i])
    postos = [0.0] * len(valores)
    i = 0
    while i < len(ordem):
        j = i
        while j + 1 < len(ordem) and valores[ordem[j + 1]] == valores[ordem[i]]:
            j += 1
        for k in range(i, j + 1):
            postos[ordem[k]] = (i + j) / 2 + 1
        i = j + 1
    return postos


def _p_por_sinais(estatistica_observada: float, pesos: list[float]) -> float:
    """P(|T| >= |T_obs|) sobre todas as atribuições de sinais, com T = soma(sinal * peso). Bilateral e exacto."""
    centro = sum(pesos) / 2  # se só o sinal «positivo» conta, T tem média soma/2; trabalhamos com o desvio ao centro
    observado = abs(estatistica_observada - centro)
    total = favoraveis = 0
    for sinais in product((0, 1), repeat=len(pesos)):
        t = sum(p for s, p in zip(sinais, pesos, strict=True) if s)
        total += 1
        if abs(t - centro) >= observado - 1e-12:
            favoraveis += 1
    return favoraveis / total


def wilcoxon_exacto(diferencas: list[float]) -> float:
    """Valor p bilateral do teste de Wilcoxon de postos com sinais. As diferenças nulas são descartadas."""
    d = [x for x in diferencas if x != 0]
    if not d:
        return 1.0
    postos = _postos([abs(x) for x in d])
    soma_positivos = sum(p for x, p in zip(d, postos, strict=True) if x > 0)
    return _p_por_sinais(soma_positivos, postos)


def permutacao_de_sinais(diferencas: list[float]) -> float:
    """Valor p bilateral do teste de permutação de sinais sobre a média das diferenças."""
    d = [x for x in diferencas if x != 0]
    if not d:
        return 1.0
    pesos = [abs(x) for x in d]
    soma_positivos = sum(p for x, p in zip(d, pesos, strict=True) if x > 0)
    return _p_por_sinais(soma_positivos, pesos)


def comparar_emparelhado(referencia: list[float], alternativa: list[float]) -> dict:
    """Compara `alternativa` com `referencia` (menos é melhor): média, redução, quantas sementes melhoraram e valores p."""
    if len(referencia) != len(alternativa) or not referencia:
        raise ValueError("As duas listas têm de ter o mesmo tamanho, não vazio (uma entrada por semente).")
    diferencas = [r - a for r, a in zip(referencia, alternativa, strict=True)]  # positivo = a alternativa melhorou
    media_ref = mean(referencia)
    return {
        "sementes": len(referencia),
        "media_referencia": media_ref,
        "media_alternativa": mean(alternativa),
        "reducao_percentual": 100 * mean(diferencas) / media_ref if media_ref else 0.0,
        "sementes_que_melhoraram": sum(1 for x in diferencas if x > 0),
        "p_wilcoxon": wilcoxon_exacto(diferencas),
        "p_permutacao": permutacao_de_sinais(diferencas),
    }


def ajuste_de_holm(valores_p: list[float]) -> list[float]:
    """Valores p ajustados pelo método de Holm (comparações múltiplas), na ordem original.

    Fazer várias comparações sobre os mesmos dados aumenta a probabilidade de achar uma «significativa» por acaso;
    o Holm corrige isso sem ser tão severo como o Bonferroni.
    """
    m = len(valores_p)
    ordem = sorted(range(m), key=lambda i: valores_p[i])
    ajustados = [0.0] * m
    maximo = 0.0
    for posicao, i in enumerate(ordem):
        maximo = max(maximo, min(1.0, (m - posicao) * valores_p[i]))  # o ajustado nunca desce ao longo da ordem
        ajustados[i] = maximo
    return ajustados
