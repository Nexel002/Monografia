import numpy as np

from gestao_trafego.previsao.dataset import (
    Normalizacao,
    erro_absoluto_medio,
    janelas_deslizantes,
    previsao_por_persistencia,
)
from gestao_trafego.previsao.modelo import ModeloTreinado, treinar


def serie(valores, na_rede=10.0, velocidade=5.0) -> np.ndarray:
    return np.array([[v, na_rede, velocidade] for v in valores], dtype=np.float32)


def test_janelas_tem_a_forma_e_o_alvo_certos():
    # parados = 0,1,2,...,9; recuo 3; horizonte 2 passos
    janelas = janelas_deslizantes([serie(range(10))], recuo=3, horizontes_passos=(2,))

    assert janelas.entradas.shape == (6, 3, 3)  # janelas que acabam nos passos 2..7 (precisam de +2 à frente)
    primeira = janelas.entradas[0, :, 0]
    assert list(primeira) == [0, 1, 2]
    assert janelas.alvos[0, 0] == 4  # último visto = 2; daqui a 2 passos = 4
    assert janelas.instantes_alvo_s[0, 0] == 50  # passo 4 = amostra n.º 5 = 50 s


def test_varios_horizontes_numa_so_janela():
    janelas = janelas_deslizantes([serie(range(20))], recuo=3, horizontes_passos=(1, 5))

    assert list(janelas.alvos[0]) == [3, 7]
    assert len(janelas.alvos) == 20 - 3 - 5 + 1


def test_series_curtas_nao_dao_janelas_e_nao_rebentam():
    janelas = janelas_deslizantes([serie(range(4))], recuo=3, horizontes_passos=(5,))

    assert len(janelas.alvos) == 0


def test_nao_mistura_series_diferentes_e_guarda_a_origem():
    janelas = janelas_deslizantes([serie(range(8)), serie(range(100, 108))], recuo=3, horizontes_passos=(1,))

    assert set(janelas.origem) == {0, 1}
    # nenhuma janela atravessa a fronteira entre as duas séries
    assert all(abs(j[:, 0].max() - j[:, 0].min()) <= 2 for j in janelas.entradas)


def test_persistencia_repete_o_ultimo_valor_visto():
    janelas = janelas_deslizantes([serie(range(10))], recuo=3, horizontes_passos=(1, 4))

    previsto = previsao_por_persistencia(janelas)

    assert list(previsto[0]) == [2, 2]
    assert list(erro_absoluto_medio(previsto, janelas.alvos)) == [1.0, 4.0]  # numa rampa, o erro é o horizonte


def test_normalizacao_com_variavel_constante_nao_divide_por_zero():
    entradas = serie(range(10))  # as outras duas colunas são constantes

    n = Normalizacao.ajustar(entradas[None])

    assert np.isfinite(n.aplicar(entradas)).all()
    assert list(n.desvio[1:]) == [1.0, 1.0]


def test_lstm_aprende_um_padrao_periodico_e_bate_a_persistencia(tmp_path):
    # Fila que sobe e desce em ondas: dá para a prever olhando para a fase da onda, a persistência não.
    t = np.arange(400)
    ondas = [serie(10 + 8 * np.sin(2 * np.pi * (t + fase) / 40)) for fase in (0, 7, 13, 21)]
    janelas = janelas_deslizantes(ondas, recuo=12, horizontes_passos=(10,))

    modelo, perdas = treinar(janelas, (10,), recuo=12, epocas=25, escondido=16)

    erro_lstm = erro_absoluto_medio(modelo.prever(janelas.entradas), janelas.alvos)[0]
    erro_pers = erro_absoluto_medio(previsao_por_persistencia(janelas), janelas.alvos)[0]
    assert perdas[-1] < perdas[0]
    assert erro_lstm < erro_pers

    # guardar e carregar dá as mesmas previsões
    modelo.guardar(tmp_path / "m.pt")
    recarregado = ModeloTreinado.carregar(tmp_path / "m.pt")
    assert np.allclose(recarregado.prever(janelas.entradas[:5]), modelo.prever(janelas.entradas[:5]), atol=1e-5)


def test_previsoes_nunca_sao_negativas():
    janelas = janelas_deslizantes([serie([0.0] * 60)], recuo=6, horizontes_passos=(3,))
    modelo, _ = treinar(janelas, (3,), recuo=6, epocas=3, escondido=8)

    assert (modelo.prever(janelas.entradas) >= 0).all()
