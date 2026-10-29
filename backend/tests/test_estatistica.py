import pytest

from gestao_trafego.comum.estatistica import comparar_emparelhado, permutacao_de_sinais, wilcoxon_exacto


def test_oito_melhorias_em_oito_da_o_menor_p_possivel():
    # só as combinações «tudo positivo» e «tudo negativo» são tão extremas: 2 em 256
    assert wilcoxon_exacto([5, 3, 8, 1, 9, 2, 7, 4]) == pytest.approx(2 / 256)
    assert permutacao_de_sinais([5, 3, 8, 1, 9, 2, 7, 4]) == pytest.approx(2 / 256)


def test_diferencas_simetricas_nao_sao_significativas():
    assert wilcoxon_exacto([1, -1, 2, -2, 3, -3]) == pytest.approx(1.0)


def test_um_so_sinal_contrario_com_efeito_pequeno_continua_significativo():
    # 7 melhorias grandes e uma piora pequena (a de menor posto)
    assert wilcoxon_exacto([10, 9, 8, 7, 6, 5, 4, -1]) < 0.05


def test_diferencas_nulas_sao_descartadas_e_tudo_nulo_da_p_1():
    assert wilcoxon_exacto([0, 0, 0]) == 1.0
    assert wilcoxon_exacto([0, 5, 3, 2, 4, 6, 1, 7, 8]) == pytest.approx(2 / 256)  # 8 não nulas, todas positivas


def test_empates_nos_modulos_nao_rebentam():
    assert 0 < wilcoxon_exacto([2, 2, 2, -2, 2, 2]) <= 1


def test_nao_depende_do_sinal_global_mas_so_da_simetria():
    assert wilcoxon_exacto([5, 3, 8, 1]) == wilcoxon_exacto([-5, -3, -8, -1])


def test_comparar_emparelhado_calcula_a_reducao_e_conta_as_sementes():
    r = comparar_emparelhado([100, 120, 140, 110, 130, 90, 100, 115], [80, 90, 100, 85, 100, 70, 85, 95])

    assert r["sementes"] == 8 and r["sementes_que_melhoraram"] == 8
    assert r["reducao_percentual"] == pytest.approx(100 * (sum([20, 30, 40, 25, 30, 20, 15, 20]) / 8) / (905 / 8))
    assert r["p_wilcoxon"] == pytest.approx(2 / 256)


def test_comparar_emparelhado_com_listas_incompativeis_falha_alto():
    with pytest.raises(ValueError):
        comparar_emparelhado([1, 2], [1])
    with pytest.raises(ValueError):
        comparar_emparelhado([], [])


def test_holm_multiplica_pelo_numero_de_comparacoes_que_faltam_e_mantem_a_ordem():
    from gestao_trafego.comum.estatistica import ajuste_de_holm

    ajustados = ajuste_de_holm([0.01, 0.04, 0.03, 0.2])

    assert ajustados == pytest.approx([0.04, 0.09, 0.09, 0.2])  # 0.01×4, max(0.03×3, 0.04×2)... em ordem crescente: 0.04, 0.09, 0.09, 0.2


def test_holm_nunca_passa_de_1_nem_baixa_o_p():
    from gestao_trafego.comum.estatistica import ajuste_de_holm

    assert ajuste_de_holm([0.6, 0.9]) == [1.0, 1.0]
    assert all(a >= p for a, p in zip(ajuste_de_holm([0.001, 0.2, 0.5]), [0.001, 0.2, 0.5], strict=True))
