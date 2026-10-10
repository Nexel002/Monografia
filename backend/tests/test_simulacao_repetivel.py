import pytest

from gestao_trafego.simulacao.executar import executar_simulacao


@pytest.mark.slow
def test_mesma_semente_da_o_mesmo_resultado(tmp_path):
    # Sem repetibilidade a comparação fixo vs inteligente não vale nada: qualquer diferença
    # podia ser ruído da simulação e não efeito do algoritmo.
    a = executar_simulacao("fixo", semente=7, limite_s=300, pasta_saida=tmp_path / "a")
    b = executar_simulacao("fixo", semente=7, limite_s=300, pasta_saida=tmp_path / "b")

    assert a == b
    assert a["veiculos_concluidos"] > 0


@pytest.mark.slow
def test_sementes_diferentes_dao_resultados_diferentes(tmp_path):
    a = executar_simulacao("fixo", semente=1, limite_s=300, pasta_saida=tmp_path / "a")
    b = executar_simulacao("fixo", semente=2, limite_s=300, pasta_saida=tmp_path / "b")

    assert a["espera_media_s"] != b["espera_media_s"]
